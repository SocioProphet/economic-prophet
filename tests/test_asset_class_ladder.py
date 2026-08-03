"""Teeth for the Jacob's Ladder of Assets contract (ALC-1).

VERIFIES the ladder is total + ordered, every rung carries every axis, and the
canonical classifications hold (farming -> regenerating_flow, mining ->
depleting_stock, digital_service -> non_rival). REJECTS every documented
miscategorization via a dedicated ``.invalid.json`` fixture.
"""
import json

import pytest

from open_ep_framework.asset_ladder.ladder import (
    AssetLadderError,
    LADDER_ORDER,
    RENEWABILITY_REGIME,
    check_ladder,
    classify,
    load_ladder,
    run_check,
)
from open_ep_framework.risk_measures import KNOWN_KERNELS
from open_ep_framework.validation import ValidationError, validate_json_file

SCHEMA = "schemas/asset_class_ladder.schema.json"
LADDER = "examples/asset_class_ladder.json"

REJECT_FIXTURES = [
    "examples/asset_class_ladder_farming_depleting.invalid.json",
    "examples/asset_class_ladder_mining_regenerating.invalid.json",
    "examples/asset_class_ladder_digital_asset_scarcity.invalid.json",
    "examples/asset_class_ladder_nonrenewable_no_hotelling.invalid.json",
    "examples/asset_class_ladder_missing_axis.invalid.json",
    "examples/asset_class_ladder_nonmonotone_order.invalid.json",
]


def _ladder():
    return load_ladder(LADDER)


# --------------------------------------------------------------------------- #
# schema
# --------------------------------------------------------------------------- #
def test_canonical_fixture_validates_against_schema():
    assert validate_json_file(LADDER, SCHEMA)


# --------------------------------------------------------------------------- #
# VERIFIES: total + ordered + every axis
# --------------------------------------------------------------------------- #
def test_ladder_is_total_and_ordered():
    receipt = run_check(LADDER, SCHEMA)
    assert receipt["contract"] == "ALC-1"
    assert receipt["total"] is True
    assert receipt["ordered"] is True
    assert receipt["rung_count"] == len(LADDER_ORDER)
    keys = [r["key"] for r in receipt["rungs"]]
    assert keys == list(LADDER_ORDER)


def test_replaces_thin_asset_class_enum():
    receipt = run_check(LADDER, SCHEMA)
    assert set(receipt["replaces_enum"]) == {"credit", "equity", "market", "crypto"}


def test_every_rung_carries_every_required_axis():
    required = (
        "value_stage",
        "key",
        "label",
        "tangibility",
        "rivalry",
        "renewability",
        "labor_content",
        "process_regime",
        "valuation_model",
        "risk_F_family",
    )
    for rung in _ladder()["rungs"]:
        for axis in required:
            assert rung.get(axis) not in (None, ""), f"{rung.get('key')} missing {axis}"


def test_value_stage_strictly_increases_and_tangibility_never_increases():
    order = {"tangible": 3, "semi_tangible": 2, "intangible": 1}
    rungs = _ladder()["rungs"]
    stages = [r["value_stage"] for r in rungs]
    assert stages == sorted(stages)
    assert len(set(stages)) == len(stages)
    tang = [order[r["tangibility"]] for r in rungs]
    assert tang == sorted(tang, reverse=True)


def test_renewability_regime_crosswalk_holds_on_every_rung():
    for rung in _ladder()["rungs"]:
        assert rung["process_regime"] == RENEWABILITY_REGIME[rung["renewability"]]


def test_every_risk_F_family_is_a_known_rm1_kernel():
    for rung in _ladder()["rungs"]:
        assert rung["risk_F_family"] in KNOWN_KERNELS


# --------------------------------------------------------------------------- #
# VERIFIES: canonical classifications
# --------------------------------------------------------------------------- #
def test_farming_classifies_regenerating_flow():
    rung = classify({"key": "renewable_harvest"}, _ladder())
    assert rung["renewability"] == "regenerating_flow"
    assert rung["process_regime"] == "mean_reverting_ou"
    assert rung["valuation_model"] == "sustainable_yield"


def test_mining_classifies_depleting_stock_with_hotelling():
    rung = classify({"key": "extractive_nonrenewable"}, _ladder())
    assert rung["renewability"] == "depleting_stock"
    assert rung["process_regime"] == "monotone_absorbing"
    assert rung["valuation_model"] == "hotelling_rent"


def test_digital_service_classifies_non_rival():
    rung = classify({"key": "digital_service"}, _ladder())
    assert rung["rivalry"] == "non_rival"
    assert rung["valuation_model"] == "economia_mentium"


def test_digital_asset_is_non_rival_and_network_priced():
    rung = classify({"key": "digital_asset"}, _ladder())
    assert rung["rivalry"] == "non_rival"
    assert rung["valuation_model"] == "network_memetic"


def test_classify_rejects_contradictory_descriptor():
    # farming asserted as a depleting stock contradicts its canonical rung.
    with pytest.raises(AssetLadderError):
        classify({"key": "renewable_harvest", "renewability": "depleting_stock"}, _ladder())


# --------------------------------------------------------------------------- #
# REJECTS: every invalid fixture must be rejected by the checker
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", REJECT_FIXTURES)
def test_invalid_fixture_is_rejected(path):
    ladder = load_ladder(path)
    with pytest.raises(AssetLadderError):
        check_ladder(ladder)


def test_renewable_harvest_tagged_depleting_is_rejected():
    with pytest.raises(AssetLadderError, match="regenerating_flow"):
        check_ladder(load_ladder("examples/asset_class_ladder_farming_depleting.invalid.json"))


def test_mining_tagged_regenerating_is_rejected():
    with pytest.raises(AssetLadderError, match="depleting_stock"):
        check_ladder(load_ladder("examples/asset_class_ladder_mining_regenerating.invalid.json"))


def test_digital_asset_priced_by_scarcity_is_rejected():
    with pytest.raises(AssetLadderError, match="NON-RIVAL|non_rival"):
        check_ladder(load_ladder("examples/asset_class_ladder_digital_asset_scarcity.invalid.json"))


def test_nonrenewable_without_hotelling_is_rejected():
    with pytest.raises(AssetLadderError, match="depletion/Hotelling"):
        check_ladder(load_ladder("examples/asset_class_ladder_nonrenewable_no_hotelling.invalid.json"))


def test_missing_axis_is_rejected_by_schema_and_checker():
    path = "examples/asset_class_ladder_missing_axis.invalid.json"
    with pytest.raises(ValidationError):
        validate_json_file(path, SCHEMA)
    with pytest.raises(AssetLadderError, match="missing required axis"):
        check_ladder(load_ladder(path))


def test_nonmonotone_ordering_is_rejected():
    with pytest.raises(AssetLadderError, match="strictly increasing"):
        check_ladder(load_ladder("examples/asset_class_ladder_nonmonotone_order.invalid.json"))
