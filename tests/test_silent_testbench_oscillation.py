"""Per-tooth tests: the paper-inductance oscillation lens (reuses flow_regime by reference)."""
import pytest

from open_ep_framework.silent_testbench.oscillation import (
    DebtOscillator, OscillationError, classify_debt_regime, debt_to_lorenz_rho,
    oscillation_taxonomy_agrees,
)


# --- TOOTH: the damping ratio sets the regime (laminar/limit-cycle/unstable) -- #
def test_damped_oscillator_is_laminar():
    assert DebtOscillator(omega=1.0, zeta=0.3).regime() == "laminar"


def test_undamped_oscillator_is_limit_cycle():
    assert DebtOscillator(omega=1.0, zeta=0.0).regime() == "limit_cycle"


def test_negative_damping_is_unstable():
    osc = DebtOscillator(omega=1.0, zeta=-0.1)
    assert osc.regime() == "unstable"
    assert osc.is_unstable is True


def test_nonphysical_frequency_rejected():
    with pytest.raises(OscillationError):
        DebtOscillator(omega=0.0, zeta=0.1)


# --- TOOTH: high debt -> super-critical -> turbulent (reuse flow_regime lens) -- #
def test_high_debt_classifies_turbulent():
    v = classify_debt_regime(1.72)     # Greece 2012 peak debt/GDP
    assert v.near_or_super_critical is True
    assert v.flow.regime == "turbulent"
    assert v.flow.stable_fixed_point is False
    assert v.weak_form_holds is True


def test_low_debt_classifies_laminar():
    v = classify_debt_regime(0.20)
    assert v.near_or_super_critical is False
    assert v.flow.regime == "laminar"
    assert v.flow.stable_fixed_point is True
    assert v.weak_form_holds is False


# --- TOOTH: the debt->rho map is monotone and crosses the Hopf point ---------- #
def test_debt_to_rho_monotone_and_crosses_hopf():
    assert debt_to_lorenz_rho(0.20) < debt_to_lorenz_rho(0.90)
    lo = classify_debt_regime(0.20)
    hi = classify_debt_regime(0.90)
    assert lo.lorenz_params[1] < lo.rho_hopf < hi.lorenz_params[1]


def test_negative_debt_rejected():
    with pytest.raises(OscillationError):
        debt_to_lorenz_rho(-0.1)


# --- TOOTH: the regime agrees with the memory-mesh taxonomy (delegated) ------- #
def test_regime_agrees_with_taxonomy():
    assert oscillation_taxonomy_agrees(classify_debt_regime(1.72)) is True
    assert oscillation_taxonomy_agrees(classify_debt_regime(0.20)) is True
