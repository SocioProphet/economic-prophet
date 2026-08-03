#!/usr/bin/env python3
"""Validate the index-relative benchmarking contract (IRB-1) -- teeth BOTH ways.

  VERIFIES   A valid book schema-validates and, when recomputed by the deterministic
             module, every cohort's split reconciles in LEVEL (beta*B + eps == X) and
             in VARIANCE (beta^2 var(B) + var(eps) == var(X)); every admitted
             cross-frame comparison rides a DIMENSIONLESS basis.

  REJECTS    Every committed *.invalid.json is refused for its specific tooth: a cohort
             with no declared baseline index; a measure declared decomposed=false; a
             cross-frame comparison on an ABSOLUTE basis.

  COHERENCE  systematic_share + idiosyncratic_share == 1 for every cohort (the variance
             partition is exhaustive).

Consume-by-reference: the RM-1 systematic/idiosyncratic factorization (risk_measures).
Deterministic, stdlib + jsonschema only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from open_ep_framework.benchmarking.index_relative import (  # noqa: E402
    IndexRelativeError, check_book, decompose, check_reconciliation,
)

SCHEMA = ROOT / "schemas" / "index_relative_cohort.schema.json"
EXAMPLES = ROOT / "examples" / "benchmarking"

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
    receipt = check_book(rec)
    for c in receipt["cohorts"]:
        # independent recompute of the reconciliation teeth
        src = next(x for x in rec["cohorts"] if x["cohort_id"] == c["cohort_id"])
        d = decompose(src["measure"]["series"], src["baseline_index"]["series"])
        check_reconciliation(d, src["measure"]["series"])
        share = c["systematic_share"] + c["idiosyncratic_share"]
        if abs(share - 1.0) > 1e-9:
            fail(f"{path.name}:{c['cohort_id']}: variance shares sum to {share} != 1")
    for cmp in receipt["comparisons"]:
        if not cmp["unit_free"]:
            fail(f"{path.name}: comparison {cmp['left']}/{cmp['right']} is not unit-free")
    ok(f"{path.name}: {receipt['cohort_count']} cohorts reconcile (level+variance); "
       f"{len(receipt['comparisons'])} cross-frame comparisons dimensionless")


def reject_invalid(path: Path, schema) -> None:
    rec = load(path)
    name = path.name
    errs = list(schema.iter_errors(rec))
    if errs:
        ok(f"{name}: REJECTED by schema ({errs[0].message[:70]})")
        return
    try:
        check_book(rec)
    except IndexRelativeError as e:
        ok(f"{name}: REJECTED -- {str(e)[:80]}")
        return
    fail(f"{name}: expected REJECTION but no tooth fired")


def main() -> int:
    schema = Draft202012Validator(load(SCHEMA))
    print("IRB-1 index-relative benchmarking contract:")
    for path in sorted(EXAMPLES.glob("*.valid.json")):
        verify_valid(path, schema)
    for path in sorted(EXAMPLES.glob("*.invalid.json")):
        reject_invalid(path, schema)
    print(f"\nOK: {_passes} benchmarking teeth passed (VERIFIES + REJECTS + COHERENCE).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
