"""No global price -- an eventually-consistent, causally-ordered value model (RVO-1).

There is no global, instantaneous price. There are FRAMES (market / venue /
currency), each with a local real-time price, and a CAUSAL (partial) order between
value events across frames. This module supplies:

  * vector-clock causality (``vc_leq`` / ``vc_concurrent`` / ``vc_dominates``);
  * a hash-chained receipt (SHA-256) that is the value-event clock, binding the
    causal order to the estate receipt spine;
  * a CRDT-like merge of per-frame value observations -- a per-frame LWW-register
    keyed by the total order ``(lamport, receipt_hash)`` -- that is COMMUTATIVE,
    ASSOCIATIVE and IDEMPOTENT, so ``converge`` is order-INDEPENDENT and reaches
    one eventually-consistent global view from any interleaving.

Teeth (the relativity-of-value guards)
--------------------------------------
REQUIRES  a per-frame price is admitted as ``local_realtime`` (locally consistent,
          real time); global consistency is asserted only as ``eventual``; the
          cross-frame merge is order-independent (any permutation -> same state).
REJECTS   a merge whose result depends on the order observations are applied (not a
          CRDT); a claim of a single GLOBAL price / global simultaneity (the
          relativity-of-value guard, mirroring the flow-regime Navier-Stokes
          no-overclaim tooth); imposing a TOTAL global order where only a
          partial / causal order exists (two causally-concurrent events linearized
          as if ordered); a record asserting IMMEDIATE global consistency
          (``consistency_scope == immediate_global``) -- value is local + eventual,
          not global-instantaneous.

Deterministic and stdlib-only.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import random
from dataclasses import dataclass
from pathlib import Path

_SCHEMA = "schemas/value_frame_observation.schema.json"

# Admissible consistency scopes. A per-frame observation is locally-consistent in
# real time; the global view is eventual. An immediate/global-instantaneous claim
# is the relativity-of-value violation.
LOCAL_SCOPE = "local_realtime"
EVENTUAL_SCOPE = "eventual"
IMMEDIATE_GLOBAL_SCOPE = "immediate_global"
ADMISSIBLE_SCOPES = {LOCAL_SCOPE, EVENTUAL_SCOPE}

# Phrases that assert an inadmissible global / instantaneous price.
_GLOBAL_ACTS = ("is", "are", "holds", "exists", "equals", "converged", "guaranteed",
                "assert", "asserts", "impose", "imposes")
_GLOBAL_PRICE_CLAIMS = (
    "single global price", "one global price", "global price", "universal price",
    "global simultaneity", "simultaneous global", "instantaneous global",
    "instantaneously global", "immediate global consistency",
    "globally consistent at all times", "law of one price holds instantly",
    "law of one price holds exactly at every instant", "global total order of value",
    "one true price",
)


class ValueOrderingError(ValueError):
    """Raised for an inadmissible value record (order-dependent merge, a global-price
    over-claim, a total order over concurrent events) -- REJECTED."""


# --------------------------------------------------------------------------- #
# vector clocks (the causal / partial order)
# --------------------------------------------------------------------------- #
def vc_leq(a: dict, b: dict) -> bool:
    """a <= b in the causal order iff a[k] <= b[k] for every frame k."""
    keys = set(a) | set(b)
    return all(a.get(k, 0) <= b.get(k, 0) for k in keys)


def vc_lt(a: dict, b: dict) -> bool:
    return vc_leq(a, b) and a != b


def vc_dominates(a: dict, b: dict) -> bool:
    """a dominates b iff b <= a (a is causally at-or-after b)."""
    return vc_leq(b, a)


def vc_concurrent(a: dict, b: dict) -> bool:
    """a and b are causally concurrent iff neither precedes the other."""
    return not vc_leq(a, b) and not vc_leq(b, a)


# --------------------------------------------------------------------------- #
# the hash-chained receipt = the value-event clock (bind to the receipt spine)
# --------------------------------------------------------------------------- #
def canonical(body: dict) -> str:
    return json.dumps(body, sort_keys=True, separators=(",", ":"))


def chain_receipt(prev_hash: str, body: dict) -> str:
    """SHA-256 hash-chain: receipt = H(prev_receipt || canonical(event body)).

    The chain is the value-event clock -- a tamper-evident causal spine the merge's
    deterministic tiebreak reads. FIPS SHA-256, deterministic.
    """
    payload = (prev_hash or "") + "\n" + canonical(body)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# observations + the per-frame LWW-register CRDT
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Observation:
    """One per-frame value observation (a local, real-time price event)."""

    frame_id: str
    currency: str
    value: float
    lamport: int                 # scalar Lamport clock (monotone per frame)
    vclock: tuple                 # causal clock as a sorted tuple of (frame, count)
    receipt_hash: str            # hash-chained value-event clock id

    @property
    def vc(self) -> dict:
        return {k: v for k, v in self.vclock}

    def order_key(self) -> tuple:
        """Total order used by the LWW register: (lamport, receipt_hash).

        Deterministic and total, so ``max`` over it is a proper CRDT join --
        commutative, associative, idempotent. The vector clock is used for the
        CAUSAL teeth (concurrency), not for the convergence tiebreak."""
        return (self.lamport, self.receipt_hash)


def observation_from_dict(d: dict) -> Observation:
    vc = d.get("vclock", {})
    vclock = tuple(sorted((str(k), int(v)) for k, v in vc.items()))
    return Observation(
        frame_id=d["frame_id"],
        currency=d["currency"],
        value=float(d["value"]),
        lamport=int(d["lamport"]),
        vclock=vclock,
        receipt_hash=d["receipt_hash"],
    )


def _register(obs: Observation) -> dict:
    return {
        "frame_id": obs.frame_id,
        "currency": obs.currency,
        "value": obs.value,
        "lamport": obs.lamport,
        "vclock": list(obs.vclock),
        "receipt_hash": obs.receipt_hash,
        "_order_key": list(obs.order_key()),
    }


def _reg_order_key(reg: dict) -> tuple:
    return (reg["lamport"], reg["receipt_hash"])


def merge(state_a: dict, state_b: dict) -> dict:
    """Join two converged states. Per frame, keep the register that is maximal under
    the total order ``(lamport, receipt_hash)``.

    This is a per-key LWW-Register CRDT join: commutative, associative, idempotent.
    """
    out = {k: dict(v) for k, v in state_a.items()}
    for frame, reg in state_b.items():
        cur = out.get(frame)
        if cur is None or _reg_order_key(reg) > _reg_order_key(cur):
            out[frame] = dict(reg)
    return out


def observe(state: dict, obs: Observation) -> dict:
    """Merge a single observation into a converged state (join with a singleton)."""
    return merge(state, {obs.frame_id: _register(obs)})


def converge(observations) -> dict:
    """Fold-merge observations into the eventually-consistent global view.

    Order-INDEPENDENT by construction (the fold is a CRDT join)."""
    state: dict = {}
    for obs in observations:
        state = observe(state, obs)
    return state


def state_fingerprint(state: dict) -> str:
    """Canonical id of a converged state (drops volatile ordering)."""
    body = {
        frame: {
            "value": reg["value"],
            "currency": reg["currency"],
            "lamport": reg["lamport"],
            "receipt_hash": reg["receipt_hash"],
        }
        for frame, reg in state.items()
    }
    return "sha256:" + hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# TEETH
# --------------------------------------------------------------------------- #
def assert_merge_order_independent(observations, sample: int = 240) -> str:
    """REJECT a merge whose converged state depends on the order of application.

    Applies the observations in many interleavings (all permutations when few,
    a seeded sample otherwise) and asserts every convergence yields the identical
    state. Returns the common state fingerprint.
    """
    obs = list(observations)
    baseline = state_fingerprint(converge(obs))

    orders = []
    if len(obs) <= 6:
        orders = list(itertools.permutations(obs))
    else:
        orders = [tuple(reversed(obs))]
        rng = random.Random(0xC0FFEE)
        for _ in range(sample):
            perm = obs[:]
            rng.shuffle(perm)
            orders.append(tuple(perm))

    for order in orders:
        fp = state_fingerprint(converge(order))
        if fp != baseline:
            raise ValueOrderingError(
                "merge is ORDER-DEPENDENT: a different interleaving produced a "
                "different converged state; a value merge that depends on order is "
                "not a CRDT and is REJECTED"
            )
    # idempotence: re-applying every observation must not move the state
    doubled = state_fingerprint(converge(obs + obs))
    if doubled != baseline:
        raise ValueOrderingError("merge is NOT idempotent (re-applying an observation moved the state)")
    return baseline


def reject_global_price_overclaim(text) -> None:
    """REJECT any claim of a single GLOBAL price / global simultaneity.

    The relativity-of-value guard (mirrors the flow-regime Navier-Stokes
    no-overclaim tooth): value is local + eventual, never global-instantaneous.
    """
    if text is None:
        return
    if isinstance(text, (list, tuple)):
        for t in text:
            reject_global_price_overclaim(t)
        return
    low = str(text).lower()
    if any(claim in low for claim in _GLOBAL_PRICE_CLAIMS):
        raise ValueOrderingError(
            "REJECTED: single-global-price / global-simultaneity over-claim -- there "
            "is no global instantaneous price; value is local (per frame) and only "
            "EVENTUALLY consistent globally"
        )


def reject_immediate_global_consistency(record: dict) -> None:
    """REJECT a record asserting IMMEDIATE global consistency.

    A per-frame price is admitted as ``local_realtime``; the global view is
    ``eventual``. ``immediate_global`` is inadmissible.
    """
    scope = record.get("consistency_scope")
    if scope == IMMEDIATE_GLOBAL_SCOPE:
        raise ValueOrderingError(
            "REJECTED: consistency_scope=immediate_global -- global consistency is "
            "only EVENTUAL; a per-frame price is locally-consistent-real-time"
        )
    if scope is not None and scope not in ADMISSIBLE_SCOPES:
        raise ValueOrderingError(
            f"unknown consistency_scope {scope!r}; expected one of {sorted(ADMISSIBLE_SCOPES)}"
        )


def reject_total_order_on_concurrent(observations, declared_order) -> None:
    """REJECT imposing a TOTAL global order where only a partial/causal order exists.

    ``declared_order`` is a proposed linear sequence of receipt_hashes. If any two
    ADJACENT-in-claim events are causally CONCURRENT (vector clocks incomparable),
    the claim has linearized a partial order into a false total order.
    """
    by_hash = {o.receipt_hash: o for o in observations}
    seq = [by_hash[h] for h in declared_order if h in by_hash]
    for i in range(len(seq)):
        for j in range(i + 1, len(seq)):
            a, b = seq[i], seq[j]
            if vc_concurrent(a.vc, b.vc):
                raise ValueOrderingError(
                    f"REJECTED: total order imposed over causally-CONCURRENT events "
                    f"{a.receipt_hash!r} and {b.receipt_hash!r}; only a partial/causal "
                    f"order exists (vector clocks are incomparable)"
                )


# --------------------------------------------------------------------------- #
# whole-record check + receipt
# --------------------------------------------------------------------------- #
def check_record(record: dict) -> dict:
    """Validate a value-ordering record against every tooth. Returns a receipt."""
    reject_global_price_overclaim(record.get("interpretation"))
    reject_immediate_global_consistency(record)

    raw = record.get("observations", [])
    if not raw:
        raise ValueOrderingError("record has no observations")
    observations = [observation_from_dict(o) for o in raw]

    # per-frame scope tooth: each observation frame is a local_realtime price
    for o in raw:
        fscope = o.get("scope", LOCAL_SCOPE)
        if fscope != LOCAL_SCOPE:
            raise ValueOrderingError(
                f"observation {o.get('receipt_hash')!r} scope={fscope!r}; a per-frame "
                f"price must be {LOCAL_SCOPE!r} (locally consistent, real time)"
            )

    fingerprint = assert_merge_order_independent(observations)

    if "declared_total_order" in record:
        reject_total_order_on_concurrent(observations, record["declared_total_order"])

    converged = converge(observations)
    frames = sorted(converged.keys())

    # detect concurrency present in the record (proves the order is genuinely partial)
    concurrent_pairs = 0
    for i in range(len(observations)):
        for j in range(i + 1, len(observations)):
            if vc_concurrent(observations[i].vc, observations[j].vc):
                concurrent_pairs += 1

    return {
        "contract": "RVO-1",
        "record_id": record.get("record_id"),
        "consistency_scope": record.get("consistency_scope", EVENTUAL_SCOPE),
        "frames": frames,
        "frame_count": len(frames),
        "observation_count": len(observations),
        "concurrent_pairs": concurrent_pairs,
        "order_independent": True,
        "converged_fingerprint": fingerprint,
        "converged_view": {
            f: {"value": converged[f]["value"], "currency": converged[f]["currency"],
                "lamport": converged[f]["lamport"], "receipt_hash": converged[f]["receipt_hash"]}
            for f in frames
        },
        "global_consistency": "eventual",
    }


def load(path: str) -> dict:
    return json.loads(Path(path).read_text())


def run_check(record_path: str, schema_path: str = _SCHEMA) -> dict:
    from ..validation import validate_json_file

    validate_json_file(record_path, schema_path)
    return check_record(load(record_path))


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Check the relativity-of-price value-ordering contract (RVO-1)."
    )
    parser.add_argument("--record", default="examples/value_ordering/eventual_consistency.valid.json")
    parser.add_argument("--schema", default=_SCHEMA)
    parser.add_argument("--receipt", default=None, help="Optional path to write the receipt JSON.")
    args = parser.parse_args(argv)

    receipt = run_check(args.record, args.schema)
    text = json.dumps(receipt, indent=2, sort_keys=True)
    if args.receipt:
        Path(args.receipt).write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
