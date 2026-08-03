import math

import pytest

from open_ep_framework.risk_adjusted_profit import (
    RiskAdjustedProfitError,
    evaluate_contract,
    run_risk_adjusted_profit,
)
from open_ep_framework.validation import validate_json_file

ECONOMIC = "examples/risk_adjusted_profit_economic.json"
EPISTEMIC = "examples/risk_adjusted_profit_epistemic.json"
NONRECONCILING = "examples/risk_adjusted_profit_nonreconciling.invalid.json"


def _credit_dist(seed=1, n=200):
    return {
        "credit": {
            "pd_long": 0.02, "lgd": 0.45, "ead": 1000000.0,
            "w_systematic": 0.7, "w_idiosyncratic": 0.3,
            "n_scenarios": n, "seed": seed,
        }
    }


def _base_arm():
    return {
        "arm_id": "unit",
        "hurdle_rate": 0.12,
        "return_components": {
            "revenue": 1000.0, "expected_loss": 100.0, "expense": 200.0,
            "funding_costs": 50.0, "funding_credits": 20.0, "taxes": 100.0,
        },
        "economic_capital": {
            "components": {"credit": 1000.0, "market": 500.0, "operating": 200.0,
                           "business": 100.0, "other": 50.0},
        },
        "risk_measure": {
            "kernel": "expected_shortfall", "alpha": 0.975,
            "capital_from_measure": False, "distribution": _credit_dist(),
        },
    }


# --------------------------------------------------------------------------- #
# fixtures validate + evaluate
# --------------------------------------------------------------------------- #
def test_fixtures_validate_against_schema():
    assert validate_json_file(ECONOMIC, "schemas/risk_adjusted_profit.schema.json")
    assert validate_json_file(EPISTEMIC, "schemas/risk_adjusted_profit.schema.json")
    assert validate_json_file(NONRECONCILING, "schemas/risk_adjusted_profit.schema.json")


def test_economic_contract_verifies_and_reconciles():
    result = run_risk_adjusted_profit(ECONOMIC)
    parent = result["arm"]
    assert parent["verdict"] == "verified"
    assert math.isclose(parent["economic_profit"], 210.0, abs_tol=1e-9)
    assert math.isclose(parent["nopat"], 570.0, abs_tol=1e-9)
    assert math.isclose(parent["raroc"], 570.0 / 3000.0, rel_tol=1e-12)
    assert parent["raroc_above_hurdle"] is True
    assert math.isclose(parent["capital_charge"], 360.0, abs_tol=1e-9)

    # IC-1 conservation reconciliation of the org cut.
    recon = result["decomposition"]["reconciliation"]
    assert recon["conservation"]["conserved"] is True
    assert math.isclose(recon["conservation"]["residual"], 0.0, abs_tol=1e-9)

    children = {c["arm_id"]: c for c in result["decomposition"]["children"]}
    assert children["markets"]["verdict"] == "verified"
    # Teeth: a value-destroying arm is FLAGGED, not silently accepted.
    assert children["retail"]["verdict"] == "flagged"
    assert children["retail"]["raroc_above_hurdle"] is False
    assert math.isclose(
        children["markets"]["economic_profit"] + children["retail"]["economic_profit"],
        parent["economic_profit"],
        abs_tol=1e-9,
    )


def test_receipt_carries_distribution_and_is_deterministic():
    r1 = run_risk_adjusted_profit(ECONOMIC)["arm"]
    r2 = run_risk_adjusted_profit(ECONOMIC)["arm"]
    assert r1["receipt_hash"] == r2["receipt_hash"]
    assert r1["receipt_hash"].startswith("sha256:")
    # Distribution + measure choice recorded for reproducibility/audit.
    rm = r1["risk_measure"]
    assert rm["kernel"] == "expected_shortfall"
    assert rm["coherent"] is True
    assert rm["distribution_id"].startswith("sha256:")
    assert rm["provisional"] is False


