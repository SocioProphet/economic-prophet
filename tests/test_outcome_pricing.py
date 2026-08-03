"""Teeth for the outcome-based wisdom-services pricing contract (OPX-1).

VERIFIES: a verified-outcome engagement prices to a positive risk-adjusted value;
the mesh contributions sum to the total price (conservation); certified truth
earns full VoI while speculative is discounted.
REJECTS: no verified outcome-receipt (time-and-materials); truth priced above its
VoI / on uncertified knowledge; a mesh split that does not sum to P; a price that
ignores the outcome distribution; a false-graded outcome not clawed back.
"""
import copy
import json

import pytest

from open_ep_framework.outcome_pricing import (
    OutcomePricingError,
    price_engagement,
    run_outcome_pricing,
)
from open_ep_framework.validation import validate_json_file

SCHEMA = "schemas/outcome_pricing.schema.json"
VALID = "examples/outcome_pricing_engagement.json"
NO_RECEIPT = "examples/outcome_pricing_no_receipt.invalid.json"
TRUTH_OVER_VOI = "examples/outcome_pricing_truth_over_voi.invalid.json"
NONCONSERVING = "examples/outcome_pricing_nonconserving_split.invalid.json"
NO_RISK = "examples/outcome_pricing_no_risk_adjust.invalid.json"
FALSE_NOT_CLAWED = "examples/outcome_pricing_false_not_clawed.invalid.json"

ALL_FIXTURES = [VALID, NO_RECEIPT, TRUTH_OVER_VOI, NONCONSERVING, NO_RISK, FALSE_NOT_CLAWED]


def _valid_spec():
    return json.loads(open(VALID).read())


# --------------------------------------------------------------------------- #
# fixtures are all schema-valid: the ENGINE, not the schema, enforces the teeth
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", ALL_FIXTURES)
def test_fixtures_validate_against_schema(path):
    assert validate_json_file(path, SCHEMA)


# --------------------------------------------------------------------------- #
# VERIFIES
# --------------------------------------------------------------------------- #
def test_verified_engagement_prices_to_positive_risk_adjusted_value():
    result = run_outcome_pricing(VALID)
    d = result["decomposition"]
    # a genuine, verified outcome prices to a positive risk-adjusted value
    assert d["risk_adjust"]["risk_adjusted_value"] > 0
    assert d["equilibrium"]["joint_surplus"] > 0
    assert result["engagement_price"] > 0
    # the price sits between the provider cost-floor and the client value-ceiling
    assert d["equilibrium"]["provider_cost_floor"] <= result["engagement_price"] <= d["equilibrium"]["client_value_ceiling"]
    # every stage of the decomposition is present
    for stage in ("outcome_value", "value_of_information", "risk_adjust",
                  "complexity_time_discount", "equilibrium", "mesh_split"):
        assert stage in d
    assert result["receipt_id"].startswith("sha256:")


def test_outcome_value_is_an_ep_delta_over_the_ibm_tree():
    result = run_outcome_pricing(VALID)
    ov = result["decomposition"]["outcome_value"]
    # V == EP_after - EP_before, and equals the sum of the four IBM driver deltas
    assert ov["value_point"] == pytest.approx(ov["ep_after"] - ov["ep_before"])
    assert ov["value_point"] == pytest.approx(sum(ov["per_driver"].values()))
    assert set(ov["per_driver"]) == {"grow_revenue", "manage_cost", "utilize_capital", "manage_risk"}


def test_economic_capital_is_a_coherent_tail_measure():
    result = run_outcome_pricing(VALID)
    ra = result["decomposition"]["risk_adjust"]
    assert ra["coherent"] is True
    assert ra["economic_capital"] > 0
    # RAV = E[V] - hurdle * EconomicCapital
    assert ra["risk_adjusted_value"] == pytest.approx(
        ra["expected_value"] - ra["hurdle_rate"] * ra["economic_capital"]
    )


def test_discount_uses_fisher_real_separation():
    result = run_outcome_pricing(VALID)
    disc = result["decomposition"]["complexity_time_discount"]
    spec = _valid_spec()["discount"]
    # exact Fisher: (1+nominal)/(1+inflation) - 1
    expected_real = (1 + spec["nominal_rate"]) / (1 + spec["inflation"]) - 1
    assert disc["real_rate"] == pytest.approx(expected_real)
    # the real rate is strictly below the nominal rate (inflation is positive)
    assert disc["real_rate"] < spec["nominal_rate"]
    assert 0 < disc["time_factor"] <= 1
    assert 0 < disc["complexity_factor"] <= 1


