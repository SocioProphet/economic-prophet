"""CLI: emit the silent_testbench audit receipt (Phase 1 demonstration + Phase 2 verdicts).

    python -m open_ep_framework.silent_testbench --audit silent_testbench_audit.json

Writes a deterministic JSON audit combining the estimator=VAR/impulse demonstration and the
per-mechanism confrontation verdicts. Audit-only; no live or shared writes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .confront import run_confrontation
from .shock_estimator import DemandSystem, demonstrate_estimator_is_var

# A small two-good demand system (gasoline, public-transit) with own-price elasticities on
# the diagonal and a substitute cross-price off-diagonal -- purely to exercise the
# estimator=VAR demonstration deterministically.
_DEMO_SYSTEM = DemandSystem(
    goods=("gasoline", "transit"),
    elasticities=[[-0.30, 0.10], [0.15, -0.45]],
    log_intercepts=[2.0, 1.5],
)
_DEMO_PRICES = [3.0, 2.0]


def build_audit() -> dict:
    demo = demonstrate_estimator_is_var(_DEMO_SYSTEM, _DEMO_PRICES)
    confrontation = run_confrontation()
    return {
        "run_id": "silent-testbench-audit-001",
        "scope": "audit_only_falsification_not_operationalization",
        "phase1_estimator_is_var_demonstration": demo,
        "phase2_confrontation": confrontation,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="open_ep_framework.silent_testbench")
    parser.add_argument("--audit", type=str, default="",
                        help="path to write the JSON audit receipt")
    args = parser.parse_args(argv)
    audit = build_audit()
    text = json.dumps(audit, indent=2, default=str)
    if args.audit:
        Path(args.audit).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    # exit non-zero if any verdict is off-spec (a control that never fires is suspect)
    return 0 if audit["phase2_confrontation"]["all_verdicts_as_expected"] else 1


if __name__ == "__main__":
    sys.exit(main())
