"""Per-tooth mutation tests for the relativity-of-price value-ordering contract (RVO-1)."""
import itertools

import pytest

from open_ep_framework.value_ordering.relativity import (
    Observation, ValueOrderingError, assert_merge_order_independent, chain_receipt,
    check_record, converge, merge, observation_from_dict, reject_global_price_overclaim,
    reject_immediate_global_consistency, reject_total_order_on_concurrent,
    state_fingerprint, vc_concurrent, vc_dominates, vc_leq,
)


def _obs(frame, val, lamport, vc, h):
    return Observation(frame, "CUR", val, lamport, tuple(sorted(vc.items())), h)


OBS = [
    _obs("A", 100.0, 1, {"A": 1}, "sha256:aa"),
    _obs("B", 200.0, 1, {"B": 1}, "sha256:bb"),          # concurrent with A
    _obs("C", 300.0, 2, {"C": 1}, "sha256:cc"),          # concurrent with A, B
    _obs("A", 101.0, 3, {"A": 2, "B": 1}, "sha256:dd"),  # dominates A#1 and B
]


# --- vector-clock causal (partial) order ----------------------------------- #
def test_vector_clock_order():
    assert vc_leq({"A": 1}, {"A": 2, "B": 1})
    assert vc_dominates({"A": 2, "B": 1}, {"A": 1})
    assert vc_concurrent({"A": 1}, {"B": 1})
    assert not vc_concurrent({"A": 1}, {"A": 2, "B": 1})


# --- TOOTH: the merge is order-INDEPENDENT (commutative/assoc/idempotent) --- #
def test_merge_order_independent_all_permutations():
    fp = assert_merge_order_independent(OBS)  # tries every permutation, must not raise
    # explicit: every permutation converges to the same fingerprint
    fps = {state_fingerprint(converge(list(p))) for p in itertools.permutations(OBS)}
    assert fps == {fp}


def test_merge_commutative_associative_idempotent():
    a = {o.frame_id: {"frame_id": o.frame_id, "currency": o.currency, "value": o.value,
                      "lamport": o.lamport, "vclock": list(o.vclock),
                      "receipt_hash": o.receipt_hash} for o in [OBS[0]]}
    b = {o.frame_id: {"frame_id": o.frame_id, "currency": o.currency, "value": o.value,
                      "lamport": o.lamport, "vclock": list(o.vclock),
                      "receipt_hash": o.receipt_hash} for o in [OBS[3]]}
    assert merge(a, b) == merge(b, a)               # commutative
    assert merge(a, a) == a                          # idempotent
    # A#2 (lamport 3) dominates A#1 in the register total order
    assert merge(a, b)["A"]["value"] == 101.0


def test_converged_view_picks_causally_latest_per_frame():
    state = converge(OBS)
    assert state["A"]["value"] == 101.0   # lamport-3 observation wins
    assert set(state.keys()) == {"A", "B", "C"}


# --- MUTATION: a non-CRDT (arrival-order) merge is genuinely order-dependent  #
def test_order_dependent_merge_would_be_caught():
    """An arrival-wins merge (last applied wins regardless of clock) is NOT a CRDT.
    Demonstrate it converges differently under different orders -- exactly what the
    order-independence tooth exists to reject."""
    def arrival_converge(observations):
        state = {}
        for o in observations:
            state[o.frame_id] = o.value  # last writer by ARRIVAL, not by clock
        return state

    forward = arrival_converge(OBS)
    backward = arrival_converge(list(reversed(OBS)))
    assert forward != backward  # order-dependent -> not a CRDT
    # our real merge is NOT order-dependent:
    assert state_fingerprint(converge(OBS)) == state_fingerprint(converge(list(reversed(OBS))))


# --- TOOTH: single-global-price / global-simultaneity over-claim REJECTED --- #
def test_global_price_overclaim_rejected():
    with pytest.raises(ValueOrderingError):
        reject_global_price_overclaim("There is a single global price at every instant.")
    with pytest.raises(ValueOrderingError):
        reject_global_price_overclaim(["ok", "global simultaneity of value holds"])


def test_benign_price_language_allowed():
    reject_global_price_overclaim("Each venue has its own local price; the global view is eventual.")
    reject_global_price_overclaim(None)


# --- TOOTH: immediate global consistency REJECTED, local/eventual admitted -- #
def test_immediate_global_consistency_rejected():
    with pytest.raises(ValueOrderingError):
        reject_immediate_global_consistency({"consistency_scope": "immediate_global"})
    reject_immediate_global_consistency({"consistency_scope": "eventual"})
    reject_immediate_global_consistency({"consistency_scope": "local_realtime"})


# --- TOOTH: a total order over CONCURRENT events REJECTED ------------------- #
def test_total_order_over_concurrent_rejected():
    order = ["sha256:aa", "sha256:bb"]  # A and B are concurrent
    with pytest.raises(ValueOrderingError):
        reject_total_order_on_concurrent(OBS, order)


def test_causal_total_order_admitted():
    # A#1 -> A#2 is a genuine causal chain (not concurrent); admitted
    order = ["sha256:aa", "sha256:dd"]
    reject_total_order_on_concurrent(OBS, order)  # must not raise


# --- receipt spine: hash chain is deterministic and body-sensitive --------- #
def test_chain_receipt_deterministic_and_sensitive():
    h1 = chain_receipt("", {"frame_id": "A", "value": 100.0})
    h2 = chain_receipt("", {"frame_id": "A", "value": 100.0})
    h3 = chain_receipt("", {"frame_id": "A", "value": 100.5})
    h4 = chain_receipt(h1, {"frame_id": "A", "value": 100.0})
    assert h1 == h2 and h1.startswith("sha256:")
    assert h1 != h3          # body change moves the hash
    assert h1 != h4          # prev-link change moves the hash (it is a chain)


# --- end-to-end: the shipped valid record passes every tooth --------------- #
def test_valid_record_end_to_end():
    import json
    from pathlib import Path
    rec = json.loads(
        (Path(__file__).resolve().parents[1] / "examples" / "value_ordering"
         / "eventual_consistency.valid.json").read_text()
    )
    receipt = check_record(rec)
    assert receipt["order_independent"] is True
    assert receipt["global_consistency"] == "eventual"
    assert receipt["concurrent_pairs"] >= 1
    obs = [observation_from_dict(o) for o in rec["observations"]]
    assert assert_merge_order_independent(obs) == receipt["converged_fingerprint"]
