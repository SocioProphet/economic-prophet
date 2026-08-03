"""Per-tooth mutation tests for the low-dimensional flow-regime lens (FRL-1)."""
import os
import sys
from pathlib import Path

import pytest

from open_ep_framework.flow_regime.lorenz import (
    CHAOS_LAMBDA, LORENZ_CLASSIC, FlowRegimeError, benettin_lyapunov, classify_flow,
    eigenvalues, fixed_points, is_stable_fixed_point, lyapunov_sign_agrees,
    reject_navier_stokes_overclaim,
)


# --- TOOTH: classic Lorenz set classifies turbulent (VERIFIES) ------------- #
def test_classic_lorenz_is_turbulent():
    cls = classify_flow(LORENZ_CLASSIC)
    assert cls.lambda_max > CHAOS_LAMBDA, cls.lambda_max
    assert cls.regime == "turbulent"
    assert cls.stable_fixed_point is False
    # literature largest Lyapunov ~= 0.906; our Benettin estimate must be near-positive
    assert 0.7 < cls.lambda_max < 1.1


def test_classic_lorenz_origin_is_unstable():
    # the origin has a positive real eigenvalue for rho>1 (convection sets in)
    origin = (0.0, 0.0, 0.0)
    reals = [ev.real for ev in eigenvalues(origin, LORENZ_CLASSIC)]
    assert max(reals) > 0.0


# --- TOOTH: sub-critical Rayleigh classifies laminar (VERIFIES) ------------ #
def test_low_rayleigh_is_laminar():
    cls = classify_flow((10.0, 0.5, 8.0 / 3.0))
    assert cls.lambda_max < 0.0
    assert cls.regime == "laminar"
    assert cls.stable_fixed_point is True


def test_convective_pair_stable_below_hopf():
    # for 1 < rho < ~24.74 the C+/- fixed points are stable -> laminar
    cls = classify_flow((10.0, 10.0, 8.0 / 3.0))
    assert cls.regime == "laminar"
    assert cls.stable_fixed_point is True
    assert any(lbl in ("C+", "C-") for lbl, _ in fixed_points((10.0, 10.0, 8.0 / 3.0)))


# --- TOOTH: Lyapunov sign agrees with the memory-mesh taxonomy ------------- #
def test_lyapunov_sign_agrees_with_taxonomy():
    turb = classify_flow(LORENZ_CLASSIC)
    lam = classify_flow((10.0, 0.5, 8.0 / 3.0))
    assert lyapunov_sign_agrees(turb, "chaotic")
    assert lyapunov_sign_agrees(lam, "memoryless")
    # and it FIRES on a mismatch
    assert not lyapunov_sign_agrees(turb, "memoryless")
    assert not lyapunov_sign_agrees(lam, "chaotic")


# --- TOOTH: Navier-Stokes over-claim is REJECTED (mutation) ---------------- #
def test_navier_stokes_overclaim_rejected():
    with pytest.raises(FlowRegimeError):
        reject_navier_stokes_overclaim(
            "This Lorenz reduction proves Navier-Stokes global existence and smoothness."
        )
    with pytest.raises(FlowRegimeError):
        reject_navier_stokes_overclaim(["benign", "we resolve the Navier-Stokes regularity problem"])


def test_benign_navier_stokes_mention_allowed():
    # naming Navier-Stokes as the physical system being ANALOGIZED is fine
    reject_navier_stokes_overclaim(
        "An analogue lens for Navier-Stokes turbulence; it does not address existence."
    )
    reject_navier_stokes_overclaim(None)


# --- TOOTH: non-physical parameters are REJECTED (mutation) ---------------- #
def test_nonphysical_params_rejected():
    with pytest.raises(FlowRegimeError):
        classify_flow((-1.0, 28.0, 8.0 / 3.0))
    with pytest.raises(FlowRegimeError):
        classify_flow((10.0, 28.0, -1.0))


# --- consume-by-reference: the memory-mesh Lyapunov estimator, when present  #
def test_memory_mesh_estimator_reuse_when_available():
    """Genuinely REUSE the memory-mesh Rosenstein estimator via the injection seam.

    Hermetic CI has no sibling repo -> this skips cleanly; when the memory-mesh
    characterizer is checked out alongside, its estimator is injected and must agree in
    SIGN (positive on the classic Lorenz attractor) with the local Benettin exponent."""
    candidates = [
        Path.home() / "dev" / "memory-mesh" / "scripts",
        Path(os.environ.get("MEMORY_MESH_SCRIPTS", "")),
    ]
    est = None
    for c in candidates:
        if c and (c / "memory_regime_estimators.py").exists():
            sys.path.insert(0, str(c))
            import memory_regime_estimators as est  # noqa: F811
            break
    if est is None:
        pytest.skip("memory-mesh characterizer not available (hermetic CI)")
    injected = classify_flow(LORENZ_CLASSIC, lyapunov_fn=est.lyapunov_rosenstein)
    assert injected.lyapunov_source == "lyapunov_rosenstein"
    # SIGN agreement is the tooth: the memory-mesh Rosenstein estimator returns a
    # per-sample-step divergence slope (magnitude scales with the sampling dt, so it is
    # not directly comparable to the per-unit-time CHAOS_LAMBDA threshold), but its SIGN
    # must be positive on the chaotic Lorenz attractor -- agreeing with the local
    # per-unit-time Benettin exponent, which is what the estate cross-check asserts.
    assert injected.lambda_max > 0.0, "memory-mesh estimator disagrees on Lorenz sign"
    assert classify_flow(LORENZ_CLASSIC).lambda_max > 0.0  # Benettin agrees in sign
