import copy
import json
import math

import pytest

from open_ep_framework.crypto.valuation import (
    CryptoValuationError,
    evaluate_valuation,
    run_valuation,
)
from open_ep_framework.validation import validate_json_file

FEE_BEARING = "examples/crypto_valuation_fee_bearing.json"
DCF_WRONG = "examples/crypto_valuation_dcf_wrong_model.invalid.json"


def _spec():
    with open(FEE_BEARING) as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# schema
# --------------------------------------------------------------------------- #
def test_fixtures_validate_against_schema():
    assert validate_json_file(FEE_BEARING, "schemas/crypto_asset_valuation.schema.json")
    assert validate_json_file(DCF_WRONG, "schemas/crypto_asset_valuation.schema.json")


# --------------------------------------------------------------------------- #
# VERIFIES
# --------------------------------------------------------------------------- #
def test_fee_bearing_chain_gets_finite_accretive_modified_ep():
    result = run_valuation(FEE_BEARING)
    ep = result["modified_economic_profit"]
    assert math.isfinite(ep["modified_ep"])
    # fee_revenue - security_cost - emission_dilution - risk_capital, each present.
    assert ep["fee_revenue"] > 0
    assert ep["security_cost"] > 0
    assert ep["risk_capital"] > 0
    # Deflationary token (burn > emission) -> negative dilution (accretive).
    assert ep["net_new_tokens"] < 0
    assert ep["emission_dilution"] < 0
    assert result["verdict"] == "accretive"
    # Identity holds exactly.
    assert math.isclose(
        ep["modified_ep"],
        ep["fee_revenue"] - ep["security_cost"] - ep["emission_dilution"] - ep["risk_capital"],
        rel_tol=1e-12,
    )


def test_network_value_reconciles_to_inputs():
    result = run_valuation(FEE_BEARING)
    nv = result["network_value"]
    spec = _spec()
    n = spec["onchain"]["active_addresses"]
    k = spec["network"]["metcalfe_coefficient"]
    supply = spec["tokenomics"]["circulating_supply"]
    price = spec["tokenomics"]["price"]
    tx = spec["onchain"]["annual_tx_volume"]
    # Metcalfe value proportional to n^2.
    assert math.isclose(nv["metcalfe_value"], k * n * n, rel_tol=1e-12)
    # NVT == market_cap / annual tx volume (the crypto P/E).
    assert math.isclose(nv["market_cap"], supply * price, rel_tol=1e-12)
    assert math.isclose(nv["nvt_ratio"], (supply * price) / tx, rel_tol=1e-12)
    assert math.isclose(nv["metcalfe_implied_price"], (k * n * n) / supply, rel_tol=1e-12)


def test_risk_capital_consumes_the_estate_risk_kernel():
    result = run_valuation(FEE_BEARING)
    rc = result["modified_economic_profit"]["risk"]
    # Coherent Expected Shortfall over a reflexive fat-tailed F (RM-1 kernel).
    assert rc["coherent"] is True
    assert rc["es_fraction"] > 0
    assert rc["lpm2_downside"] > 0
    assert rc["reflexivity"] == 0.35
    assert rc["distribution_id"].startswith("sha256:")
    assert math.isclose(rc["risk_capital"], rc["es_fraction"] * rc["risk_notional"], rel_tol=1e-12)


def test_reflexivity_widens_tail_risk_capital():
    # A control that never moves is suspect: more reflexivity -> larger ES risk_capital.
    base = _spec()
    calm = copy.deepcopy(base)
    calm["risk"]["reflexivity"] = 0.0
    hot = copy.deepcopy(base)
    hot["risk"]["reflexivity"] = 1.5
    rc_calm = evaluate_valuation(calm)["modified_economic_profit"]["risk_capital"]
    rc_hot = evaluate_valuation(hot)["modified_economic_profit"]["risk_capital"]
    assert rc_hot > rc_calm


def test_memetic_value_is_evidence_bound_and_positive():
    result = run_valuation(FEE_BEARING)
    m = result["memetic_value"]
    assert m["virality"] > 1.0  # latest spike beats its own history
    assert m["epistemic_delta_bits"] > 0.0
    assert m["information_value"] > 0.0
    assert m["evidence_count"] == 3


def test_receipt_is_deterministic():
    r1 = run_valuation(FEE_BEARING)
    r2 = run_valuation(FEE_BEARING)
    assert r1["receipt_hash"] == r2["receipt_hash"]
    assert r1["receipt_hash"].startswith("sha256:")


# --------------------------------------------------------------------------- #
# REJECTS (teeth)
# --------------------------------------------------------------------------- #
def test_dcf_on_no_cashflow_token_is_rejected():
    # Wrong-model guard: DCF cannot be applied to a token with no cash flows.
    with pytest.raises(CryptoValuationError, match="no cash flows"):
        run_valuation(DCF_WRONG)


def test_cash_flow_bearing_token_may_use_dcf():
    # The guard is precise: it fires only for NO-cash-flow tokens, not always.
    spec = _spec()
    spec["valuation_method"] = "dcf"
    spec["tokenomics"]["cash_flow_bearing"] = True
    result = evaluate_valuation(spec)
    assert result["valuation_method"] == "dcf"


def test_emission_dilution_may_not_be_silently_dropped():
    spec = _spec()
    # Positive net emission but no price == unpriced dilution (silent inflation).
    spec["tokenomics"]["emission_rate"] = 0.20
    spec["tokenomics"]["burn_tokens_annual"] = 0
    del spec["tokenomics"]["price"]
    with pytest.raises(CryptoValuationError, match="silent inflation|dilution"):
        evaluate_valuation(spec)


def test_higher_emission_lowers_modified_ep():
    # Silent-inflation direction: more issuance -> more dilution -> lower modified-EP.
    low = _spec()
    low["tokenomics"]["emission_rate"] = 0.005
    low["tokenomics"]["burn_tokens_annual"] = 0
    high = copy.deepcopy(low)
    high["tokenomics"]["emission_rate"] = 0.30
    ep_low = evaluate_valuation(low)["modified_economic_profit"]["modified_ep"]
    ep_high = evaluate_valuation(high)["modified_economic_profit"]["modified_ep"]
    assert ep_high < ep_low


def test_bare_memetic_claim_without_evidence_is_rejected():
    spec = _spec()
    spec["memetic"] = {"attention_series": [1, 2, 3], "evidence": []}
    with pytest.raises(CryptoValuationError, match="bare narrative|evidence"):
        evaluate_valuation(spec)

    spec2 = _spec()
    spec2["memetic"] = {"attention_series": [], "evidence": [{"metric": "x", "source": "y"}]}
    with pytest.raises(CryptoValuationError, match="attention series|evidence"):
        evaluate_valuation(spec2)


def test_unknown_valuation_method_is_rejected():
    spec = _spec()
    spec["valuation_method"] = "astrology"
    with pytest.raises(CryptoValuationError, match="unknown valuation_method"):
        evaluate_valuation(spec)
