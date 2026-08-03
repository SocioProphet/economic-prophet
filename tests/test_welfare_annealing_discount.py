"""Per-tooth tests for discounting: Fisher-real, Fisher-ideal, MV=PQ, social discount rate."""
import math

import pytest

from open_ep_framework.welfare_annealing.discount import (
    DiscountError, DiscountScenario, NORDHAUS, STERN, assert_mv_pq, assert_real_adjusted,
    assert_sensitivity_reconciles, discount_sensitivity, fisher_ideal_index,
    fisher_real_rate, present_value, quantity_theory_residual, ramsey_rate,
)


# --- TOOTH: a growth claim must be Fisher-real-adjusted -------------------- #
def test_fisher_real_rate_matches_inflation_module():
    # consumed from inflation.real_rate: (1+0.05)/(1+0.02)-1
    assert fisher_real_rate(0.05, 0.02) == pytest.approx(1.05 / 1.02 - 1)


def test_real_adjusted_claim_accepted():
    out = assert_real_adjusted({"nominal_growth": 0.05, "inflation": 0.02,
                                "real_growth": 1.05 / 1.02 - 1})
    assert out["fisher_real_adjusted"] is True


def test_nominal_booked_as_real_rejected():
    # reporting the nominal figure as "real" (inflation booked as gain) -> REJECTED
    with pytest.raises(DiscountError):
        assert_real_adjusted({"nominal_growth": 0.05, "inflation": 0.02, "real_growth": 0.05})


def test_missing_real_growth_rejected():
    with pytest.raises(DiscountError):
        assert_real_adjusted({"nominal_growth": 0.05, "inflation": 0.02})


# --- Fisher-ideal index ---------------------------------------------------- #
def test_fisher_ideal_is_geomean_of_laspeyres_paasche():
    p0, q0, p1, q1 = [1.0, 2.0], [10.0, 5.0], [1.1, 2.2], [9.0, 6.0]
    lasp = (1.1 * 10 + 2.2 * 5) / (1.0 * 10 + 2.0 * 5)
    paa = (1.1 * 9 + 2.2 * 6) / (1.0 * 9 + 2.0 * 6)
    assert fisher_ideal_index(p0, q0, p1, q1) == pytest.approx(math.sqrt(lasp * paa))


# --- MV = PQ exchange identity --------------------------------------------- #
def test_mv_pq_identity_holds():
    out = assert_mv_pq(100.0, 6.0, 2.0, 300.0)
    assert out["holds"] is True
    assert quantity_theory_residual(100.0, 6.0, 2.0, 300.0) == pytest.approx(0.0)


def test_mv_pq_broken_rejected():
    with pytest.raises(DiscountError):
        assert_mv_pq(100.0, 6.0, 2.0, 301.0)


# --- TOOTH: social discount rate is the master parameter; sensitivity ------ #
def test_ramsey_rule():
    assert ramsey_rate(0.001, 1.0, 0.02) == pytest.approx(0.021)   # Stern
    assert ramsey_rate(0.015, 1.45, 0.02) == pytest.approx(0.044)  # Nordhaus


def test_low_rate_weights_future_more():
    # Stern (low delta) values a distant QoL gain far more than Nordhaus (high delta)
    stern_r = ramsey_rate(STERN["delta"], STERN["eta"], 0.02)
    nord_r = ramsey_rate(NORDHAUS["delta"], NORDHAUS["eta"], 0.02)
    assert present_value(1000.0, stern_r, 100.0) > present_value(1000.0, nord_r, 100.0)


def test_sensitivity_sweep_reconciles():
    scen = discount_sensitivity(1000.0, 100.0, 0.02, [
        dict(name="stern", **{k: STERN[k] for k in ("delta", "eta")}),
        {"name": "mid", "delta": 0.008, "eta": 1.2},
        dict(name="nordhaus", **{k: NORDHAUS[k] for k in ("delta", "eta")}),
    ])
    recon = assert_sensitivity_reconciles(scen)
    assert recon["monotone_decreasing_in_rate"] is True
    assert recon["future_weighted_more_by_low_rate"] is True
    assert recon["lowest_rate"]["name"] == "stern"
    assert recon["highest_rate"]["name"] == "nordhaus"


def test_non_monotone_sensitivity_rejected():
    # a hand-built sweep where a higher rate has a HIGHER present value is inconsistent
    bad = [
        DiscountScenario("lo", 0.001, 1.0, 0.02, 100.0),
        DiscountScenario("hi", 0.02, 1.0, 0.05, 500.0),  # higher rate, higher PV -> impossible
    ]
    with pytest.raises(DiscountError):
        assert_sensitivity_reconciles(bad)
