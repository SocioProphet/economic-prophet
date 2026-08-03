import math

import pytest

from open_ep_framework.market_instruments import (
    MarketInstrumentError,
    VolSurface,
    bs_call,
    bs_put,
    equity_as_call,
    implied_distribution,
    liquidity_premium,
    physical_from_riskneutral,
    pd_from_structural,
)


def _mean(xs):
    return sum(xs) / len(xs)


def _flat_surface(vol=0.20, tenor=1.0):
    return VolSurface.from_nodes([{"tenor": tenor, "strike": k, "vol": vol}
                                  for k in (80, 90, 100, 110, 120)])


def _put_skew_surface(tenor=1.0):
    smile = {80: 0.30, 90: 0.25, 100: 0.20, 110: 0.17, 120: 0.15}
    return VolSurface.from_nodes([{"tenor": tenor, "strike": k, "vol": v}
                                  for k, v in smile.items()])


# --------------------------------------------------------------------------- #
# Black-76 sanity + put-call parity
# --------------------------------------------------------------------------- #
def test_black_put_call_parity():
    c = bs_call(100.0, 100.0, 0.2, 1.0)
    p = bs_put(100.0, 100.0, 0.2, 1.0)
    assert math.isclose(c - p, 100.0 - 100.0, abs_tol=1e-9)


# --------------------------------------------------------------------------- #
# risk-neutral implied distribution: put skew => fatter downside
# --------------------------------------------------------------------------- #
def test_surfaces_validate():
    assert _flat_surface().validate(forward=100.0)
    assert _put_skew_surface().validate(forward=100.0)


def test_put_skew_implies_fatter_downside_than_flat():
    forward = 100.0
    flat = implied_distribution(_flat_surface(), 1.0, forward, n_samples=800)
    skew = implied_distribution(_put_skew_surface(), 1.0, forward, n_samples=800)

    def q05(dist):
        s = sorted(dist.samples)
        return s[int(0.05 * len(s))]

    # The 5th-percentile return under the put-skew surface is more negative.
    assert q05(skew) < q05(flat)


def test_negative_implied_variance_is_rejected():
    bad = VolSurface.from_nodes([{"tenor": 1.0, "strike": 100.0, "vol": -0.1}])
    with pytest.raises(MarketInstrumentError, match="implied variance"):
        bad.validate(forward=100.0)


def test_calendar_arbitrage_is_rejected():
    # Same strike, total variance falls with tenor: w(1) = 0.09, w(2) = 0.02.
    bad = VolSurface.from_nodes([
        {"tenor": 1.0, "strike": 100.0, "vol": 0.30},
        {"tenor": 2.0, "strike": 100.0, "vol": 0.10},
    ])
    with pytest.raises(MarketInstrumentError, match="calendar arbitrage"):
        bad.validate(forward=100.0)


# --------------------------------------------------------------------------- #
# Merton bridge
# --------------------------------------------------------------------------- #
def test_merton_put_call_parity_and_debt_identity():
    m = equity_as_call(asset_value=100.0, debt=80.0, asset_vol=0.25, t=1.0, r=0.03)
    # equity - put == V - D e^{-rT}
    assert math.isclose(m["equity"] - m["put"], 100.0 - m["riskfree_debt"], abs_tol=1e-9)
    # risky debt == riskfree debt - put
    assert math.isclose(m["risky_debt"], m["riskfree_debt"] - m["put"], abs_tol=1e-9)


def test_merton_pd_and_recovery_move_inversely_with_leverage():
    low_lev = equity_as_call(100.0, 80.0, 0.25, 1.0, 0.03)
    high_lev = equity_as_call(100.0, 95.0, 0.25, 1.0, 0.03)
    assert high_lev["pd"] > low_lev["pd"]
    assert high_lev["recovery"] < low_lev["recovery"]
    assert pd_from_structural(100.0, 95.0, 0.25, 1.0, 0.03) == high_lev["pd"]


def test_merton_el_reconciles_to_pd_lgd_ead():
    m = equity_as_call(100.0, 80.0, 0.25, 1.0, 0.03, ead=1_000_000.0)
    assert math.isclose(m["expected_loss"], m["pd"] * m["lgd"] * 1_000_000.0, rel_tol=1e-12)


# --------------------------------------------------------------------------- #
# Ross recovery / Arrow-Debreu seam
# --------------------------------------------------------------------------- #
def test_ross_identity_kernel_returns_f_q_unchanged():
    f_q = implied_distribution(_flat_surface(), 1.0, 100.0, n_samples=400)
    physical = physical_from_riskneutral(f_q, kernel_fn=None)
    assert physical.fingerprint() == f_q.fingerprint()


def test_ross_risk_averse_kernel_lifts_physical_mean():
    f_q = implied_distribution(_put_skew_surface(), 1.0, 100.0, n_samples=800)
    # Risk-averse pricing kernel: larger m in bad (low-return) states.
    physical = physical_from_riskneutral(f_q, kernel_fn=lambda r: math.exp(-3.0 * r))
    assert _mean(physical.samples) > _mean(f_q.samples)


# --------------------------------------------------------------------------- #
# liquidity premium (volume / regime)
# --------------------------------------------------------------------------- #
def test_liquidity_premium_falls_with_volume_rises_with_persistence():
    assert liquidity_premium(volume=100.0) < liquidity_premium(volume=1.0)
    assert liquidity_premium(1.0, regime_hurst=0.8) > liquidity_premium(1.0, regime_hurst=0.5)
