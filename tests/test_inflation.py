"""Teeth for the alternative-inflation reconstructions — proprietary sources rebuilt, verifiably."""
from open_ep_framework.inflation import (
    billion_prices_index, shadowstats_alt_cpi, MethodologyAddbacks,
    real_rate, inflation_wedge,
)


def test_bpp_flat_panel_is_no_inflation():
    panel = [{"a": 10, "b": 20}, {"a": 10, "b": 20}, {"a": 10, "b": 20}]
    out = billion_prices_index(panel)
    assert out["index"][-1] == 100.0
    assert out["annualized_inflation"] == 0.0
    assert out["reconstructed"] is True


def test_bpp_doubling_prices_doubles_the_jevons_index():
    # every matched price doubles each step -> geometric relative = 2 -> index doubles
    panel = [{"a": 10, "b": 20}, {"a": 20, "b": 40}]
    out = billion_prices_index(panel)
    assert abs(out["index"][-1] - 200.0) < 1e-6


def test_bpp_matched_model_ignores_unmatched_products():
    # 'c' appears only in t1 (new product) -> excluded from the relative
    panel = [{"a": 10}, {"a": 11, "c": 99}]
    out = billion_prices_index(panel)
    assert abs(out["index"][-1] - 110.0) < 1e-6


def test_shadowstats_alt_exceeds_official_by_addbacks():
    out = shadowstats_alt_cpi(0.031, basis="1990")
    assert out["alt_inflation"] > out["official_inflation"]
    assert abs(out["alt_inflation"] - (out["official_inflation"] + out["addback"])) < 1e-9
    assert out["reconstructed"] is True


def test_shadowstats_1980_basis_higher_than_1990():
    a90 = shadowstats_alt_cpi(0.031, basis="1990")["alt_inflation"]
    a80 = shadowstats_alt_cpi(0.031, basis="1980")["alt_inflation"]
    assert a80 > a90


def test_shadowstats_addbacks_are_configurable():
    zero = MethodologyAddbacks(0, 0, 0, 0)
    out = shadowstats_alt_cpi(0.031, basis="1990", addbacks=zero)
    assert abs(out["alt_inflation"] - 0.031) < 1e-9  # no methodology delta -> equals official


def test_real_rate_is_exact_fisher():
    assert abs(real_rate(0.05, 0.03) - ((1.05 / 1.03) - 1.0)) < 1e-12
    # higher inflation measure -> lower real rate (the whole point for pricing real assets)
    assert real_rate(0.05, 0.06) < real_rate(0.05, 0.03)


def test_inflation_wedge_signs():
    w = inflation_wedge(0.045, 0.031, 0.072)
    assert w["bpp_vs_official_pp"] > 0
    assert w["shadowstats_vs_official_pp"] > w["bpp_vs_official_pp"]
