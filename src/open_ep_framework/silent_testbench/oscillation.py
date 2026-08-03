"""PAPER-INDUCTANCE OSCILLATION (SILENT) -> the near-critical / limit-cycle regime.

"Silent Weapons for Quiet Wars" pushes its circuit analogy to a specific dynamical claim:
money/credit behaves like an *inductance*, and an economy carrying excess public debt is
like an over-energised LC/RLC circuit -- it enters a "self-destructive oscillation" that
the controller must damp (the doc's chilling gloss is that the population is the resistor
that dissipates the energy). We take the DYNAMICS seriously and the gloss NOT at all:

  * WEAK FORM (dynamics): a debt-service feedback loop is a second-order oscillator
        D'' + 2*zeta*omega * D' + omega^2 (D - D*) = 0
    whose stability is set by the damping ratio zeta. zeta>0 -> damped -> stable ("laminar");
    zeta≈0 -> sustained oscillation (a limit cycle / near-critical); zeta<0 -> divergent
    (unstable). We classify by the eigenvalues of the linearisation -- the SAME
    sign-of-real-part test the flow_regime Lorenz engine uses -- and, for the strongly
    nonlinear high-debt case, we hand the parameters to the flow_regime Lorenz lens (#54)
    BY REFERENCE and let its Lyapunov exponent decide laminar vs turbulent.

  * STRONG FORM (the doc's gloss: population-negation as the balancing "resistance") is a
    behavioural/eschatological claim, NOT a dynamical one, and is confronted -- and
    FALSIFIED -- against the historical record in ``confront.py``. Nothing here operationalises
    it; this module only reads REGIME.

Consume-by-reference: the Lyapunov estimator, the CHAOS_LAMBDA threshold and the
laminar/turbulent taxonomy are the flow_regime Lorenz module's property (which in turn
consumes the memory-mesh characterizer). We map an economic debt-load onto the Lorenz
drive parameter (the reduced Rayleigh number ``rho``) and reuse ``classify_flow`` unchanged.

Deterministic and stdlib-only.
"""
from __future__ import annotations

import cmath
import math
from dataclasses import dataclass

from ..flow_regime.lorenz import (
    CHAOS_LAMBDA, FlowClassification, classify_flow, lyapunov_sign_agrees,
)


class OscillationError(ValueError):
    """Raised for an inadmissible oscillator configuration -- REJECTED."""


# --------------------------------------------------------------------------- #
# The paper-inductance second-order oscillator (RLC analogue).
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class DebtOscillator:
    """A linear debt-service oscillator D'' + 2*zeta*omega*D' + omega^2 (D-D*) = 0.

    ``omega`` (>0) is the natural frequency of the debt/refinancing loop; ``zeta`` is the
    damping ratio delivered by fiscal/monetary response. In the circuit analogy omega ~
    1/sqrt(LC) and 2*zeta*omega ~ R/L: the "population as resistor" gloss is the claim that
    R (hence zeta) must be supplied by dissipating the public. We treat zeta as an ordinary
    policy parameter and read the regime it implies.
    """
    omega: float
    zeta: float

    def __post_init__(self) -> None:
        if self.omega <= 0:
            raise OscillationError("natural frequency omega must be positive")

    def eigenvalues(self) -> tuple[complex, complex]:
        """Roots of s^2 + 2*zeta*omega s + omega^2 = 0."""
        w, z = self.omega, self.zeta
        disc = cmath.sqrt(complex((z * w) ** 2 - w * w))
        return (-z * w + disc, -z * w - disc)

    def regime(self) -> str:
        """laminar (damped, Re<0) | limit_cycle (undamped, Re≈0) | unstable (Re>0)."""
        reals = [ev.real for ev in self.eigenvalues()]
        m = max(reals)
        if m > 1e-9:
            return "unstable"
        if m < -1e-9:
            return "laminar"
        return "limit_cycle"

    @property
    def is_unstable(self) -> bool:
        return self.regime() in ("unstable", "limit_cycle")


