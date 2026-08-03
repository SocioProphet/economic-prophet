"""Teeth for Basel IRB-Advanced capital, AMA op-risk, and the reg-vs-economic comparison."""
from open_ep_framework.regulatory_capital import (
    irb_correlation, irb_capital_requirement, irb_regulatory_capital,
    oprisk_ama_capital, economic_capital_credit, economic_vs_regulatory,
    OpRiskCell, OPRISK_EVENT_TYPES,
)


def test_irb_correlation_bounds_and_monotonic():
    assert 0.12 <= irb_correlation(0.20) <= 0.24
    assert irb_correlation(0.001) > irb_correlation(0.20)   # decreases with PD
    assert abs(irb_correlation(0.0) - 0.24) < 1e-6          # PD→0 → 0.24
    assert abs(irb_correlation(1.0) - 0.12) < 1e-6          # PD→1 → 0.12


def test_irb_K_increases_with_pd_lgd_maturity():
    base = irb_capital_requirement(0.02, 0.45, 2.5)
    assert base > 0
    assert irb_capital_requirement(0.05, 0.45, 2.5) > base   # higher PD
    assert irb_capital_requirement(0.02, 0.60, 2.5) > base   # higher LGD
    assert irb_capital_requirement(0.02, 0.45, 5.0) > base   # longer maturity


def test_irb_regulatory_capital_identities():
    out = irb_regulatory_capital(0.02, 0.45, 100.0, 2.5)
    assert abs(out["regulatory_capital"] - 0.08 * out["rwa"]) < 1e-3  # rounding artifact
    assert abs(out["rwa"] - out["capital_requirement_K"] * 12.5 * 100.0) < 1e-2
    assert abs(out["expected_loss"] - 0.02 * 0.45 * 100.0) < 1e-9
    # sanity: a 2% PD / 45% LGD corporate loan carries roughly 6-10% capital of EAD
    assert 3.0 < out["regulatory_capital"] < 12.0


def _cells():
    return [OpRiskCell(t, annual_frequency=2.0, severity_mu=0.0, severity_sigma=1.2)
            for t in OPRISK_EVENT_TYPES]


def test_oprisk_var_exceeds_mean_and_capital_positive():
    out = oprisk_ama_capital(_cells(), sims=4000, seed=1)
    assert out["oprisk_var_999"] > out["expected_annual_loss"]
    assert out["oprisk_capital"] > 0
    assert out["oprisk_es_999"] >= out["oprisk_var_999"]


def test_oprisk_scales_with_frequency():
    low = oprisk_ama_capital([OpRiskCell("internal_fraud", 1.0, 0.0, 1.0)], sims=4000, seed=2)
    high = oprisk_ama_capital([OpRiskCell("internal_fraud", 6.0, 0.0, 1.0)], sims=4000, seed=2)
    assert high["oprisk_var_999"] > low["oprisk_var_999"]


def test_economic_capital_rises_with_own_correlation():
    lo = economic_capital_credit(0.02, 0.45, 100.0, rho=0.10, confidence=0.999)
    hi = economic_capital_credit(0.02, 0.45, 100.0, rho=0.30, confidence=0.999)
    assert hi > lo > 0


def test_economic_vs_regulatory_reports_both_and_divergence():
    out = economic_vs_regulatory(0.02, 0.45, 100.0, oprisk_cells=_cells(),
                                 market_capital=5.0, own_rho=0.20, diversification=0.15)
    assert out["regulatory"]["total"] > 0 and out["economic"]["total"] > 0
    assert out["divergence"]["binding_constraint"] in ("economic", "regulatory")
    # diversification pulls economic below its standalone sum
    assert out["economic"]["total"] < (out["economic"]["credit"] + out["economic"]["operational"] + out["economic"]["market"]) + 1e-6
    assert out["divergence"]["economic_pct_of_regulatory"] is not None
