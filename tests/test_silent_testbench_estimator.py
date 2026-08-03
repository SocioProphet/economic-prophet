"""Per-tooth tests: the 'Silent Weapons' shock-test estimator IS ordinary econometrics."""
import math

import pytest

from open_ep_framework.silent_testbench.shock_estimator import (
    DemandSystem, ShockTestError, demonstrate_estimator_is_var, ols_elasticities,
    reject_conspiracy_overclaim, shock_test, solve_for_inputs, var1_impulse_matrix,
)
from open_ep_framework.silent_testbench import linalg


def _system():
    return DemandSystem(
        goods=("gasoline", "transit"),
        elasticities=[[-0.30, 0.10], [0.15, -0.45]],
        log_intercepts=[2.0, 1.5],
    )


# --- TOOTH: the shock test recovers the true cross-price elasticity matrix ---- #
def test_shock_test_recovers_elasticities():
    system = _system()
    res = shock_test(system, base_prices=[3.0, 2.0])
    assert linalg.max_abs_diff(res.recovered_elasticities, system.elasticities) < 1e-9


# --- TOOTH: shock-test == OLS == VAR impulse response (the equivalence) ------- #
def test_estimator_is_var_equivalence():
    demo = demonstrate_estimator_is_var(_system(), [3.0, 2.0])
    assert demo["equivalent"] is True
    assert demo["max_dev_shock_vs_truth"] < 1e-6
    assert demo["max_dev_ols_vs_truth"] < 1e-6
    assert demo["max_dev_shocktest_vs_ols"] < 1e-6
    assert demo["max_dev_irf_vs_shocktest"] < 1e-12   # IRF horizon-0 IS the impact matrix


def test_ols_matches_shock_test():
    system = _system()
    a = shock_test(system, [3.0, 2.0]).recovered_elasticities
    b = ols_elasticities(system, [3.0, 2.0]).recovered_elasticities
    assert linalg.max_abs_diff(a, b) < 1e-6


def test_var_irf_horizon0_is_impact_matrix():
    a = [[-0.30, 0.10], [0.15, -0.45]]
    assert var1_impulse_matrix(a, horizon=0) == a


# --- TOOTH: solve/invert are exact linear algebra --------------------------- #
def test_solve_and_invert_roundtrip():
    system = _system()
    res = shock_test(system, [3.0, 2.0])
    a, b = res.recovered_elasticities, res.inverse_matrix
    prod = linalg.matmul(a, b)
    ident = [[1.0 if i == j else 0.0 for j in range(2)] for i in range(2)]
    assert linalg.max_abs_diff(prod, ident) < 1e-9
    y = [0.3, -0.2]
    x = solve_for_inputs(a, y)
    assert linalg.max_abs_diff(linalg.matvec(a, x), y) < 1e-9


# --- TOOTH: a singular (collinear) system is REJECTED, not silently fudged ---- #
def test_singular_system_rejected():
    system = DemandSystem(goods=("a", "b"), elasticities=[[0.0, 0.0], [0.0, 0.0]],
                          log_intercepts=[0.0, 0.0])
    with pytest.raises(ShockTestError):
        shock_test(system, [1.0, 1.0])


def test_bad_shock_rejected():
    with pytest.raises(ShockTestError):
        shock_test(_system(), [3.0, 2.0], rel_shock=0.0)
    with pytest.raises(ShockTestError):
        shock_test(_system(), [3.0], rel_shock=0.01)


# --- TOOTH: reproducing the mechanism does NOT confirm the conspiracy -------- #
def test_conspiracy_overclaim_rejected():
    with pytest.raises(ShockTestError):
        reject_conspiracy_overclaim("Reproducing this estimator confirms the Silent Weapons conspiracy.")
    with pytest.raises(ShockTestError):
        reject_conspiracy_overclaim(["benign", "this proves the depopulation plot"])


def test_benign_mention_allowed():
    # naming the document as the object under audit is fine
    reject_conspiracy_overclaim("An audit of the Silent Weapons shock-test estimator.")
    reject_conspiracy_overclaim(None)


# --- consistency: finite-difference shock == analytic elasticity for logs ----- #
def test_finite_difference_is_log_derivative():
    system = _system()
    res = shock_test(system, [3.0, 2.0], rel_shock=1e-6)
    # for a log-linear system the finite difference equals the analytic slope exactly
    assert math.isclose(res.recovered_elasticities[0][0], -0.30, abs_tol=1e-6)
