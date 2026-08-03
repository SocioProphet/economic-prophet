import math

import pytest

from open_ep_framework.risk_measures import (
    LossDistribution,
    RiskMeasureError,
    euler_allocation,
    expected_loss,
    largest_cumulative_gap,
    max_drawdown,
    risk,
    risk_term_structure,
    structural_transform,
)


def _skewed():
    # Negatively skewed returns: a few sharp losses, many small gains.
    return LossDistribution.from_samples(
        [0.02, 0.03, 0.01, 0.02, 0.04, -0.20, 0.03, 0.02, -0.15, 0.05,
         0.01, 0.02, 0.03, -0.10, 0.04, 0.02, 0.03, 0.01, 0.02, 0.06,
         0.03, 0.02, 0.01, -0.08, 0.05, 0.02, 0.03, 0.04, 0.02, 0.03,
         0.01, 0.02, 0.03, 0.04, -0.05, 0.02, 0.03, 0.01, 0.02, 0.03]
    )


def test_es_dominates_var_at_same_alpha():
    F = _skewed()
    es = risk(F, "expected_shortfall", alpha=0.95)
    var = risk(F, "var", alpha=0.95)
    # Tail average must dominate the tail quantile.
    assert es.value >= var.value
    assert es.value > var.value  # strict for a distribution with distinct tail losses


def test_var_and_sharpe_are_flagged_noncoherent_es_coherent():
    F = _skewed()
    assert risk(F, "var", alpha=0.95).coherent is False
    assert risk(F, "sharpe").coherent is False
    assert risk(F, "expected_shortfall", alpha=0.95).coherent is True
    assert risk(F, "spectral", alpha=0.95).coherent is True  # flat-tail spectrum


def test_sortino_ignores_upside_where_sharpe_penalizes_it():
    # Same downside, extra upside dispersion in d2.
    d1 = LossDistribution.from_samples([-0.02, -0.01, 0.01, 0.02, 0.03])
    d2 = LossDistribution.from_samples([-0.02, -0.01, 0.01, 0.02, 0.20])
    # Sharpe denominator (two-sided sigma) rises when upside spread rises.
    assert risk(d2, "sharpe").risk_functional > risk(d1, "sharpe").risk_functional
    # Sortino denominator (downside deviation about MAR=0) is unchanged.
    assert math.isclose(
        risk(d2, "sortino", reference=0.0).risk_functional,
        risk(d1, "sortino", reference=0.0).risk_functional,
        rel_tol=1e-12,
    )


def test_kappa_order_two_equals_sortino():
    F = _skewed()
    kappa2 = risk(F, "kappa", order=2, reference=0.0)
    sortino = risk(F, "sortino", reference=0.0)
    assert math.isclose(kappa2.value, sortino.value, rel_tol=1e-12)


def test_kappa_order_generalizes_family():
    F = _skewed()
    # order 0 is a shortfall-probability denominator; different from n=2.
    k0 = risk(F, "kappa", order=0, reference=0.0)
    k2 = risk(F, "kappa", order=2, reference=0.0)
    assert k0.value != k2.value
    assert 0.0 < k0.risk_functional <= 1.0  # a probability


def test_min_n_flags_provisional():
    small = LossDistribution.from_samples([0.01, -0.02, 0.03])
    assert small.provisional is True
    assert risk(small, "expected_shortfall", alpha=0.95).provisional is True
    big = _skewed()
    assert big.provisional is False
    assert risk(big, "expected_shortfall", alpha=0.95).provisional is False


def test_horizon_term_structure_is_increasing():
    F = _skewed()
    ts = risk_term_structure(F, "expected_shortfall", [1.0, 5.0, 10.0], alpha=0.95)
    assert ts[10.0] > ts[5.0] > ts[1.0]  # sqrt-time growth


def test_largest_cumulative_gap_lcr():
    # cumulative: 10, -20, -15, -35, 5 -> deepest gap 35
    assert largest_cumulative_gap([10, -30, 5, -20, 40]) == 35.0
    assert largest_cumulative_gap([5, 5, 5]) == 0.0  # never negative cumulative


