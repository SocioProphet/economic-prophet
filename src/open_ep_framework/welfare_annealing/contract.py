"""WEA-1 Welfare-Annealing contract: orchestrate the teeth over a record and emit a receipt.

This is the top-level contract-with-teeth. It reads a welfare-annealing record (one of four
``record_kind``s), applies the relevant teeth, and emits a signed receipt using the estate
receipt-spine convention (canonical JSON, sha256, ``sha256:`` prefix -- the same discipline as
``settlement``). Measurement / simulation / audit only: no live or shared-state writes, no
token issuance -- a conservation + welfare-annealing checker and receipt emitter.

The record kinds:
  * ``exchange``    -- a pure exchange; VERIFIES value-energy conservation (IC-1, by ref).
  * ``anneal``      -- a welfare anneal over allocations; VERIFIES monotone free-energy
                       descent to a laminar attractor, energy conserved at every step, and
                       the FRL-1 regime matches what the record declares.
  * ``growth_path`` -- a multi-period growth path; VERIFIES renewable-only growth is
                       sustainable and Fisher-real-adjusted; FLAGS non-renewable drawdown
                       booked as sustainable, and un-deflated growth claims.
  * ``discount``    -- the social-discount-rate sweep; VERIFIES MV=PQ, the Fisher-ideal
                       index, and that the Stern-vs-Nordhaus sensitivity reconciles.

WEA-1 is the estate's named "better framework": the normative INVERSE of "Silent Weapons for
Quiet Wars" over the SAME value-as-energy physics -- same conservation law, same free-energy /
laminar-turbulent dynamics, objective flipped from elite-control to global welfare. The SILENT
epistemic-firewall (Phase 4) contrasts a control-max objective against THIS welfare objective
over the same conserved energy.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .anneal import (
    AnnealError, assert_descends, regime_for_taxonomy, run_anneal,
)
from .discount import (
    assert_mv_pq, assert_real_adjusted, assert_sensitivity_reconciles,
    discount_sensitivity, fisher_ideal_index,
)
from .energy import assert_exchange_conserves, assert_sustainable
from .gaia_binding import emit_manifests
from .qol import groups_from_records, qol_index

CONTRACT = "WEA-1"
_SCHEMA = "schemas/welfare_annealing.schema.json"


class WelfareAnnealingError(ValueError):
    """Raised when a welfare-annealing record violates the contract (REJECTED)."""


def _sha256(text: str) -> str:
    """Estate receipt-spine hash: ``sha256:`` + hex digest."""
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# --------------------------------------------------------------------------- #
# per-kind evaluators
# --------------------------------------------------------------------------- #
def _eval_exchange(record: dict) -> dict:
    ledger = assert_exchange_conserves(record["exchange"])
    return {"conservation": ledger, "verdict": "verified"}


def _eval_anneal(record: dict) -> dict:
    spec = record["anneal"]
    groups = groups_from_records(spec["groups"])
    x0 = list(spec["initial_allocation"])
    result = run_anneal(groups, x0, float(spec["learning_rate"]), int(spec["steps"]),
                        energy=spec.get("total_energy"))

    # The FRL-1 lens must agree with what the record declares. A record that CLAIMS a
    # healthy laminar descent while the recomputed anneal is turbulent (it increases the
    # free-energy / never settles) is a mis-declaration and is REJECTED here.
    declared = spec.get("expect_regime")
    if declared is not None and declared != result.regime:
        raise AnnealError(
            f"REJECTED: declared regime {declared!r} != recomputed {result.regime!r} "
            f"(lambda={result.lyapunov}, settled={result.settled}, "
            f"monotone_descent={result.monotone_descent})"
        )
    taxonomy = spec.get("memory_regime")
    if taxonomy is not None and regime_for_taxonomy(taxonomy) != result.regime:
        raise AnnealError(
            f"REJECTED: memory-mesh taxonomy {taxonomy!r} maps to "
            f"{regime_for_taxonomy(taxonomy)!r} but anneal is {result.regime!r}"
        )

    # A valid welfare anneal is a laminar, monotone free-energy descent to the attractor,
    # conserving the total value-energy at every step. Each failing condition is a tooth.
    assert_descends(result)  # REJECT a wrong-direction (free-energy-increasing) anneal
    if result.regime != "laminar":
        raise AnnealError(
            "REJECTED: the anneal did not reach a laminar welfare attractor "
            f"(regime={result.regime}, settled={result.settled}); a manipulated / "
            "over-driven anneal is turbulent and is not a valid welfare descent."
        )
    if not result.energy_conserved:
        raise AnnealError("REJECTED: anneal did not conserve total value-energy")
    return {
        "regime": result.regime,
        "lyapunov": result.lyapunov,
        "settled": result.settled,
        "monotone_descent": result.monotone_descent,
        "energy_conserved": result.energy_conserved,
        "total_energy": result.total_energy,
        "welfare_start": result.welfare[0],
        "welfare_end": result.welfare[-1],
        "welfare_gain": round(result.welfare_gain, 10),
        "free_energy_start": result.free_energy[0],
        "free_energy_end": result.free_energy[-1],
        "fixed_point": [round(v, 6) for v in result.fixed_point],
        "qol_index_structural": round(qol_index(spec["groups"]), 6),
        "verdict": "verified",
    }


def _eval_growth_path(record: dict) -> dict:
    periods = record["growth_path"]["periods"]
    reports = []
    for i, period in enumerate(periods):
        rep = assert_sustainable(period)  # FLAG false growth
        if "nominal_growth" in period and "real_growth" in period:
            rep.update(assert_real_adjusted(period))  # REJECT un-deflated growth
        rep["period"] = i
        reports.append(rep)
    return {"periods": reports,
            "sustainable": all(r["is_sustainable"] for r in reports),
            "verdict": "verified"}


def _eval_discount(record: dict) -> dict:
    spec = record["discount"]
    out = {"verdict": "verified"}
    if "mv_pq" in spec:
        mv = spec["mv_pq"]
        out["mv_pq"] = assert_mv_pq(float(mv["M"]), float(mv["V"]),
                                    float(mv["P"]), float(mv["Q"]))
    if "fisher_ideal" in spec:
        fi = spec["fisher_ideal"]
        out["fisher_ideal_index"] = round(
            fisher_ideal_index(fi["p0"], fi["q0"], fi["p1"], fi["q1"]), 8)
    if "sensitivity" in spec:
        sens = spec["sensitivity"]
        scenarios = discount_sensitivity(
            float(sens["future_qol"]), float(sens["horizon"]), float(sens["g"]),
            sens["scenarios"])
        out["discount_scenarios"] = [
            {"name": s.name, "delta": s.delta, "eta": s.eta,
             "rate": round(s.rate, 6), "present_value": round(s.present_value, 6)}
            for s in scenarios
        ]
        out["sensitivity_reconciliation"] = assert_sensitivity_reconciles(scenarios)
    return out


def _eval_gaia_binding(record: dict) -> dict:
    """Emit the two GAIA value-flow manifests from this welfare run and enforce the gaia
    teeth (T1-CONST, T4-REGEN, T3-QOL, T2-CONSERVE) on the EP side; T1-RESERVE breaches are
    admitted-with-flag. The emitted manifests conform to value_flow_binding.v1 /
    twin_scale_transfer.v1 so gaia's contract enforces on REAL EP runs, not just fixtures."""
    gaia = dict(record["gaia"])
    gaia.setdefault("as_of", record.get("as_of", ""))
    manifests = emit_manifests(gaia)
    return {
        "value_flow_binding": manifests["value_flow_binding"],
        "twin_scale_transfer": manifests["twin_scale_transfer"],
        "reserve_flags": manifests["reserve_flags"],
        "verdict": "verified",
    }


