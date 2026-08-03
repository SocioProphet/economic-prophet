"""RFL-1: R-Cap vs E-Cap regulatory floor. Per-tooth mutation coverage."""
import copy
import json

import pytest

from open_ep_framework.capital_floor import (
    BASEL_CAPITAL_RATIO,
    CapitalFloorError,
    evaluate_contract,
    run_capital_floor,
)
from open_ep_framework.validation import validate_json_file

BOOK = "examples/capital_floor_book.json"
SUBFLOOR = "examples/capital_floor_subfloor.invalid.json"
_SCHEMA = "schemas/capital_floor.schema.json"


def _spec():
    return json.loads(open(BOOK).read())


# --------------------------------------------------------------------------- #
# fixtures validate + evaluate
# --------------------------------------------------------------------------- #
def test_fixtures_validate_against_schema():
    assert validate_json_file(BOOK, _SCHEMA)
    assert validate_json_file(SUBFLOOR, _SCHEMA)


def test_book_verifies_and_floors():
    r = run_capital_floor(BOOK)
    nodes = {n["node_id"]: n for n in r["nodes"]}
    # E-Cap above R-Cap -> economic binds, verified.
    assert nodes["corporate-book"]["binding_constraint"] == "economic"
    assert nodes["corporate-book"]["verdict"] == "verified"
    assert nodes["corporate-book"]["allocated_capital"] == nodes["corporate-book"]["economic_capital"]
    # E-Cap below R-Cap -> regulatory floor binds, flagged, allocated AT the floor.
    retail = nodes["retail-book"]
    assert retail["binding_constraint"] == "regulatory"
    assert retail["verdict"] == "flagged"
    assert retail["allocated_capital"] == pytest.approx(retail["regulatory_capital"])
    assert retail["ecap_rcap_ratio"] < 1.0
    # Standardized RWA path.
    assert nodes["market-desk-standardized"]["regulatory_detail"]["approach"] == "standardized"


def test_ratio_reconciles_to_inputs():
    r = run_capital_floor(BOOK)
    for n in r["nodes"]:
        assert n["ecap_rcap_ratio"] * n["regulatory_capital"] == pytest.approx(n["economic_capital"])
    p = r["portfolio"]
    assert p["ecap_rcap_ratio"] * p["sum_regulatory_capital"] == pytest.approx(p["sum_economic_capital"])


def test_floor_uplift_is_nonnegative_and_conserves():
    r = run_capital_floor(BOOK)
    p = r["portfolio"]
    assert p["sum_allocated_capital"] >= p["sum_economic_capital"]
    assert p["sum_allocated_capital"] >= p["sum_regulatory_capital"]
    assert p["floor_uplift"] == pytest.approx(p["sum_allocated_capital"] - p["sum_economic_capital"])


def test_receipt_is_deterministic_and_records_8pct_assumption():
    r1 = run_capital_floor(BOOK)
    r2 = run_capital_floor(BOOK)
    assert r1["receipt_hash"] == r2["receipt_hash"]
    assert r1["receipt_hash"].startswith("sha256:")
    assert r1["assumptions"]["target_capital_ratio"] == BASEL_CAPITAL_RATIO
    assert r1["assumptions"]["asserted"] is True


# --------------------------------------------------------------------------- #
# TEETH (mutation coverage) — each REJECT reachable from a mutated valid spec
# --------------------------------------------------------------------------- #
def test_tooth_subfloor_declared_allocation_rejected():
    # The canonical invalid fixture: diversified E-Cap allocated below the reg floor.
    with pytest.raises(CapitalFloorError, match="below its regulatory floor"):
        run_capital_floor(SUBFLOOR)


def test_tooth_subfloor_mutation_rejected():
    spec = _spec()
    # retail-book E-Cap (30k) is already below its floor; declare allocation at it.
    spec["nodes"][1]["declared_allocated_capital"] = spec["nodes"][1]["economic_capital_contribution"]
    with pytest.raises(CapitalFloorError, match="diversify under the regulatory minimum"):
        evaluate_contract(spec)


def test_tooth_missing_8pct_assumption_rejected():
    spec = _spec()
    del spec["assumptions"]["target_capital_ratio"]
    with pytest.raises(CapitalFloorError, match="target_capital_ratio is required"):
        evaluate_contract(spec)


def test_tooth_nonpositive_target_ratio_rejected():
    spec = _spec()
    spec["assumptions"]["target_capital_ratio"] = 0.0
    with pytest.raises(CapitalFloorError, match="must be positive"):
        evaluate_contract(spec)


def test_tooth_zero_rwa_floor_rejected():
    spec = _spec()
    spec["nodes"] = [{
        "node_id": "empty-book",
        "economic_capital_contribution": 100.0,
        "regulatory": {"rwa": 0.0},
    }]
    with pytest.raises(CapitalFloorError, match="non-positive regulatory floor"):
        evaluate_contract(spec)


def test_tooth_bad_regulatory_inputs_rejected():
    spec = _spec()
    spec["nodes"] = [{
        "node_id": "no-reg",
        "economic_capital_contribution": 100.0,
        "regulatory": {"lgd": 0.4},  # neither rwa nor pd/lgd/ead
    }]
    with pytest.raises(CapitalFloorError, match="standardized.*or.*IRB|either 'rwa'"):
        evaluate_contract(spec)


def test_declared_allocation_at_floor_is_accepted():
    spec = _spec()
    # Declaring the floored allocation for the flagged node is fine.
    r0 = run_capital_floor(BOOK)
    retail_floor = [n for n in r0["nodes"] if n["node_id"] == "retail-book"][0]["allocated_capital"]
    spec["nodes"][1]["declared_allocated_capital"] = retail_floor
    r = evaluate_contract(spec)
    retail = [n for n in r["nodes"] if n["node_id"] == "retail-book"][0]
    assert retail["verdict"] == "flagged"  # floor still binds, but not rejected
