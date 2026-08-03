import math

import pytest

from open_ep_framework.ftp_curve import (
    FTPCurve,
    FTPError,
    assign_ftp,
    curve_rate,
    funding_cost,
    run_ftp_separation,
    separation_decomposition,
)
from open_ep_framework.term_calculus import Cashflow
from open_ep_framework.validation import validate_json_file

BOOK = "examples/ftp_separation_book.json"
CROSS_SUBSIDY = "examples/ftp_separation_cross_subsidy.invalid.json"


def _curve():
    return FTPCurve.from_points([
        {"tenor": 0.25, "rate": 0.03},
        {"tenor": 1.0, "rate": 0.035},
        {"tenor": 5.0, "rate": 0.04},
        {"tenor": 10.0, "rate": 0.045},
    ])


# --------------------------------------------------------------------------- #
# matched-maturity: a 5y flow prices at the 5y point, not overnight
# --------------------------------------------------------------------------- #
def test_matched_maturity_bullet_prices_at_its_tenor():
    curve = _curve()
    five_year = assign_ftp([Cashflow(5.0, 100.0)], curve)
    assert math.isclose(five_year["transfer_rate"], 0.04, rel_tol=1e-12)
    # NOT the overnight/3m point
    assert not math.isclose(five_year["transfer_rate"], curve_rate(curve, 0.25))


def test_curve_interpolates_between_points():
    curve = _curve()
    # halfway (in tenor) between 1y (0.035) and 5y (0.04): tenor 3 -> 0.0375
    assert math.isclose(curve_rate(curve, 3.0), 0.0375, rel_tol=1e-9)


def test_funding_cost_feeds_ep_identity():
    assert funding_cost(1000.0, 0.04) == 40.0


def test_curve_rejects_unsorted_tenors():
    with pytest.raises(FTPError, match="sorted"):
        FTPCurve.from_points([{"tenor": 5.0, "rate": 0.04}, {"tenor": 1.0, "rate": 0.035}])


# --------------------------------------------------------------------------- #
# separation theorem: reconciles to NIM under IC-1
# --------------------------------------------------------------------------- #
def test_fixtures_validate_against_schema():
    assert validate_json_file(BOOK, "schemas/ftp_separation.schema.json")
    assert validate_json_file(CROSS_SUBSIDY, "schemas/ftp_separation.schema.json")


def test_separation_reconciles_to_nim():
    receipt = run_ftp_separation(BOOK)
    assert math.isclose(receipt["net_interest_margin"], 50.0, abs_tol=1e-9)
    assert math.isclose(receipt["total_unit_spreads"], 40.0, abs_tol=1e-9)
    assert math.isclose(receipt["treasury_residual"]["computed"], 10.0, abs_tol=1e-9)
    assert receipt["conservation"]["conserved"] is True
    assert math.isclose(receipt["conservation"]["residual"], 0.0, abs_tol=1e-9)
    # unit spreads: lending 20, deposit 20
    spreads = {u["unit"]: u["spread"] for u in receipt["unit_spreads"]}
    assert math.isclose(spreads["commercial_loans"], 20.0, abs_tol=1e-9)
    assert math.isclose(spreads["retail_deposits"], 20.0, abs_tol=1e-9)
    assert receipt["receipt_hash"].startswith("sha256:")


def test_cross_subsidy_is_rejected():
    # 5y asset transfer-priced at the 3m point without booking the gap to Treasury.
    with pytest.raises(FTPError, match="cross-subsidy"):
        run_ftp_separation(CROSS_SUBSIDY)


def test_cross_subsidy_allowed_when_booked_to_treasury():
    book = {
        "book_id": "b", "as_of": "d", "tolerance": 1e-6,
        "curve": {"points": [{"tenor": 0.25, "rate": 0.03}, {"tenor": 5.0, "rate": 0.04}]},
        "assets": [{"unit": "loans", "balance": 1000.0, "tenor": 5.0, "customer_rate": 0.06,
                    "booked_ftp_rate": 0.03, "treasury_absorbs_cross_subsidy": True}],
        "liabilities": [],
        # treasury_ftp = booked_a * bal = 0.03 * 1000 = 30
        "treasury": {"structural": 20.0, "liquidity": 7.0, "basis": 3.0},
    }
    receipt = separation_decomposition(book)
    assert receipt["conservation"]["conserved"] is True
    assert math.isclose(receipt["treasury_residual"]["computed"], 30.0, abs_tol=1e-9)


def test_treasury_residual_components_must_reconcile():
    book = {
        "book_id": "b", "as_of": "d", "tolerance": 1e-6,
        "curve": {"points": [{"tenor": 0.25, "rate": 0.03}, {"tenor": 5.0, "rate": 0.04}]},
        "assets": [{"unit": "loans", "balance": 1000.0, "tenor": 5.0, "customer_rate": 0.06}],
        "liabilities": [{"unit": "dep", "balance": 1000.0, "tenor": 0.25, "customer_rate": 0.01}],
        "treasury": {"structural": 1.0, "liquidity": 1.0, "basis": 1.0},  # sum 3 != 10
    }
    with pytest.raises(FTPError, match="do not reconcile"):
        separation_decomposition(book)
