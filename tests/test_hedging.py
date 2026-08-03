import math

from open_ep_framework.hedging import (
    dv01,
    futures_variation_margin,
    hedge_notional,
    hedged_pnl,
    net_first_derivative,
    net_second_derivative,
)
from open_ep_framework.term_calculus import Cashflow


def _long_bond():
    # 10y 4% annual bond.
    flows = [Cashflow(float(t), 4.0) for t in range(1, 10)]
    flows.append(Cashflow(10.0, 104.0))
    return flows


def _short_swap_leg():
    # A short-duration hedging instrument (2y bullet) -- deliberately different convexity.
    return [Cashflow(2.0, 100.0)]


def test_dv01_neutral_hedge_zeros_first_derivative():
    book = _long_bond()
    inst = _short_swap_leg()
    y = 0.04
    h = hedge_notional(book, y, inst, y)
    net_dpdy = net_first_derivative(book, inst, h["notional"], y)
    unhedged_dpdy = net_first_derivative(book, inst, 0.0, y)
    # First derivative of the hedged portfolio is driven to ~0 (many orders of
    # magnitude below the unhedged book; residual is finite-difference truncation).
    assert abs(net_dpdy) < 1e-3
    assert abs(net_dpdy) < abs(unhedged_dpdy) * 1e-3
    # Unhedged book has a materially non-zero first derivative / DV01.
    assert abs(h["dv01_book"]) > 1e-3


def test_convexity_mismatch_leaves_second_order_pnl():
    book = _long_bond()
    inst = _short_swap_leg()
    y = 0.04
    h = hedge_notional(book, y, inst, y)
    # Different convexity -> residual 2nd derivative is non-zero.
    assert abs(net_second_derivative(book, inst, h["notional"], y)) > 1e-3
    # A large curve move leaves residual (2nd-order) P&L even though DV01 is hedged.
    up = hedged_pnl(book, inst, h["notional"], y, +0.01)
    down = hedged_pnl(book, inst, h["notional"], y, -0.01)
    # Convexity => up and down moves do not cancel; net is second-order, non-zero.
    assert abs(up + down) > 1e-4


def test_futures_variation_margin_sums_to_linear_payoff():
    out = futures_variation_margin(entry_price=100.0, price_path=[101.0, 99.0, 102.0],
                                   contract_size=1000.0, position=-2.0)
    # Short 2 contracts: daily MtM sums to the linear payoff to terminal price.
    assert math.isclose(out["total"], out["linear_payoff"], rel_tol=1e-12)
    assert math.isclose(out["total"], -2.0 * 1000.0 * (102.0 - 100.0), rel_tol=1e-12)
