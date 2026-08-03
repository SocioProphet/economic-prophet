"""Per-tooth tests for the welfare-annealing dynamics (WEA-1), incl. the FRL-1 lens reuse."""
import pytest

from open_ep_framework.welfare_annealing.anneal import (
    AnnealError, CHAOS_LAMBDA, assert_descends, free_energy, project_to_simplex,
    regime_for_taxonomy, run_anneal,
)
from open_ep_framework.welfare_annealing.qol import groups_from_records

_GROUPS = groups_from_records([
    {"name": "A", "population": 5.0, "life_length": 0.50, "health": 0.50, "education": 0.50,
     "half_saturation": 0.3},
    {"name": "B", "population": 40.0, "life_length": 0.95, "health": 0.95, "education": 0.95,
     "half_saturation": 0.3},
    {"name": "C", "population": 15.0, "life_length": 0.40, "health": 0.40, "education": 0.40,
     "half_saturation": 0.3},
])
_X0 = [2.0, 2.0, 2.0]
_E = 6.0


# --- VERIFIES: healthy anneal is laminar, monotone, conserving ------------- #
def test_healthy_anneal_is_laminar_monotone_conserving():
    r = run_anneal(_GROUPS, _X0, lr=0.3, steps=400, energy=_E)
    assert r.regime == "laminar"
    assert r.monotone_descent is True
    assert r.settled is True
    assert r.energy_conserved is True
    assert r.lyapunov < 0.0            # contraction (laminar), below CHAOS_LAMBDA
    assert r.lyapunov < CHAOS_LAMBDA


def test_anneal_lowers_free_energy_and_raises_welfare():
    r = run_anneal(_GROUPS, _X0, lr=0.3, steps=400, energy=_E)
    assert r.free_energy[-1] < r.free_energy[0]      # free-energy DROPS
    assert r.welfare[-1] > r.welfare[0]              # welfare (QoL) RISES
    # gains-from-trade = the potential drop, NOT substance creation: energy is unchanged
    assert abs(sum(r.fixed_point) - _E) < 1e-6
    assert r.free_energy[0] - r.free_energy[-1] == pytest.approx(r.welfare_gain)


def test_conservation_holds_every_step():
    r = run_anneal(_GROUPS, _X0, lr=0.3, steps=200, energy=_E)
    assert r.energy_conserved is True


# --- TOOTH: manipulated / over-driven anneal is TURBULENT (FRL-1 lens) ----- #
def test_overdriven_anneal_is_turbulent():
    r = run_anneal(_GROUPS, _X0, lr=2.0, steps=400, energy=_E)
    assert r.regime == "turbulent"
    # it fails to settle into the laminar welfare attractor with monotone descent
    assert not (r.settled and r.monotone_descent)


# --- TOOTH: a wrong-direction (free-energy-increasing) anneal is REJECTED --- #
def test_assert_descends_rejects_non_monotone():
    r = run_anneal(_GROUPS, _X0, lr=2.0, steps=400, energy=_E)
    assert r.monotone_descent is False
    with pytest.raises(AnnealError):
        assert_descends(r)


def test_assert_descends_passes_healthy():
    r = run_anneal(_GROUPS, _X0, lr=0.3, steps=400, energy=_E)
    assert assert_descends(r) is r


# --- TOOTH: FRL-1 taxonomy->regime map consumed by reference --------------- #
def test_taxonomy_maps_by_reference():
    assert regime_for_taxonomy("short_decaying") == "laminar"
    assert regime_for_taxonomy("memoryless") == "laminar"
    assert regime_for_taxonomy("chaotic") == "turbulent"
    with pytest.raises(AnnealError):
        regime_for_taxonomy("not_a_regime")


# --- projection conserves energy exactly ----------------------------------- #
def test_projection_conserves_and_clips():
    p = project_to_simplex([5.0, -1.0, 2.0], 6.0)
    assert min(p) >= 0.0
    assert sum(p) == pytest.approx(6.0)


def test_bad_learning_rate_rejected():
    with pytest.raises(AnnealError):
        run_anneal(_GROUPS, _X0, lr=0.0, steps=10, energy=_E)


def test_free_energy_is_negative_welfare():
    from open_ep_framework.welfare_annealing.qol import total_welfare
    x = [2.0, 2.0, 2.0]
    assert free_energy(_GROUPS, x) == pytest.approx(-total_welfare(_GROUPS, x))
