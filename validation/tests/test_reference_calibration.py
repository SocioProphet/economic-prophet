"""Tooth #2 -- reference-data calibration (external validity).

The merged kernels are matched against independent closed forms:

  * Merton PD: distance-to-default and PD = N(-d2) for a worked structural example,
    matched to an independent analytic computation AND pinned to the reference
    figure (mismatch REJECTED).
  * Expected Shortfall of a Normal: the kernel's numeric ES matched to the closed
    form ES_alpha = mu + sigma * phi(Phi^{-1}(alpha)) / (1 - alpha).
  * Sharpe and downside deviation matched to their analytic identities.
"""
import math

import pytest

from open_ep_framework.market_instruments import equity_as_call, pd_from_structural
from open_ep_framework.risk_measures import LossDistribution, downside_deviation, risk
from validation.regime_f import (
    analytic_es_normal,
    gaussian_returns,
    inv_norm_cdf,
    norm_cdf,
)


# --------------------------------------------------------------------------- #
# Merton PD -- worked structural-credit example
# --------------------------------------------------------------------------- #
# Standard Merton (1974) worked example: a firm with asset value V, face debt D,
# asset volatility sigma, risk-free r, horizon T=1y.
#   d2 = (ln(V/D) + (r - 0.5 sigma^2) T) / (sigma sqrt(T))   (distance-to-default)
#   PD = N(-d2)
# Independently computed reference for (V=100, D=80, sigma=0.20, r=0.05, T=1):
#   d2 = 1.2657189...   DD = d2 = 1.2657   PD = N(-d2) = 0.1028074...
MERTON = dict(V=100.0, D=80.0, sigma=0.20, r=0.05, T=1.0)
MERTON_DD_REF = 1.265717756571  # distance-to-default (= d2)
MERTON_PD_REF = 0.102807074403  # N(-d2)


def _analytic_merton_d2(V, D, sigma, r, T):
    return (math.log(V / D) + (r - 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))


def test_merton_distance_to_default_matches_reference():
    d2 = _analytic_merton_d2(MERTON["V"], MERTON["D"], MERTON["sigma"], MERTON["r"], MERTON["T"])
    # kernel's d2 must equal the analytic distance-to-default.
    kd2 = equity_as_call(MERTON["V"], MERTON["D"], MERTON["sigma"], MERTON["T"], MERTON["r"])["d2"]
    assert math.isclose(kd2, d2, rel_tol=0, abs_tol=1e-9)
    # and both must match the pinned reference figure (external validity).
    assert math.isclose(kd2, MERTON_DD_REF, rel_tol=0, abs_tol=1e-6)


def test_merton_pd_matches_textbook_reference_within_tolerance():
    pd_kernel = pd_from_structural(MERTON["V"], MERTON["D"], MERTON["sigma"], MERTON["T"], MERTON["r"])
    # independent closed form N(-d2)
    d2 = _analytic_merton_d2(MERTON["V"], MERTON["D"], MERTON["sigma"], MERTON["r"], MERTON["T"])
    pd_analytic = norm_cdf(-d2)
    assert math.isclose(pd_kernel, pd_analytic, rel_tol=0, abs_tol=1e-9)
    # pinned reference: mismatch is REJECTED.
    assert math.isclose(pd_kernel, MERTON_PD_REF, rel_tol=0, abs_tol=1e-6), pd_kernel


def test_merton_pd_and_recovery_move_inversely_with_leverage():
    # External-validity sanity: more leverage (higher D) -> higher PD, lower recovery.
    low = equity_as_call(100.0, 70.0, 0.20, 1.0, 0.05)
    high = equity_as_call(100.0, 95.0, 0.20, 1.0, 0.05)
    assert high["pd"] > low["pd"]
    assert high["recovery"] < low["recovery"]


# --------------------------------------------------------------------------- #
# Expected Shortfall of a Normal -- numeric kernel vs closed form
# --------------------------------------------------------------------------- #
def test_kernel_ES_matches_closed_form_normal():
    n = 40000
    F = LossDistribution.from_samples(gaussian_returns(n, mu=0.0, sigma=1.0))
    for alpha in (0.95, 0.975, 0.99):
        es_num = risk(F, "expected_shortfall", alpha=alpha).value
        es_ana = analytic_es_normal(0.0, 1.0, alpha)
        assert math.isclose(es_num, es_ana, rel_tol=0, abs_tol=5e-3), (alpha, es_num, es_ana)


def test_kernel_ES_matches_closed_form_normal_scaled_and_shifted():
    # A non-standard Normal loss: mu != 0, sigma != 1. ES scales/shifts analytically.
    n = 40000
    mu, sigma, alpha = 0.01, 0.15, 0.975
    # loss L = -R; build returns with mean -mu, std sigma so the LOSS has mean mu.
    F = LossDistribution.from_samples(gaussian_returns(n, mu=-mu, sigma=sigma))
    es_num = risk(F, "expected_shortfall", alpha=alpha).value
    es_ana = analytic_es_normal(mu, sigma, alpha)
    assert math.isclose(es_num, es_ana, rel_tol=0, abs_tol=5e-3), (es_num, es_ana)


def test_ES_analytic_constants_are_the_known_values():
    # Guard the closed-form implementation itself against drift.
    assert math.isclose(analytic_es_normal(0.0, 1.0, 0.975), 2.337803, abs_tol=1e-5)
    assert math.isclose(analytic_es_normal(0.0, 1.0, 0.99), 2.665214, abs_tol=1e-5)


# --------------------------------------------------------------------------- #
# Sharpe / downside deviation -- analytic identities
# --------------------------------------------------------------------------- #
def test_sharpe_matches_analytic_identity():
    n, mu, sigma, rf = 40000, 0.08, 0.15, 0.02
    F = LossDistribution.from_samples(gaussian_returns(n, mu=mu, sigma=sigma))
    sharpe = risk(F, "sharpe", reference=rf).value
    assert math.isclose(sharpe, (mu - rf) / sigma, rel_tol=0, abs_tol=1e-3), sharpe


def test_downside_deviation_symmetric_identity():
    # For a symmetric F, downside deviation about the mean == sigma / sqrt(2)
    # (half the variance is below the mean). This is the Sortino denominator.
    n, mu, sigma = 40000, 0.08, 0.15
    xs = gaussian_returns(n, mu=mu, sigma=sigma)
    m = sum(xs) / len(xs)
    dd = downside_deviation(xs, m)
    assert math.isclose(dd, sigma / math.sqrt(2.0), rel_tol=0, abs_tol=1e-3), dd


def test_inv_norm_cdf_round_trips():
    for p in (0.01, 0.1, 0.5, 0.9, 0.975, 0.99):
        assert math.isclose(norm_cdf(inv_norm_cdf(p)), p, rel_tol=0, abs_tol=1e-10)
