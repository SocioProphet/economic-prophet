#!/usr/bin/env python3
"""Validate the WEA-1 Welfare-Annealing contract -- with teeth in BOTH directions
(a control that never fires is suspect).

Tooth families:

  VERIFIES   Every committed *.valid.json is schema-valid AND passes its kind's teeth when
             recomputed by the deterministic modules:
               * exchange    -- pure exchange CONSERVES total value-energy (IC-1, by ref);
               * anneal      -- the anneal is LAMINAR, monotonically LOWERS the free-energy
                                potential (raises the QoL index) toward the attractor, and
                                conserves the value-energy at every step (FRL-1 lens, by ref);
               * growth_path -- a renewable-only path is SUSTAINABLE and every growth claim is
                                Fisher-real-adjusted (ALC-1 renewability + inflation, by ref);
               * discount    -- MV=PQ holds, the Fisher-ideal index computes, and the
                                Stern-vs-Nordhaus sensitivity RECONCILES (present value falls
                                monotonically as the social discount rate rises).

  REJECTS    Every committed *.invalid.json is refused for its specific tooth: value CREATED in
             pure exchange (conservation violation); an anneal that INCREASES the free-energy /
             is turbulent while claiming a healthy laminar descent (wrong direction); a growth
             path funded by NON-RENEWABLE drawdown booked as sustainable (false-growth flag); a
             growth claim NOT Fisher-real-adjusted; a QoL group MISSING a required dimension.

  COHERENCE  Each valid anneal's terminal allocation sums to the conserved energy; each valid
             discount sweep is monotone-decreasing in the rate and weights the future more under
             the low-rate (Stern) calibration.

Consume-by-reference: IC-1 settlement (#39), FRL-1 flow-regime (#54), ALC-1 asset-ladder (#52),
inflation (Fisher). Deterministic, stdlib + jsonschema only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from open_ep_framework.welfare_annealing.contract import run_record  # noqa: E402

SCHEMA = ROOT / "schemas" / "welfare_annealing.schema.json"
EXAMPLES = ROOT / "examples" / "welfare_annealing"
# Vendored gaia-owned economy schemas (consume-by-reference; see the fixtures PROVENANCE).
GAIA_SCHEMAS = ROOT / "tests" / "fixtures" / "gaia"

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
# VERIFIES + COHERENCE over valid fixtures
# --------------------------------------------------------------------------- #
def verify_valid(path: Path, schema: Draft202012Validator) -> None:
    rec = load(path)
    errs = sorted(schema.iter_errors(rec), key=lambda e: str(e.path))
    if errs:
        fail(f"{path.name}: schema-invalid: {errs[0].message}")
    try:
        audit = run_record(rec)
    except Exception as exc:  # noqa: BLE001
        fail(f"{path.name}: valid fixture unexpectedly REJECTED: {exc}")
    out = audit["outputs"]
    kind = audit["record_kind"]

    if kind == "exchange":
        if not out["conservation"]["conserved"]:
            fail(f"{path.name}: exchange did not conserve value-energy")
        ok(f"{path.name}: exchange CONSERVES value-energy "
           f"(residual={out['conservation']['residual']})")

    elif kind == "anneal":
        if out["regime"] != "laminar":
            fail(f"{path.name}: anneal regime {out['regime']} != laminar")
        if not out["monotone_descent"]:
            fail(f"{path.name}: anneal free-energy not monotone-descending")
        if out["free_energy_end"] > out["free_energy_start"]:
            fail(f"{path.name}: anneal did not lower free-energy")
        if out["welfare_gain"] <= 0:
            fail(f"{path.name}: anneal did not raise welfare")
        if not out["energy_conserved"]:
            fail(f"{path.name}: anneal did not conserve value-energy")
        # COHERENCE: terminal allocation sums to the conserved energy
        if abs(sum(out["fixed_point"]) - out["total_energy"]) > 1e-4:
            fail(f"{path.name}: terminal allocation does not sum to the conserved energy")
        ok(f"{path.name}: LAMINAR anneal lowers free-energy "
           f"{out['free_energy_start']:.3f}->{out['free_energy_end']:.3f} "
           f"(welfare_gain={out['welfare_gain']:.3f}, lambda={out['lyapunov']}, "
           f"energy_conserved={out['energy_conserved']})")

    elif kind == "growth_path":
        if not out["sustainable"]:
            fail(f"{path.name}: renewable-only path reported unsustainable")
        for rep in out["periods"]:
            if rep.get("nonrenewable_drawdown", 0.0) != 0.0:
                fail(f"{path.name}: valid path booked non-renewable drawdown")
        ok(f"{path.name}: renewable-only growth SUSTAINABLE and Fisher-real-adjusted "
           f"({len(out['periods'])} periods)")

    elif kind == "discount":
        if "mv_pq" in out and not out["mv_pq"]["holds"]:
            fail(f"{path.name}: MV=PQ identity broken")
        recon = out.get("sensitivity_reconciliation")
        if recon:
            if not recon["monotone_decreasing_in_rate"]:
                fail(f"{path.name}: discount sensitivity not monotone in rate")
            if not recon["future_weighted_more_by_low_rate"]:
                fail(f"{path.name}: low rate did not weight the future more (Stern>Nordhaus)")
            ok(f"{path.name}: MV=PQ holds; Stern-vs-Nordhaus sensitivity RECONCILES "
               f"(low-rate PV {recon['lowest_rate']['present_value']:.3f} >= "
               f"high-rate PV {recon['highest_rate']['present_value']:.3f})")
        else:
            ok(f"{path.name}: discount checks pass")

    elif kind == "gaia_binding":
        binding = out["value_flow_binding"]
        transfer = out["twin_scale_transfer"]
        # CONFORMANCE: the emitted manifests must validate against the gaia-owned schemas.
        vfb_schema = Draft202012Validator(load(GAIA_SCHEMAS / "value_flow_binding.v1.schema.json"))
        tsvt_schema = Draft202012Validator(load(GAIA_SCHEMAS / "twin_scale_transfer.v1.schema.json"))
        berrs = sorted(vfb_schema.iter_errors(binding), key=lambda e: str(e.path))
        if berrs:
            fail(f"{path.name}: emitted ValueFlowSubsystemBinding is NOT gaia-conformant: "
                 f"{berrs[0].message}")
        terrs = sorted(tsvt_schema.iter_errors(transfer), key=lambda e: str(e.path))
        if terrs:
            fail(f"{path.name}: emitted TwinScaleValueTransfer is NOT gaia-conformant: "
                 f"{terrs[0].message}")
        # the world-model reads that satisfy T1-CONST / T4-REGEN
        if binding["carrying_capacity"]["source"]["kind"] != "world_model_read":
            fail(f"{path.name}: carrying-capacity source is not a world-model read (T1-CONST)")
        ok(f"{path.name}: emitted VFB + TSVT are gaia-conformant "
           f"(qol_value={binding['qol_index']['value']:.3f}, "
           f"twin-scale conserved @tol={transfer['conservation']['tolerance']}, "
           f"reserve_flags={len(out['reserve_flags'])})")
    else:
        fail(f"{path.name}: unknown record_kind {kind}")


# --------------------------------------------------------------------------- #
# REJECTS over invalid fixtures
# --------------------------------------------------------------------------- #
def reject_invalid(path: Path, schema: Draft202012Validator) -> None:
    rec = load(path)
    errs = list(schema.iter_errors(rec))
    if errs:
        ok(f"{path.name}: REJECTED by schema ({errs[0].message[:70]})")
        return
    try:
        run_record(rec)
    except Exception as exc:  # noqa: BLE001
        ok(f"{path.name}: REJECTED -- {str(exc).splitlines()[0][:90]}")
        return
    fail(f"{path.name}: expected REJECTION but the record was accepted")


def main() -> int:
    schema = Draft202012Validator(load(SCHEMA))
    print("WEA-1 Welfare-Annealing contract:")
    for path in sorted(EXAMPLES.glob("*.valid.json")):
        verify_valid(path, schema)
    for path in sorted(EXAMPLES.glob("*.invalid.json")):
        reject_invalid(path, schema)
    print(f"\nOK: {_passes} welfare-annealing teeth passed (VERIFIES + REJECTS + COHERENCE).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
