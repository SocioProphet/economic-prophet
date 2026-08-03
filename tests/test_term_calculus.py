import math

import pytest

from open_ep_framework.risk_measures import (
    LossDistribution,
    euler_allocation,
    excess_kurtosis,
    risk,
    skewness,
)
from open_ep_framework.term_calculus import (
    Cashflow,
    analytic_convexity,
    average_life,
    effective_convexity,
    effective_duration,
    finite_difference,
    macaulay_duration,
    modified_duration,
    price,
    taylor_reprice,
    term_regime,
)


def _coupon_bond():
    # 5y annual 5% coupon bond, face 100.
    flows = [Cashflow(t, 5.0) for t in range(1, 5)]
    flows.append(Cashflow(5.0, 105.0))
    return flows


# --------------------------------------------------------------------------- #
# time-axis integrals: WAL + duration reconcile to the schedule
# --------------------------------------------------------------------------- #
def test_bullet_wal_equals_maturity():
    assert average_life([Cashflow(5.0, 100.0)]) == 5.0


def test_wal_reconciles_to_schedule():
    flows = [Cashflow(1.0, 50.0), Cashflow(3.0, 50.0)]
    # (1*50 + 3*50) / 100 = 2.0
    assert average_life(flows) == 2.0


def test_analytic_and_numerical_duration_reconcile():
    bond = _coupon_bond()
    y = 0.04
    reprice = lambda yy: price(bond, yy)
    assert math.isclose(modified_duration(bond, y), effective_duration(reprice, y),
                        rel_tol=1e-4)
    assert math.isclose(analytic_convexity(bond, y), effective_convexity(reprice, y),
                        rel_tol=1e-3)


def test_second_order_taylor_reprices_within_tolerance():
    bond = _coupon_bond()
    y = 0.04
    dy = 0.01
    p0 = price(bond, y)
    approx = taylor_reprice(p0, modified_duration(bond, y), analytic_convexity(bond, y), dy)
    assert math.isclose(price(bond, y + dy), approx, rel_tol=1e-3)


# --------------------------------------------------------------------------- #
# value-axis integrals: moments + higher-moment warning
# --------------------------------------------------------------------------- #
def test_gaussian_has_near_zero_skew_and_excess_kurtosis():
    gauss = LossDistribution.simulate_equity(mu=0.0, sigma=0.01, df=60.0, n_scenarios=2000, seed=9)
    assert abs(skewness(gauss.samples)) < 0.3
    assert abs(excess_kurtosis(gauss.samples)) < 0.6


def test_fat_tailed_has_positive_excess_kurtosis():
    fat = LossDistribution.simulate_equity(mu=0.0, sigma=0.01, df=3.0, n_scenarios=2000, seed=9)
    gauss = LossDistribution.simulate_equity(mu=0.0, sigma=0.01, df=60.0, n_scenarios=2000, seed=9)
    assert excess_kurtosis(fat.samples) > excess_kurtosis(gauss.samples)
    assert excess_kurtosis(fat.samples) > 1.0


def test_sharpe_on_skewed_f_warns_higher_moment_symmetric_does_not():
    skewed = LossDistribution.from_samples(
        [0.01] * 30 + [-0.30, -0.25, -0.20, -0.18, -0.15]
    )
    warned = " ".join(risk(skewed, "sharpe").warnings)
    assert "higher-moment risk unpriced" in warned

    near_gaussian = LossDistribution.simulate_equity(mu=0.0, sigma=0.01, df=100.0,
                                                     n_scenarios=1000, seed=5)
    clean = " ".join(risk(near_gaussian, "sharpe").warnings)
    assert "higher-moment risk unpriced" not in clean


# --------------------------------------------------------------------------- #
# integration: ES is the tail integral consistent with the VaR quantile
# --------------------------------------------------------------------------- #
def test_es_is_tail_integral_consistent_with_var():
    F = LossDistribution.simulate_credit(0.05, 0.5, 1_000_000, 0.7, 0.3, n_scenarios=400, seed=2)
    alpha = 0.95
    var = risk(F, "var", alpha=alpha).value
    es = risk(F, "expected_shortfall", alpha=alpha).value
    tail = [x for x in F.losses if x >= var]
    assert math.isclose(es, sum(tail) / len(tail), rel_tol=1e-9)
    assert es >= var


# --------------------------------------------------------------------------- #
# differentiation: marginal capital == finite-difference sensitivity
# --------------------------------------------------------------------------- #
def test_marginal_capital_matches_finite_difference():
    a = LossDistribution.simulate_credit(0.03, 0.45, 500_000, 0.7, 0.3, n_scenarios=600, seed=1)
    b = LossDistribution.simulate_credit(0.02, 0.55, 800_000, 0.6, 0.4, n_scenarios=600, seed=1)
    a_loss = list(a.losses)
    b_loss = list(b.losses)
    alpha = 0.95

    def portfolio_es(scale_a: float) -> float:
        combined = [-(scale_a * a_loss[s] + b_loss[s]) for s in range(len(a_loss))]
        return risk(LossDistribution.from_samples(combined), "expected_shortfall", alpha=alpha).value

    # Euler contribution of A == marginal ES w.r.t. scaling A's exposure.
    contrib_a = euler_allocation({"a": a, "b": b}, "expected_shortfall", alpha=alpha)["contributions"]["a"]
    marginal = finite_difference(portfolio_es, 1.0, h=1e-3)
    assert math.isclose(contrib_a, marginal, rel_tol=1e-6, abs_tol=1e-3)


# --------------------------------------------------------------------------- #
# term regime: shape + persistence via injectable Hurst
# --------------------------------------------------------------------------- #
def test_term_regime_shapes():
    upward = term_regime([(1, 0.02), (2, 0.025), (5, 0.03), (10, 0.035)])
    assert upward["shape"] == "upward"
    inverted = term_regime([(1, 0.05), (2, 0.045), (5, 0.03), (10, 0.02)])
    assert inverted["shape"] == "inverted"
    flat = term_regime([(1, 0.03), (10, 0.03)])
    assert flat["shape"] == "flat"


def test_term_regime_accepts_injected_hurst_characterizer():
    calls = {}

    def fake_characterizer(values):
        calls["values"] = list(values)
        return 0.8  # persistent

    out = term_regime([(1, 0.02), (2, 0.025), (5, 0.03), (10, 0.035)], hurst_fn=fake_characterizer)
    assert out["persistence"] == "persistent"
    assert out["hurst_source"] == "injected"
    assert calls["values"]  # the estate characterizer was actually consumed