def test_credit_simulation_is_deterministic_and_reproducible():
    a = LossDistribution.simulate_credit(0.02, 0.45, 1_000_000, 0.7, 0.3, n_scenarios=500, seed=7)
    b = LossDistribution.simulate_credit(0.02, 0.45, 1_000_000, 0.7, 0.3, n_scenarios=500, seed=7)
    assert a.samples == b.samples
    assert a.fingerprint() == b.fingerprint()
    assert a.n == 500 and a.provisional is False


def test_spectral_non_increasing_is_coherent_increasing_is_not():
    F = _skewed()
    # tail size k = ceil((1-0.9)*40) = 4
    coherent = risk(F, "spectral", alpha=0.9, phi=[0.4, 0.3, 0.2, 0.1])
    noncoherent = risk(F, "spectral", alpha=0.9, phi=[0.1, 0.2, 0.3, 0.4])
    assert coherent.coherent is True
    assert noncoherent.coherent is False


# --------------------------------------------------------------------------- #
# omnirisk kernel: equity F, structure/issuance, coherent allocation
# --------------------------------------------------------------------------- #
def test_equity_return_distribution_reads_same_interface():
    F = LossDistribution.simulate_equity(mu=0.0004, sigma=0.012, df=4.0, beta=1.1,
                                         n_scenarios=500, seed=3)
    assert F.beta == 1.1
    assert not F.provisional
    # The same risk() interface serves equity: reward-to-risk AND tail lenses.
    assert risk(F, "sharpe").family == "reward_to_risk"
    assert risk(F, "expected_shortfall", alpha=0.95).coherent is True
    # Drawdown is path-dependent equity/market risk.
    assert 0.0 <= max_drawdown(F.samples) <= 1.0


def test_structural_transform_reconciles_tranche_el_to_pool_el():
    pool = LossDistribution.simulate_credit(0.05, 0.5, 1_000_000, 0.7, 0.3,
                                            n_scenarios=400, seed=5)
    cap = max(pool.losses) + 1.0  # a top detach that covers all pool loss
    equity = structural_transform(pool, 0.0, 5000.0)      # first-loss / residual claim
    mezz = structural_transform(pool, 5000.0, 25000.0)
    senior = structural_transform(pool, 25000.0, cap)
    total_tranche_el = expected_loss(equity) + expected_loss(mezz) + expected_loss(senior)
    # Conservation: contiguous tranche ELs sum back to the pool EL.
    assert math.isclose(total_tranche_el, expected_loss(pool), rel_tol=1e-9, abs_tol=1e-6)


def test_structural_transform_rejects_bad_tranche():
    pool = LossDistribution.simulate_credit(0.05, 0.5, 1_000_000, 0.7, 0.3,
                                            n_scenarios=100, seed=5)
    with pytest.raises(RiskMeasureError, match="detach"):
        structural_transform(pool, 5000.0, 5000.0)


def test_euler_allocation_sums_to_total_for_coherent_measure():
    a = LossDistribution.simulate_credit(0.03, 0.45, 500_000, 0.7, 0.3, n_scenarios=400, seed=1)
    b = LossDistribution.simulate_credit(0.02, 0.55, 800_000, 0.6, 0.4, n_scenarios=400, seed=1)
    alloc = euler_allocation({"bu_a": a, "bu_b": b}, "expected_shortfall", alpha=0.95)
    assert alloc["coherent"] is True
    # Sum-to-total == the IC-1 conservation of allocated capital.
    assert alloc["sum_to_total"] is True
    assert math.isclose(alloc["sum_of_contributions"], alloc["total"], rel_tol=1e-9)


def test_euler_allocation_rejects_noncoherent_without_override():
    a = LossDistribution.simulate_credit(0.03, 0.45, 500_000, 0.7, 0.3, n_scenarios=200, seed=1)
    b = LossDistribution.simulate_credit(0.02, 0.55, 800_000, 0.6, 0.4, n_scenarios=200, seed=1)
    with pytest.raises(RiskMeasureError, match="non-coherent"):
        euler_allocation({"a": a, "b": b}, "var", alpha=0.95)
    warned = euler_allocation({"a": a, "b": b}, "var", alpha=0.95, allow_noncoherent=True)
    assert warned["coherent"] is False
    assert any("incoherence warning" in w for w in warned["warnings"])
