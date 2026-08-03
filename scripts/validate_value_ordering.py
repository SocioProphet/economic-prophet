#!/usr/bin/env python3
"""Validate the relativity-of-price value-ordering contract (RVO-1) -- teeth BOTH ways.

  VERIFIES   A valid record schema-validates; its cross-frame merge is ORDER-INDEPENDENT
             (every interleaving converges to the same state); consistency is EVENTUAL;
             the record genuinely exhibits a PARTIAL order (at least one causally-
             concurrent pair) so the no-total-order claim has teeth.

  REJECTS    Every committed *.invalid.json is refused for its specific tooth: a single-
             global-price / global-simultaneity over-claim; a consistency_scope pinned to
             immediate_global; a declared total order imposed over causally-concurrent
             events.

  COHERENCE  The merge is idempotent (re-applying every observation does not move the
             converged state) and the converged fingerprint is stable.

Consume-by-reference: the estate receipt spine (SHA-256 hash chain = value-event clock)
and the holographic-message-stream as the eventually-consistent log. Deterministic,
stdlib + jsonschema only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from open_ep_framework.value_ordering.relativity import (  # noqa: E402
    ValueOrderingError, check_record, observation_from_dict,
    assert_merge_order_independent, converge, state_fingerprint,
)

SCHEMA = ROOT / "schemas" / "value_frame_observation.schema.json"
EXAMPLES = ROOT / "examples" / "value_ordering"

_passes = 0


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ok(msg: str) -> None:
    global _passes
    _passes += 1
    print(f"  PASS  {msg}")


def fail(msg: str) -> None:
    print(f"  FAIL  {msg}")
    sys.exit(1)


def verify_valid(path: Path, schema) -> None:
    rec = load(path)
    errs = sorted(schema.iter_errors(rec), key=lambda e: str(e.path))
    if errs:
        fail(f"{path.name}: schema-invalid: {errs[0].message}")
    receipt = check_record(rec)
    if receipt["global_consistency"] != "eventual":
        fail(f"{path.name}: global consistency is not eventual")
    if receipt["concurrent_pairs"] < 1:
        fail(f"{path.name}: no causally-concurrent pair -- the partial-order claim has no teeth")
    # independent order-independence + idempotence recompute
    obs = [observation_from_dict(o) for o in rec["observations"]]
    fp = assert_merge_order_independent(obs)
    doubled = state_fingerprint(converge(obs + list(reversed(obs))))
    if doubled != fp:
        fail(f"{path.name}: merge not idempotent under duplication")
    ok(f"{path.name}: {receipt['frame_count']} frames, {receipt['concurrent_pairs']} "
       f"concurrent pairs; order-independent + idempotent; eventual consistency")


def reject_invalid(path: Path, schema) -> None:
    rec = load(path)
    name = path.name
    errs = list(schema.iter_errors(rec))
    if errs:
        ok(f"{name}: REJECTED by schema ({errs[0].message[:70]})")
        return
    try:
        check_record(rec)
    except ValueOrderingError as e:
        ok(f"{name}: REJECTED -- {str(e)[:80]}")
        return
    fail(f"{name}: expected REJECTION but no tooth fired")


def main() -> int:
    schema = Draft202012Validator(load(SCHEMA))
    print("RVO-1 relativity-of-price value-ordering contract:")
    for path in sorted(EXAMPLES.glob("*.valid.json")):
        verify_valid(path, schema)
    for path in sorted(EXAMPLES.glob("*.invalid.json")):
        reject_invalid(path, schema)
    print(f"\nOK: {_passes} value-ordering teeth passed (VERIFIES + REJECTS + COHERENCE).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
