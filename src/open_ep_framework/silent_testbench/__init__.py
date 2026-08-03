"""silent_testbench -- an audit-only falsification of "Silent Weapons for Quiet Wars".

This module is a CONFRONTATION, not an operationalisation. It implements the pamphlet's
own "shock-test" estimator (SILENT pp.26-29) and its "paper-inductance oscillation" claim
on this repo's engines BY REFERENCE, then confronts each mechanism with cited historical
reference data and grades it with a verdict + receipt.

Phase 1 -- the executable simulator:
  * ``shock_estimator`` implements ``P = Σ a_jk X_k``, recovers ``a_jk = ∂P/∂X_k`` by
    shocking prices, assembles/inverts ``[a_jk] -> [b_kj]``, and SHOWS this is exactly
    cross-price-elasticity / VAR impulse-response identification (ordinary econometrics).
  * ``oscillation`` reads the excess-debt "self-destructive oscillation" as a near-critical
    / limit-cycle regime, reusing the flow_regime Lorenz lens (#54) and its Lyapunov/regime
    taxonomy BY REFERENCE.

Phase 2 -- the empirical confrontation (``confront`` + ``fixtures``):
  * MECH-1 shock-test estimator      -> RELABELING of ordinary econometrics
  * MECH-2 behavioural shock claim   -> REJECTED (no out-of-sample coefficient)
  * MECH-3 debt -> instability (weak) -> PARTLY_HOLDS
  * MECH-4 debt -> depopulation (strong) -> FALSIFIED against the historical record

Teeth run in both directions. Reproducing the mechanism is NOT confirming the conspiracy;
an ``reject_conspiracy_overclaim`` guard refuses any record that says otherwise.

Deterministic and stdlib-only (hermetic CI). This feeds the Phase-4 firewall synthesis.
"""
from . import confront, fixtures, linalg, oscillation, shock_estimator  # noqa: F401

__all__ = ["shock_estimator", "oscillation", "fixtures", "confront", "linalg"]