def test_mesh_split_conserves_total_price():
    result = run_outcome_pricing(VALID)
    mesh = result["decomposition"]["mesh_split"]
    total = sum(a["allocation"] for a in mesh["allocations"])
    assert total == pytest.approx(result["engagement_price"])
    assert mesh["conservation"]["conserved"] is True
    assert mesh["settlement_receipt"].startswith("sha256:")
    assert mesh["settlement_unit"]["real_asset_backed"] is True


def test_certified_earns_full_voi_speculative_is_discounted():
    # certified -> full raw VoI
    certified = run_outcome_pricing(VALID)["decomposition"]["value_of_information"]
    assert certified["grade"] == "certified"
    assert certified["voi_ceiling"] == pytest.approx(certified["raw_voi"])

    # same knowledge graded speculative with a discount -> strictly less VoI
    spec = _valid_spec()
    spec["knowledge"]["assay_grade"] = "speculative"
    spec["knowledge"]["speculative_discount"] = 0.5
    spec["knowledge"]["priced_voi"] = 10.0  # <= discounted ceiling (20)
    # keep the outcome distribution consistent: E[F] must equal V + priced_voi
    spec["risk"]["outcome_samples"] = _shifted_samples(spec, new_priced_voi=10.0)
    spec_result = price_engagement(spec)
    speculative = spec_result["decomposition"]["value_of_information"]
    assert speculative["voi_ceiling"] < certified["voi_ceiling"]
    assert speculative["voi_ceiling"] == pytest.approx(certified["raw_voi"] * 0.5)


def _shifted_samples(spec, new_priced_voi):
    """Rebuild outcome_samples so E[F] == V + new_priced_voi (value-consistency)."""
    v = price_engagement(_valid_spec())["decomposition"]["outcome_value"]["value_point"]
    target_mean = v + new_priced_voi
    base = json.loads(open(VALID).read())["risk"]["outcome_samples"]
    old_mean = sum(base) / len(base)
    shift = target_mean - old_mean
    return [x + shift for x in base]


# --------------------------------------------------------------------------- #
# REJECTS (teeth)
# --------------------------------------------------------------------------- #
def test_reject_price_not_contingent_on_verified_outcome_receipt():
    with pytest.raises(OutcomePricingError, match="VERIFIED"):
        run_outcome_pricing(NO_RECEIPT)


def test_reject_truth_priced_above_voi_on_uncertified_knowledge():
    with pytest.raises(OutcomePricingError, match="VoI|UNCERTIFIED"):
        run_outcome_pricing(TRUTH_OVER_VOI)


def test_reject_certified_priced_above_raw_voi():
    spec = _valid_spec()
    spec["knowledge"]["priced_voi"] = spec["knowledge"]["decision_value_with"] * 10  # absurdly high
    with pytest.raises(OutcomePricingError, match="above its VoI"):
        price_engagement(spec)


def test_reject_mesh_split_that_does_not_sum_to_price():
    with pytest.raises(OutcomePricingError, match="conservation|Sum"):
        run_outcome_pricing(NONCONSERVING)


def test_reject_price_ignoring_the_outcome_distribution_noncoherent():
    with pytest.raises(OutcomePricingError, match="COHERENT|coherent"):
        run_outcome_pricing(NO_RISK)


def test_reject_price_with_no_outcome_distribution_at_all():
    spec = _valid_spec()
    del spec["risk"]["outcome_samples"]
    with pytest.raises(OutcomePricingError, match="ignores the outcome distribution|no outcome distribution"):
        price_engagement(spec)


def test_reject_false_graded_outcome_not_clawed_back():
    with pytest.raises(OutcomePricingError, match="clawback|FALSE"):
        run_outcome_pricing(FALSE_NOT_CLAWED)


def test_false_graded_with_clawback_is_permitted_but_prices_nonpositive_truth():
    spec = _valid_spec()
    spec["knowledge"]["assay_grade"] = "false"
    spec["knowledge"]["clawback"] = True
    spec["knowledge"]["priced_voi"] = 0.0
    # keep value-consistency: E[F] must equal V + 0
    spec["risk"]["outcome_samples"] = _shifted_samples(spec, new_priced_voi=0.0)
    result = price_engagement(spec)
    voi = result["decomposition"]["value_of_information"]
    assert voi["clawback"] is True
    assert voi["priced_voi"] <= 0.0


# --------------------------------------------------------------------------- #
# equilibrium teeth
# --------------------------------------------------------------------------- #
def test_reject_when_no_positive_surplus_to_split():
    spec = _valid_spec()
    # push the provider cost-floor above any achievable client value-ceiling
    spec["equilibrium"]["provider_cost_floor"] = 10_000.0
    with pytest.raises(OutcomePricingError, match="surplus|POSITIVE"):
        price_engagement(spec)


def test_receipt_is_deterministic():
    r1 = run_outcome_pricing(VALID)
    r2 = run_outcome_pricing(VALID)
    assert r1["receipt_id"] == r2["receipt_id"]
