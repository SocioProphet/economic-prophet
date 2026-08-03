"""Welfare-annealing dynamics: a gradient flow over allocations descending a free-energy
potential toward the maximal-welfare attractor.

The anneal is a state machine over allocations ``x`` on the fixed-energy simplex
``{x : sum_i x_i = E, x_i >= 0}``. It descends the **free-energy potential**

    F(x) = -W(x)          (the zero-temperature limit of a simulated anneal)

by projected gradient flow. Because the welfare functional ``W`` (see ``qol``) is strictly
CONCAVE in each allocation, ``F`` is convex and the flow

    g_i    = dF/dx_i = -marginal_welfare_i          (points "downhill" in F)
    x <-   project_to_simplex( x - lr * (g - mean(g)) )   # sum-preserving descent

converges to the UNIQUE welfare-maximizing allocation -- the point of EQUAL MARGINAL
WELFARE across groups. The subtracted ``mean(g)`` projects each step onto the sum-zero
subspace, so **every step conserves the total value-energy E** (the anneal reconfigures the
SAME conserved substance; it never creates any -- see ``energy``). The welfare gained is the
POTENTIAL DROP ``F(x0) - F(x*)``, not new substance.

Regime lens (consume-by-reference from FRL-1 ``flow_regime.lorenz``, #54): the anneal is
read with the SAME laminar/turbulent lens as the Lorenz flow. A healthy anneal is a
CONTRACTION to a stable fixed point -- its largest Lyapunov exponent (estimated by the same
Benettin variational method as ``lorenz.benettin_lyapunov``, two nearby trajectories advanced
by the SAME map and renormalized) is negative: **laminar**. A manipulated anneal -- an
over-driven or adversarial (control-maximizing) update -- fails to settle; nearby trajectories
separate, the exponent is positive: **turbulent** (the same math as Silent Weapons'
self-destructive oscillation, intent inverted). The turbulence threshold ``CHAOS_LAMBDA`` and
the taxonomy->regime map ``TAXONOMY_TO_FLOW`` are consumed from ``lorenz`` by reference so the
two lenses agree by construction.

Deterministic and stdlib-only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# Consume-by-reference: the FRL-1 turbulence threshold + taxonomy->regime map (#54).
from ..flow_regime.lorenz import CHAOS_LAMBDA, TAXONOMY_TO_FLOW
from .qol import WelfareGroup, total_welfare

# convergence tolerance on the terminal step size (a settled fixed point)
SETTLE_TOL = 1e-6
# monotone-descent slack: F may not rise by more than this between steps
MONOTONE_SLACK = 1e-9


class AnnealError(ValueError):
    """Raised for an inadmissible anneal (bad params, wrong-direction claim) -- REJECTED."""


def free_energy(groups: list[WelfareGroup], allocation: list[float]) -> float:
    """The free-energy potential F(x) = -W(x). The anneal descends this."""
    return -total_welfare(groups, allocation)


def project_to_simplex(x: list[float], energy: float) -> list[float]:
    """Project onto {sum == energy, x_i >= 0}: clip negatives, renormalize to ``energy``.

    Guarantees exact conservation of the total value-energy after every step."""
    clipped = [xi if xi > 0.0 else 0.0 for xi in x]
    s = sum(clipped)
    if s <= 0.0:
        n = len(x)
        return [energy / n] * n
    scale = energy / s
    return [xi * scale for xi in clipped]


def anneal_step(groups: list[WelfareGroup], x: list[float], lr: float,
                energy: float) -> list[float]:
    """One sum-preserving projected-gradient descent step on F(x) = -W(x)."""
    grad = [-g.marginal_welfare(xi) for g, xi in zip(groups, x)]
    mean_g = sum(grad) / len(grad)
    stepped = [xi - lr * (gi - mean_g) for xi, gi in zip(x, grad)]
    return project_to_simplex(stepped, energy)


def _step_size(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))


def benettin_lyapunov_anneal(groups: list[WelfareGroup], x0: list[float], lr: float,
                             energy: float, *, n: int = 400, transient: int = 40,
                             d0: float = 1e-9) -> float:
    """Largest Lyapunov exponent of the anneal map by the Benettin (1980) variational
    method -- the SAME method ``lorenz.benettin_lyapunov`` uses for the Lorenz flow.

    Two nearby allocations are advanced by the SAME anneal step and their separation is
    renormalized to ``d0`` each iteration; the mean log-growth is the exponent. Negative =>
    contraction to a fixed point (laminar); positive => sensitive dependence (turbulent)."""
    x = list(x0)
    for _ in range(transient):
        x = anneal_step(groups, x, lr, energy)
    # perturbed companion along the first coordinate (re-projected to stay feasible)
    xp = project_to_simplex([x[0] + d0] + list(x[1:]), energy)
    total = 0.0
    counted = 0
    for _ in range(n):
        x = anneal_step(groups, x, lr, energy)
        xp = anneal_step(groups, xp, lr, energy)
        dist = _step_size(xp, x)
        if dist <= 0.0:
            continue
        total += math.log(dist / d0)
        counted += 1
        scale = d0 / dist
        xp = [xi + (xpi - xi) * scale for xi, xpi in zip(x, xp)]
    return total / counted if counted else 0.0


@dataclass(frozen=True)
class AnnealResult:
    total_energy: float             # conserved value-energy E (== sum(x) at every step)
    welfare: tuple                  # W(x_k) per step
    free_energy: tuple              # F(x_k) = -W(x_k) per step
    step_sizes: tuple               # ||x_{k+1}-x_k|| per step
    fixed_point: tuple              # terminal allocation x*
    lyapunov: float                 # largest Lyapunov exponent (Benettin)
    regime: str                     # "laminar" | "turbulent"
    settled: bool                   # terminal step below SETTLE_TOL
    monotone_descent: bool          # F never rose (within slack)
    energy_conserved: bool          # sum(x) == E within tolerance at every step

    @property
    def welfare_gain(self) -> float:
        """The potential drop realized: W(x*) - W(x0) (== F(x0) - F(x*))."""
        return self.welfare[-1] - self.welfare[0]

    @property
    def is_laminar(self) -> bool:
        return self.regime == "laminar"


def run_anneal(groups: list[WelfareGroup], x0: list[float], lr: float, steps: int,
               *, energy: float | None = None, conservation_tol: float = 1e-6) -> AnnealResult:
    """Run the welfare anneal and classify its regime with the FRL-1 lens.

    Records the welfare/free-energy trajectory, checks that every step conserves the total
    value-energy, tests monotone descent, and classifies laminar vs turbulent via the
    Benettin exponent against the consumed ``CHAOS_LAMBDA`` threshold."""
    if lr <= 0:
        raise AnnealError(f"REJECTED: non-positive learning rate {lr}")
    if steps < 1:
        raise AnnealError("REJECTED: anneal needs at least one step")
    E = float(sum(x0)) if energy is None else float(energy)
    x = project_to_simplex(list(x0), E)

    welfare = [total_welfare(groups, x)]
    fe = [free_energy(groups, x)]
    steps_taken = []
    conserved = True
    monotone = True
    for _ in range(steps):
        x_next = anneal_step(groups, x, lr, E)
        steps_taken.append(_step_size(x, x_next))
        if abs(sum(x_next) - E) > conservation_tol:
            conserved = False
        w = total_welfare(groups, x_next)
        f = -w
        if f > fe[-1] + MONOTONE_SLACK:
            monotone = False
        welfare.append(w)
        fe.append(f)
        x = x_next

    lam = benettin_lyapunov_anneal(groups, x0, lr, E)
    settled = steps_taken[-1] < SETTLE_TOL
    # FRL-1 lens: turbulent iff the largest Lyapunov exponent exceeds the consumed
    # CHAOS_LAMBDA threshold (a strange/expanding regime), or the flow never settled with
    # monotone descent to a fixed point. Otherwise laminar.
    turbulent = (lam > CHAOS_LAMBDA) or not (settled and monotone)
    regime = "turbulent" if turbulent else "laminar"
    return AnnealResult(
        total_energy=E,
        welfare=tuple(round(w, 10) for w in welfare),
        free_energy=tuple(round(f, 10) for f in fe),
        step_sizes=tuple(steps_taken),
        fixed_point=tuple(x),
        lyapunov=round(lam, 6),
        regime=regime,
        settled=settled,
        monotone_descent=monotone,
        energy_conserved=conserved,
    )


def regime_for_taxonomy(memory_regime: str) -> str:
    """Map a memory-mesh taxonomy label to the expected anneal regime (FRL-1 map, by ref).

    A converging/decaying anneal is laminar; a chaotic one is turbulent -- the SAME
    ``TAXONOMY_TO_FLOW`` crosswalk the Lorenz lens uses, consumed by reference."""
    if memory_regime not in TAXONOMY_TO_FLOW:
        raise AnnealError(f"REJECTED: unknown taxonomy label {memory_regime!r}")
    return TAXONOMY_TO_FLOW[memory_regime]


def assert_descends(result: AnnealResult) -> AnnealResult:
    """REJECT an anneal that increases free-energy (wrong direction).

    The anneal must monotonically LOWER the free-energy potential (raise welfare). A run
    whose F rose is going the wrong way -- refused."""
    if not result.monotone_descent:
        raise AnnealError(
            "REJECTED (wrong-direction): the anneal increased the free-energy potential; "
            "a welfare anneal must monotonically LOWER F (raise the QoL index)."
        )
    return result