# --------------------------------------------------------------------------- #
# dual scoring (Economia Mentium)
# --------------------------------------------------------------------------- #
def test_epistemic_contract_uses_same_machinery():
    result = run_risk_adjusted_profit(EPISTEMIC)
    arm = result["arm"]
    assert result["scoring_mode"] == "epistemic"
    assert arm["verdict"] == "verified"
    assert math.isclose(arm["economic_profit"], 11.0, abs_tol=1e-9)
    assert math.isclose(arm["raroc"], 31.0 / 100.0, rel_tol=1e-12)
    # Labels reinterpret the same legs for epistemic profit.
    assert arm["interpretation"]["capital"] == "gkn_standing_capital"
    assert arm["interpretation"]["risk"] == "counter_test_uncertainty"


def test_epistemic_requires_provenance():
    spec = {
        "contract_id": "x", "as_of": "2026-08-03", "scoring_mode": "epistemic",
        "provenance": {"gkn_standing_ref": "gkn:..."},  # missing counter_test_ref
        "arm": _base_arm(),
    }
    with pytest.raises(RiskAdjustedProfitError, match="counter_test_ref"):
        evaluate_contract(spec)


# --------------------------------------------------------------------------- #
# teeth: rejections
# --------------------------------------------------------------------------- #
def test_nonreconciling_cut_is_rejected():
    with pytest.raises(RiskAdjustedProfitError, match="does not reconcile"):
        run_risk_adjusted_profit(NONRECONCILING)


def test_no_risk_measure_is_rejected():
    arm = _base_arm()
    del arm["risk_measure"]
    spec = {"contract_id": "x", "as_of": "d", "scoring_mode": "economic", "arm": arm}
    with pytest.raises(RiskAdjustedProfitError, match="no risk measure"):
        evaluate_contract(spec)


def test_no_economic_capital_is_rejected():
    arm = _base_arm()
    arm["economic_capital"] = {"components": {"credit": 0.0, "market": 0.0}}
    spec = {"contract_id": "x", "as_of": "d", "scoring_mode": "economic", "arm": arm}
    with pytest.raises(RiskAdjustedProfitError, match="no .*economic capital"):
        evaluate_contract(spec)


def test_noncoherent_measure_as_capital_requires_override():
    arm = _base_arm()
    arm["economic_capital"] = {"components": {}}
    arm["risk_measure"] = {
        "kernel": "var", "alpha": 0.99, "capital_from_measure": True,
        "allow_noncoherent_capital": False, "distribution": _credit_dist(),
    }
    spec = {"contract_id": "x", "as_of": "d", "scoring_mode": "economic", "arm": arm}
    with pytest.raises(RiskAdjustedProfitError, match="non-coherent"):
        evaluate_contract(spec)


def test_noncoherent_measure_as_capital_with_override_warns():
    arm = _base_arm()
    arm["economic_capital"] = {"components": {}}
    arm["risk_measure"] = {
        "kernel": "var", "alpha": 0.99, "capital_from_measure": True,
        "allow_noncoherent_capital": True, "distribution": _credit_dist(),
    }
    spec = {"contract_id": "x", "as_of": "d", "scoring_mode": "economic", "arm": arm}
    result = evaluate_contract(spec)
    warnings = " ".join(result["arm"]["warnings"])
    assert "coherence warning" in warnings
    # VaR supplied the credit economic-capital component.
    assert result["arm"]["economic_capital"]["credit"] > 0.0


def test_coherent_measure_can_supply_capital():
    arm = _base_arm()
    arm["economic_capital"] = {"components": {}}
    arm["risk_measure"] = {
        "kernel": "expected_shortfall", "alpha": 0.99, "capital_from_measure": True,
        "distribution": _credit_dist(),
    }
    spec = {"contract_id": "x", "as_of": "d", "scoring_mode": "economic", "arm": arm}
    result = evaluate_contract(spec)
    assert result["arm"]["economic_capital"]["credit"] > 0.0
    assert result["arm"]["verdict"] in ("verified", "flagged")


def test_unknown_decomposition_cut_is_rejected():
    import json
    with open(ECONOMIC) as f:
        spec = json.load(f)
    spec["decomposition"]["cut"] = "not_a_real_cut"
    with pytest.raises(RiskAdjustedProfitError, match="unknown decomposition cut"):
        evaluate_contract(spec)
