"""Per-tooth mutation tests for the regime-aware trinomial pricer (FRT-1)."""
import math

import pytest

from open_ep_framework.flow_regime.trinomial import (
    EuropeanOption, NodeProbs, RegimeAwareTrinomial, RegimeSpec, TrinomialError,
    black_scholes_reference,
)


def _atm_call(rate=0.05):
    return EuropeanOption(spot=100.0, strike=100.0, vol=0.20, maturity=1.0, rate=rate, call=True)


# --- TOOTH: memoryless limit converges to Black-Scholes (VERIFIES) --------- #
def test_memoryless_converges_to_black_scholes():
    opt = _atm_call()
    bs = black_scholes_reference(opt)
    diffs = []
    for n in (50, 100, 200, 400):
        p = RegimeAwareTrinomial(opt, RegimeSpec(kind="memoryless"), steps=n).price()
        diffs.append(abs(p - bs))
    assert diffs[-1] < 8e-3, f"memoryless trinomial did not reach BS: diff={diffs[-1]}"
    # convergence: error strictly shrinks as the step count grows
    assert all(diffs[i + 1] < diffs[i] for i in range(len(diffs) - 1)), diffs


def test_memoryless_put_matches_black_scholes():
    opt = EuropeanOption(spot=100, strike=110, vol=0.25, maturity=0.75, rate=0.03, call=False)
    bs = black_scholes_reference(opt)
    p = RegimeAwareTrinomial(opt, RegimeSpec(kind="memoryless"), steps=400).price()
    assert abs(p - bs) < 1e-2


# --- TOOTH: OU regime prices mean reversion -> DIFFERS from BS (VERIFIES) --- #
def test_mean_reverting_differs_from_black_scholes():
    opt = _atm_call()
    bs = black_scholes_reference(opt)
    reg = RegimeSpec.from_ou_characterization(theta=1.5, mu=90.0)
    p = RegimeAwareTrinomial(opt, reg, steps=200).price()
    assert abs(p - bs) > 0.25, "mean reversion was not priced (OU price == BS)"


def test_mean_reverting_target_shifts_price_monotonically():
    # a lower reversion target for a call must not price above a higher target
    opt = _atm_call()
    lo = RegimeAwareTrinomial(opt, RegimeSpec.from_ou_characterization(1.5, 80.0), steps=200).price()
    hi = RegimeAwareTrinomial(opt, RegimeSpec.from_ou_characterization(1.5, 110.0), steps=200).price()
    assert hi > lo


# --- TOOTH: the middle branch projects to the regime's stable point -------- #
def test_middle_branch_projects_to_stable_point():
    # at the reversion target mu (lattice level j=0) the OU drift vanishes: the ternary
    # "stay" branch is symmetric (pu == pd) and centred on mu.
    opt = _atm_call()
    reg = RegimeSpec.from_ou_characterization(theta=1.0, mu=100.0)
    tri = RegimeAwareTrinomial(opt, reg, steps=200)
    a = reg.theta
    dt = opt.maturity / tri.steps
    jmax = max(2, math.ceil(0.184 / (a * dt)))
    center = tri._hw_node_probs(0, jmax, a, dt)  # j=0 == mu
    assert abs(center.pu - center.pd) < 1e-12, "stay branch not symmetric at mu"
    assert center.pm >= center.pu and center.pm >= center.pd, "stay branch not dominant at mu"


# --- TOOTH: branch probabilities in [0,1] and normalized (COHERENCE) ------- #
def test_branch_probabilities_in_unit_interval_and_normalized():
    opt = _atm_call()
    for reg in (RegimeSpec(kind="memoryless"),
                RegimeSpec.from_ou_characterization(1.5, 90.0)):
        tri = RegimeAwareTrinomial(opt, reg, steps=200)
        tri.price()
        for pu, pm, pd in tri.node_probabilities():
            assert 0.0 <= pu <= 1.0 and 0.0 <= pm <= 1.0 and 0.0 <= pd <= 1.0
            assert abs(pu + pm + pd - 1.0) < 1e-9


# --- TOOTH: a probability outside [0,1] is REJECTED (mutation) -------------- #
def test_negative_middle_branch_rejected():
    with pytest.raises(TrinomialError):
        NodeProbs(0.6, -0.2, 0.6, 1, 0, -1).validate()


def test_non_normalized_probabilities_rejected():
    with pytest.raises(TrinomialError):
        NodeProbs(0.5, 0.5, 0.5, 1, 0, -1).validate()


# --- TOOTH: regime-really-consumed guard (no-numerology) ------------------- #
def test_regime_really_consumed_guard():
    # a genuinely regime-aware pricer MUST move the price off BS in the OU regime;
    # a record whose OU price equals BS proves the regime was never consumed.
    opt = _atm_call()
    bs = black_scholes_reference(opt)
    ou = RegimeAwareTrinomial(opt, RegimeSpec.from_ou_characterization(1.5, 90.0), steps=200).price()
    assert not math.isclose(ou, bs, abs_tol=0.25), "regime not consumed: OU price == BS"


# --- TOOTH: an inadmissible regime spec is REJECTED (mutation) -------------- #
def test_mean_reverting_requires_positive_theta_and_mu():
    with pytest.raises(TrinomialError):
        RegimeSpec(kind="mean_reverting", theta=0.0, mu=100.0)
    with pytest.raises(TrinomialError):
        RegimeSpec(kind="mean_reverting", theta=1.0, mu=0.0)


def test_unknown_regime_kind_rejected():
    with pytest.raises(TrinomialError):
        RegimeSpec(kind="quantum_woo")


# --- consume-by-reference: OU half-life == ln2/theta ----------------------- #
def test_half_life_matches_ou_characterizer():
    reg = RegimeSpec.from_ou_characterization(theta=1.5, mu=90.0)
    assert math.isclose(reg.half_life, math.log(2.0) / 1.5, rel_tol=1e-12)
    assert reg.source_regime == "ornstein_uhlenbeck"
