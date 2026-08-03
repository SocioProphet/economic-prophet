"""AGG-1: aggregation-methodology taxonomy + tail-dependence guard. Per-tooth coverage."""
import json

import pytest

from open_ep_framework.aggregation_method import (
    AggregationMethodError,
    evaluate_contract,
    run_aggregation_method,
)
from open_ep_framework.validation import validate_json_file

COPULA = "examples/aggregation_method_copula.json"
TAILBLIND = "examples/aggregation_method_varcovar_tailblind.json"
SUPERADD = "examples/aggregation_method_superadditive.invalid.json"
NOASSUMP = "examples/aggregation_method_no_assumption.invalid.json"
_SCHEMA = "schemas/aggregation_method.schema.json"


def _spec(path=COPULA):
    return json.loads(open(path).read())


# --------------------------------------------------------------------------- #
# fixtures validate + evaluate
# --------------------------------------------------------------------------- #
def test_fixtures_validate_against_schema():
    for f in (COPULA, TAILBLIND, SUPERADD, NOASSUMP):
        assert validate_json_file(f, _SCHEMA)


def test_summation_is_the_upper_bound_over_all_methods():
    r = run_aggregation_method(COPULA)
    s = r["method_comparison"]["summation"]
    assert s == pytest.approx(2000.0)
    for name, value in r["method_comparison"].items():
        assert value <= s + 1e-6, name


def test_copula_choice_verifies_and_records_tradeoff():
    r = run_aggregation_method(COPULA)
    assert r["verdict"] == "verified"
    assert r["chosen_method"] == "copula"
    assert r["chosen_aggregate"] <= r["summation_upper_bound"]
    assert r["trade_off"] == "captures tail dependence"
    assert "hard to validate" in r["stated_limitation"]
    # Tail dependence lifts the copula above the linear var-covar number.
    assert r["method_comparison"]["copula"] > r["method_comparison"]["variance_covariance"]


def test_receipt_deterministic_and_carries_choice_and_assumption():
    r1 = run_aggregation_method(COPULA)
    r2 = run_aggregation_method(COPULA)
    assert r1["receipt_hash"] == r2["receipt_hash"]
    assert r1["receipt_hash"].startswith("sha256:")
    assert r1["assumption"]["copula_family"] == "student_t"
    assert r1["assumption"]["tail_dependence"] == 0.4


# --------------------------------------------------------------------------- #
# TEETH (mutation coverage)
# --------------------------------------------------------------------------- #
def test_tooth_variance_covariance_tail_blind_flagged_fixture():
    r = run_aggregation_method(TAILBLIND)
    assert r["verdict"] == "flagged"
    assert any("tail-dependence-blind" in w for w in r["warnings"])
    assert r["chosen_aggregate"] < r["method_comparison"]["copula"]


def test_tooth_super_additive_method_rejected_fixture():
    with pytest.raises(AggregationMethodError, match="exceeds the summation upper bound"):
        run_aggregation_method(SUPERADD)


def test_tooth_super_additive_method_rejected_mutation():
    spec = _spec()
    spec["chosen_method"] = "constant_diversification"
    spec["assumption"]["diversification_factor"] = -0.5  # aggregate = 1.5 x sum
    with pytest.raises(AggregationMethodError, match="exceeds the summation"):
        evaluate_contract(spec)


def test_tooth_missing_assumption_rejected_fixture():
    with pytest.raises(AggregationMethodError, match="no.*correlation.*copula.*diversification|no silent diversification"):
        run_aggregation_method(NOASSUMP)


def test_tooth_missing_correlation_rejected_mutation():
    spec = _spec()
    spec["chosen_method"] = "variance_covariance"
    spec["assumption"] = {}  # strip the declared correlation
    with pytest.raises(AggregationMethodError, match="no silent diversification"):
        evaluate_contract(spec)


def test_tooth_copula_without_tail_params_rejected():
    spec = _spec()
    # Keep correlation but strip the copula/tail declaration -> copula not computable.
    spec["assumption"].pop("copula_family", None)
    spec["assumption"].pop("tail_dependence", None)
    with pytest.raises(AggregationMethodError, match="no silent diversification|could not be computed"):
        evaluate_contract(spec)


def test_summation_method_needs_no_assumption():
    spec = _spec()
    spec["chosen_method"] = "summation"
    spec["assumption"] = {}
    r = evaluate_contract(spec)
    assert r["verdict"] == "verified"
    assert r["chosen_aggregate"] == pytest.approx(2000.0)
    assert r["diversification_benefit"] == pytest.approx(0.0)


def test_constant_diversification_is_below_summation():
    spec = _spec()
    spec["chosen_method"] = "constant_diversification"
    spec["assumption"]["diversification_factor"] = 0.2
    r = evaluate_contract(spec)
    assert r["verdict"] == "verified"
    assert r["chosen_aggregate"] == pytest.approx(1600.0)
