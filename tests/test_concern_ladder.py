"""CLD-1: going/gone-concern ladder == capital waterfall. Per-tooth mutation coverage."""
import copy
import json

import pytest

from open_ep_framework.concern_ladder import (
    ConcernLadderError,
    evaluate_contract,
    run_concern_ladder,
)
from open_ep_framework.validation import validate_json_file

BOOK = "examples/concern_ladder_book.json"
NONMONOTONE = "examples/concern_ladder_nonmonotone.invalid.json"
OUT_OF_ORDER = "examples/concern_ladder_out_of_order.invalid.json"
GONE_TO_SOFT = "examples/concern_ladder_gone_to_soft.invalid.json"
_SCHEMA = "schemas/concern_ladder.schema.json"


def _spec():
    return json.loads(open(BOOK).read())


# --------------------------------------------------------------------------- #
# fixtures validate + evaluate
# --------------------------------------------------------------------------- #
def test_fixtures_validate_against_schema():
    for f in (BOOK, NONMONOTONE, OUT_OF_ORDER, GONE_TO_SOFT):
        assert validate_json_file(f, _SCHEMA)


def test_book_verifies_every_rung():
    r = run_concern_ladder(BOOK)
    assert [s["verdict"] for s in r["scenarios"]] == ["verified"] * 4
    # Alphas strictly increase down the ladder.
    alphas = [s["confidence_alpha"] for s in r["scenarios"]]
    assert alphas == sorted(alphas) and len(set(alphas)) == len(alphas)
    # Each scenario is booked to the marginal layer its loss reaches (subordination order).
    by_name = {s["name"]: s for s in r["scenarios"]}
    assert by_name["early_warning"]["absorbing_capital_layer"] == "hidden_reserves"
    assert by_name["liquidation"]["absorbing_capital_layer"] == "senior_debt"


def test_waterfall_conserves_via_structural_transform():
    r = run_concern_ladder(BOOK)
    w = r["waterfall"]
    assert w["conserved"] is True
    assert w["sum_absorbed"] == pytest.approx(w["capped_expected_loss"], abs=1e-4)
    # The layers are a contiguous partition rising in subordination order.
    attaches = [layer["attach"] for layer in r["capital_stack"]]
    assert attaches == sorted(attaches)


def test_coco_converts_at_boundary_and_receipt_deterministic():
    r1 = run_concern_ladder(BOOK)
    r2 = run_concern_ladder(BOOK)
    assert r1["receipt_hash"] == r2["receipt_hash"]
    assert r1["receipt_hash"].startswith("sha256:")
    assert r1["coco_conversion"]["alpha"] == r1["going_gone_boundary_alpha"]
    assert not r1["warnings"]  # nothing flagged on the clean book


# --------------------------------------------------------------------------- #
# TEETH (mutation coverage)
# --------------------------------------------------------------------------- #
def test_tooth_nonmonotone_alphas_rejected_fixture():
    with pytest.raises(ConcernLadderError, match="not strictly increasing"):
        run_concern_ladder(NONMONOTONE)


def test_tooth_nonmonotone_alphas_rejected_mutation():
    spec = _spec()
    spec["scenarios"][2]["confidence_alpha"] = spec["scenarios"][1]["confidence_alpha"]  # equal, not strict
    with pytest.raises(ConcernLadderError, match="not strictly increasing"):
        evaluate_contract(spec)


def test_tooth_out_of_subordination_order_rejected_fixture():
    with pytest.raises(ConcernLadderError, match="out of subordination order"):
        run_concern_ladder(OUT_OF_ORDER)


def test_tooth_out_of_subordination_order_rejected_mutation():
    spec = _spec()
    # severe_stress loss (180) booked against senior_debt (attach 500) -> loss never reaches it.
    spec["scenarios"][1]["absorbing_capital_layer"] = "senior_debt"
    with pytest.raises(ConcernLadderError, match="out of subordination order"):
        evaluate_contract(spec)


def test_tooth_gone_concern_on_going_soft_layer_rejected_fixture():
    with pytest.raises(ConcernLadderError, match="gone-concern.*going-concern soft layer"):
        run_concern_ladder(GONE_TO_SOFT)


def test_tooth_gone_concern_on_going_soft_layer_rejected_mutation():
    spec = _spec()
    # Make the resolution (gone) scenario land on hidden_reserves (a going-concern soft layer).
    spec["scenarios"][2]["absorbing_capital_layer"] = "hidden_reserves"
    spec["scenarios"][2]["loss_at_alpha"] = 40.0
    with pytest.raises(ConcernLadderError, match="going-concern soft layer"):
        evaluate_contract(spec)


def test_tooth_under_capitalized_scenario_flagged():
    spec = _spec()
    # Liquidation loss punches through the whole stack (total capital = 800).
    spec["scenarios"][3]["loss_at_alpha"] = 950.0
    r = evaluate_contract(spec)
    liq = r["scenarios"][3]
    assert liq["covered"] is False
    assert liq["verdict"] == "flagged"
    assert any("under-capitalized" in w for w in liq["warnings"])


def test_tooth_coco_off_boundary_flagged():
    spec = _spec()
    spec["coco_conversion"]["alpha"] = 0.90  # not at the going->gone boundary
    r = evaluate_contract(spec)
    assert any("boundary" in w for w in r["warnings"])


def test_tooth_concern_label_inconsistent_with_boundary_flagged():
    spec = _spec()
    # Early-warning (alpha 0.80, below boundary) mislabeled gone; still lands on a going
    # layer though -> that would REJECT. Instead relabel severe_stress as gone (alpha 0.95
    # < 0.999 boundary) but keep it on a going layer -> gone-on-going-soft REJECT fires.
    # Use a scenario that stays coverage-correct: flip a gone rung to going.
    spec["scenarios"][2]["concern"] = "going"  # resolution_onset alpha 0.9998 >= boundary
    r = evaluate_contract(spec)
    assert any("inconsistent" in w for s in r["scenarios"] for w in s["warnings"])
