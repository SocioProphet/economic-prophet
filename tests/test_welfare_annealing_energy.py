"""Per-tooth tests for value-energy conservation + the renewable source term (WEA-1)."""
import pytest

from open_ep_framework.welfare_annealing.energy import (
    NON_RENEWABLE, RENEWABLE, Stock, ValueEnergyError, assert_exchange_conserves,
    assert_sustainable, classify_growth, exchange_conserves, production_source,
    sustainable_yield,
)


def _exchange(a_in, b_in, c_out, d_out):
    return {"conserved_quantity": "value_energy", "tolerance": 1e-9,
            "inflows": [{"amount": a_in}, {"amount": b_in}],
            "outflows": [{"amount": c_out}, {"amount": d_out}]}


# --- TOOTH: pure exchange conserves value-energy (reuse of IC-1) ----------- #
def test_balanced_exchange_conserves():
    ledger = assert_exchange_conserves(_exchange(40, 35, 50, 25))
    assert ledger["conserved"] is True
    assert ledger["residual"] == pytest.approx(0.0)


def test_value_created_in_exchange_rejected():
    # sum_in 85 != sum_out 75 -> value created from nothing -> REJECTED
    with pytest.raises(ValueEnergyError):
        assert_exchange_conserves(_exchange(40, 45, 50, 25))
    assert exchange_conserves(_exchange(40, 45, 50, 25))["conserved"] is False


# --- TOOTH: renewability crosswalk consumed from ALC-1 by reference -------- #
def test_stock_process_regime_from_asset_ladder():
    assert Stock(RENEWABLE, 100.0, 5.0).process_regime == "mean_reverting_ou"
    assert Stock(NON_RENEWABLE, 100.0).process_regime == "monotone_absorbing"


def test_unknown_renewability_rejected():
    with pytest.raises(ValueEnergyError):
        Stock("make_believe", 100.0)


def test_sustainable_yield_only_from_renewable():
    assert sustainable_yield(Stock(RENEWABLE, 100.0, 5.0)) == 5.0
    assert sustainable_yield(Stock(NON_RENEWABLE, 100.0, 5.0)) == 0.0  # any draw is drawdown


# --- production source term (Solow / Lockean labor-mixing) ---------------- #
def test_production_source_is_a_source():
    # positive labor mixed with positive materials yields value genesis
    assert production_source(4.0, 9.0, productivity=1.0, labor_share=0.5) == pytest.approx(6.0)
    # no labor or no materials -> no source (Lockean: value needs labor mixed with matter)
    assert production_source(0.0, 9.0) == 0.0
    assert production_source(4.0, 0.0) == 0.0


# --- TOOTH: false growth (non-renewable drawdown) is FLAGGED --------------- #
def test_renewable_only_growth_is_sustainable():
    rep = assert_sustainable({"renewable_delta": 5.0, "nonrenewable_drawdown": 0.0,
                              "claim_sustainable": True})
    assert rep["is_sustainable"] is True
    assert rep["sustainable_growth"] == 5.0


def test_drawdown_claimed_sustainable_rejected():
    with pytest.raises(ValueEnergyError):
        assert_sustainable({"renewable_delta": 2.0, "nonrenewable_drawdown": 4.0,
                            "claim_sustainable": True})


def test_drawdown_not_claimed_sustainable_is_reported_not_raised():
    rep = assert_sustainable({"renewable_delta": 2.0, "nonrenewable_drawdown": 4.0,
                              "claim_sustainable": False})
    assert rep["is_sustainable"] is False
    assert rep["false_growth"] == 4.0
    assert rep["sustainable_growth"] == 2.0


def test_classify_growth_splits_reported_growth():
    rep = classify_growth({"renewable_delta": 3.0, "nonrenewable_drawdown": 2.0})
    assert rep["reported_growth"] == 5.0
    assert rep["sustainable_growth"] == 3.0
    assert rep["false_growth"] == 2.0