# --------------------------------------------------------------------------- #
# Mapping a debt load onto the Lorenz drive, then reusing the flow-regime lens.
# --------------------------------------------------------------------------- #
# Below this debt/GDP ratio the economy is treated as sub-critically driven (laminar);
# above it the drive is super-critical. The number is the Reinhart-Rogoff/HAP-era
# discussion threshold (see fixtures.py) used ONLY as a monotone knob onto rho, NOT as a
# causal cliff -- the honest weak-form reading (fixtures record the HAP 2013 correction).
DEBT_GDP_REFERENCE = 0.90

# Lorenz geometry held at the classic sigma/beta; only the drive rho varies with debt.
_SIGMA = 10.0
_BETA = 8.0 / 3.0
# The Hopf bifurcation of the classic Lorenz system (sigma=10, beta=8/3) sits at
# rho_H = sigma(sigma+beta+3)/(sigma-beta-1) ≈ 24.74; above it the convective fixed
# points lose stability and the flow becomes turbulent.
_RHO_HOPF = _SIGMA * (_SIGMA + _BETA + 3.0) / (_SIGMA - _BETA - 1.0)


def debt_to_lorenz_rho(debt_gdp: float, gain: float = 40.0) -> float:
    """Map a debt/GDP ratio to the Lorenz drive rho (monotone, deterministic).

    rho = 1 + gain * (debt_gdp / DEBT_GDP_REFERENCE): at the reference ratio the drive is
    ~1+gain (super-critical for gain>=24); low debt maps below the Hopf point (laminar).
    """
    if debt_gdp < 0:
        raise OscillationError("debt/GDP ratio cannot be negative")
    return 1.0 + gain * (debt_gdp / DEBT_GDP_REFERENCE)


@dataclass
class OscillationVerdict:
    debt_gdp: float
    lorenz_params: tuple
    flow: FlowClassification
    rho_hopf: float
    near_or_super_critical: bool
    weak_form_holds: bool          # high debt -> unstable/turbulent regime


def classify_debt_regime(debt_gdp: float, gain: float = 40.0,
                         lyapunov_fn=None) -> OscillationVerdict:
    """Reuse the flow_regime Lorenz lens (#54) to read the regime of a debt load.

    Maps debt/GDP -> Lorenz rho, then calls ``classify_flow`` BY REFERENCE. The weak-form
    claim "high debt -> instability" holds for a fixture iff a super-critical debt load
    classifies turbulent (positive Lyapunov, no stable fixed point).
    """
    rho = debt_to_lorenz_rho(debt_gdp, gain=gain)
    params = (_SIGMA, rho, _BETA)
    flow = classify_flow(params, lyapunov_fn=lyapunov_fn)
    super_critical = rho > _RHO_HOPF
    weak_form = super_critical and flow.is_turbulent and not flow.stable_fixed_point
    return OscillationVerdict(
        debt_gdp=debt_gdp, lorenz_params=params, flow=flow, rho_hopf=_RHO_HOPF,
        near_or_super_critical=super_critical, weak_form_holds=weak_form,
    )


def oscillation_taxonomy_agrees(verdict: OscillationVerdict) -> bool:
    """The debt-regime flow classification must agree with the memory-mesh taxonomy.

    A super-critical (high-debt) load is 'chaotic' -> must read turbulent; a sub-critical
    load is a stable regime -> must read laminar. Delegates to the flow_regime tooth.
    """
    label = "chaotic" if verdict.near_or_super_critical else "memoryless"
    return lyapunov_sign_agrees(verdict.flow, label)


__all__ = [
    "CHAOS_LAMBDA", "DEBT_GDP_REFERENCE", "DebtOscillator", "OscillationError",
    "OscillationVerdict", "classify_debt_regime", "debt_to_lorenz_rho",
    "oscillation_taxonomy_agrees",
]
