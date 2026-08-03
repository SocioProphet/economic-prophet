#!/usr/bin/env python3
"""Validate the silent_testbench contract (audit-only falsification of "Silent Weapons").

Teeth in BOTH directions -- a control that never fires is suspect.

  VERIFIES   The Phase-1 estimator demonstration shows shock-test == OLS == VAR impulse
             response == the ground-truth cross-price elasticity (RELABELING). Each valid
             claim fixture's asserted verdict MATCHES the verdict recomputed by the Phase-2
             confrontation on the cited reference fixtures, and its scope is pinned to
             audit_only_falsification_not_operationalization.

  REJECTS    Every *.invalid.json is refused for its specific tooth:
               * a MECH-1 record claiming it BEATS the econometric baseline (relabeling flag);
               * a MECH-4 record claiming the strong debt->depopulation form is NOT_FALSIFIED;
               * a MECH-2 record claiming the behavioural coefficient is VERIFIED with no
                 out-of-sample test;
               * an interpretation that says reproducing the mechanism CONFIRMS the conspiracy;
               * a wrong scope pin.

Deterministic, stdlib + jsonschema only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from open_ep_framework.silent_testbench.confront import (  # noqa: E402
    run_confrontation,
)
from open_ep_framework.silent_testbench.shock_estimator import (  # noqa: E402
    DemandSystem, ShockTestError, demonstrate_estimator_is_var,
    reject_conspiracy_overclaim,
)

SCHEMA = ROOT / "schemas" / "silent_testbench_claim.schema.json"
EXAMPLES = ROOT / "examples" / "silent_testbench"
SCOPE = "audit_only_falsification_not_operationalization"

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


# --------------------------------------------------------------------------- #
# Phase 1: the estimator=VAR/impulse demonstration (VERIFIES).
# --------------------------------------------------------------------------- #
def verify_estimator_is_var() -> None:
    system = DemandSystem(
        goods=("gasoline", "transit"),
        elasticities=[[-0.30, 0.10], [0.15, -0.45]],
        log_intercepts=[2.0, 1.5],
    )
    demo = demonstrate_estimator_is_var(system, [3.0, 2.0])
    if not demo["equivalent"]:
        fail(f"estimator demonstration: NOT equivalent (max devs {demo})")
    ok("Phase-1: shock-test == OLS == VAR impulse response == true cross-price elasticity "
       f"(max dev {max(demo['max_dev_shock_vs_truth'], demo['max_dev_ols_vs_truth'], demo['max_dev_irf_vs_shocktest']):.1e}) "
       "-> RELABELING of ordinary econometrics")


# --------------------------------------------------------------------------- #
# Phase 2: recomputed verdicts (VERIFIES) + per-fixture claim teeth.
# --------------------------------------------------------------------------- #
def verify_confrontation_verdicts() -> dict:
    report = run_confrontation()
    if not report["all_verdicts_as_expected"]:
        fail(f"confrontation verdicts off-spec: {report['verdict_summary']}")
    for mid, verdict in report["verdict_summary"].items():
        ok(f"Phase-2 {mid}: {verdict}")
    return report["verdict_summary"]


def verify_claim_valid(path: Path, schema, recomputed: dict) -> None:
    rec = load(path)
    errs = sorted(schema.iter_errors(rec), key=lambda e: str(e.path))
    if errs:
        fail(f"{path.name}: schema-invalid: {errs[0].message}")
    if rec["scope"] != SCOPE:
        fail(f"{path.name}: scope not pinned to {SCOPE}")
    reject_conspiracy_overclaim(rec.get("interpretation"))
    expected = recomputed[rec["mechanism_id"]]
    if rec["asserted_verdict"] != expected:
        fail(f"{path.name}: asserted {rec['asserted_verdict']} != recomputed {expected}")
    # MECH-1 honesty: a valid record must not claim to beat the baseline
    if rec["mechanism_id"] == "MECH-1-shock-test-estimator" and rec.get("beats_econometric_baseline", False):
        fail(f"{path.name}: MECH-1 valid record must not claim to beat the baseline")
    ok(f"{path.name}: asserted verdict '{rec['asserted_verdict']}' matches recomputed")


def reject_claim_invalid(path: Path, schema, recomputed: dict) -> None:
    rec = load(path)
    name = path.name
    errs = list(schema.iter_errors(rec))
    if errs:
        ok(f"{name}: REJECTED by schema ({errs[0].message[:70]})")
        return
    # conspiracy over-claim tooth
    try:
        reject_conspiracy_overclaim(rec.get("interpretation"))
    except ShockTestError:
        ok(f"{name}: REJECTED -- reproducing the mechanism does not confirm the conspiracy")
        return
    # relabeling flag: MECH-1 claiming to beat the baseline
    if rec["mechanism_id"] == "MECH-1-shock-test-estimator" and rec.get("beats_econometric_baseline", False):
        ok(f"{name}: REJECTED -- relabeling flag: shock-test claimed to BEAT the baseline")
        return
    # verdict-vs-recomputed mismatch (covers MECH-4 NOT_FALSIFIED, MECH-2 VERIFIED, etc.)
    expected = recomputed[rec["mechanism_id"]]
    if rec["asserted_verdict"] != expected:
        ok(f"{name}: REJECTED -- asserted '{rec['asserted_verdict']}' != recomputed '{expected}'")
        return
    fail(f"{name}: expected REJECTION but no tooth fired")


def main() -> int:
    schema = Draft202012Validator(load(SCHEMA))

    print("Silent-Weapons testbench -- Phase 1 (estimator == VAR/impulse):")
    verify_estimator_is_var()

    print("Silent-Weapons testbench -- Phase 2 (per-mechanism confrontation):")
    recomputed = verify_confrontation_verdicts()

    print("Silent-Weapons testbench -- claim fixtures (VERIFIES):")
    for path in sorted(EXAMPLES.glob("claim.*.valid.json")):
        verify_claim_valid(path, schema, recomputed)

    print("Silent-Weapons testbench -- claim fixtures (REJECTS):")
    for path in sorted(EXAMPLES.glob("claim.*.invalid.json")):
        reject_claim_invalid(path, schema, recomputed)

    print(f"\nOK: {_passes} silent_testbench teeth passed (VERIFIES + REJECTS).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