_EVALUATORS = {
    "exchange": _eval_exchange,
    "anneal": _eval_anneal,
    "growth_path": _eval_growth_path,
    "discount": _eval_discount,
    "gaia_binding": _eval_gaia_binding,
}


# --------------------------------------------------------------------------- #
# top-level run + receipt
# --------------------------------------------------------------------------- #
def run_record(record: dict) -> dict:
    """Apply the teeth for ``record["record_kind"]`` and return the audit body.

    Re-raises the specific typed error (Settlement/ValueEnergy/Anneal/Discount/QoL) so the
    failing tooth is legible in CI."""
    kind = record.get("record_kind")
    if kind not in _EVALUATORS:
        raise WelfareAnnealingError(
            f"REJECTED: unknown record_kind {kind!r}; expected one of {sorted(_EVALUATORS)}"
        )
    outputs = _EVALUATORS[kind](record)
    return {
        "contract": CONTRACT,
        "record_kind": kind,
        "record_id": record.get("record_id", ""),
        "as_of": record.get("as_of", ""),
        "outputs": outputs,
    }


def emit_receipt(record: dict) -> dict:
    """Run the record and wrap the audit in a receipt-spine-hashed receipt."""
    body = run_record(record)
    body["input_hash"] = _sha256(_canonical(record))
    receipt = dict(body)
    receipt["output_hash"] = _sha256(_canonical(body))
    receipt["receipt_hash"] = _sha256(_canonical(receipt))
    return receipt


def load_record(path: str) -> dict:
    return json.loads(Path(path).read_text())


def run_file(path: str) -> dict:
    return emit_receipt(load_record(path))


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the WEA-1 Welfare-Annealing contract over a record (with teeth).")
    parser.add_argument("--record", required=True, help="Path to a welfare-annealing record JSON.")
    parser.add_argument("--receipt", default=None, help="Optional path to write the receipt JSON.")
    args = parser.parse_args(argv)

    receipt = run_file(args.record)
    text = json.dumps(receipt, indent=2, sort_keys=True)
    if args.receipt:
        Path(args.receipt).write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
