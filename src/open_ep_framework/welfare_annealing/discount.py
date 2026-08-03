"""Discounting: Fisher real rate, Fisher-ideal index, MV=PQ, and the social discount rate
as the MASTER parameter (Ramsey; Stern vs Nordhaus) with a sensitivity sweep.

Three price/quantity mechanics plus the master welfare-discounting parameter:

* **Fisher equation** (1 + i) = (1 + r)(1 + pi): a nominal growth/return claim must be
  deflated to a REAL one. The exact real rate is consumed BY REFERENCE from the estate's
  ``inflation.real_rate`` (economic-prophet ``inflation``). A growth claim that is not
  Fisher-real-adjusted (reports a real figure that does not equal the deflated nominal one)
  is REJECTED.
* **Fisher-ideal index** = geometric mean of the Laspeyres and Paasche price indices -- the
  symmetric "ideal" index used to deflate quantities consistently.
* **Quantity theory / exchange velocity** MV = PQ: the identity linking money stock and
  velocity to the price level and real output (the exchange-flow accounting identity).
* **Social discount rate (Ramsey rule)** r = delta + eta * g, where ``delta`` is the pure
  rate of time preference, ``eta`` the elasticity of marginal utility of consumption and
  ``g`` per-capita consumption growth. This is the MASTER parameter of the whole welfare
  functional: it sets how much a future unit of QoL is worth today. The Stern Review uses a
  very LOW delta (~0.001) -> a low r -> future QoL weighted heavily; Nordhaus (DICE) uses a
  HIGHER delta (~0.015) -> a higher r -> future QoL discounted more. A sensitivity sweep
  over delta must RECONCILE: the present value of a fixed future QoL gain is monotonically
  DECREASING in r, so the Stern (low-r) weight strictly exceeds the Nordhaus (high-r) weight.

Deterministic and stdlib-only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# Consume-by-reference: the exact Fisher real rate (economic-prophet ``inflation``).
from ..inflation import real_rate

# Canonical calibrations of the Ramsey parameters from the climate-economics debate.
STERN = {"name": "stern", "delta": 0.001, "eta": 1.0}      # Stern Review (2007)
NORDHAUS = {"name": "nordhaus", "delta": 0.015, "eta": 1.45}  # Nordhaus / DICE


class DiscountError(ValueError):
    """Raised for a discounting violation (nominal-not-real, broken identity) -- REJECTED."""


# --------------------------------------------------------------------------- #
# Fisher real rate + the "growth must be Fisher-real-adjusted" tooth.
# --------------------------------------------------------------------------- #
def fisher_real_rate(nominal: float, inflation: float) -> float:
    """Exact Fisher real rate (1+nominal)/(1+inflation)-1, consumed from ``inflation``."""
    return real_rate(nominal, inflation)


def fisher_nominal_rate(real: float, inflation: float) -> float:
    """Invert the Fisher equation: (1+i) = (1+r)(1+pi)."""
    return (1.0 + real) * (1.0 + inflation) - 1.0


def assert_real_adjusted(claim: dict, tol: float = 1e-6) -> dict:
    """REJECT a growth claim that is not Fisher-real-adjusted.

    ``claim`` carries ``nominal_growth``, ``inflation`` and a ``real_growth``. The real
    figure must equal the exact Fisher deflation of the nominal one; a "real growth" that
    is actually the undeflated nominal number (inflation booked as real gain) is refused."""
    if "nominal_growth" not in claim or "inflation" not in claim:
        raise DiscountError("REJECTED: growth claim missing nominal_growth/inflation")
    expected = fisher_real_rate(float(claim["nominal_growth"]), float(claim["inflation"]))
    if "real_growth" not in claim:
        raise DiscountError(
            "REJECTED: growth claim not Fisher-real-adjusted (no real_growth reported); "
            f"expected real={expected:.6f}"
        )
    reported = float(claim["real_growth"])
    if abs(reported - expected) > tol:
        raise DiscountError(
            "REJECTED: growth claim not Fisher-real-adjusted -- reported real_growth "
            f"{reported} != exact Fisher real {expected:.6f} "
            f"(nominal={claim['nominal_growth']}, inflation={claim['inflation']})"
        )
    return {"nominal_growth": float(claim["nominal_growth"]),
            "inflation": float(claim["inflation"]),
            "real_growth": expected, "fisher_real_adjusted": True}


# --------------------------------------------------------------------------- #
# Fisher-ideal price index + MV = PQ exchange identity.
# --------------------------------------------------------------------------- #
def laspeyres_index(p0, q0, p1) -> float:
    """Base-weighted price index sum(p1*q0)/sum(p0*q0)."""
    num = sum(a * b for a, b in zip(p1, q0))
    den = sum(a * b for a, b in zip(p0, q0))
    if den == 0:
        raise DiscountError("REJECTED: Laspeyres denominator is zero")
    return num / den


def paasche_index(p0, q1, p1) -> float:
    """Current-weighted price index sum(p1*q1)/sum(p0*q1)."""
    num = sum(a * b for a, b in zip(p1, q1))
    den = sum(a * b for a, b in zip(p0, q1))
    if den == 0:
        raise DiscountError("REJECTED: Paasche denominator is zero")
    return num / den


def fisher_ideal_index(p0, q0, p1, q1) -> float:
    """Fisher-ideal price index = geometric mean of Laspeyres and Paasche."""
    lasp = laspeyres_index(p0, q0, p1)
    paa = paasche_index(p0, q1, p1)
    return math.sqrt(lasp * paa)


def quantity_theory_residual(m: float, v: float, p: float, q: float) -> float:
    """MV - PQ. Zero iff the exchange identity holds."""
    return m * v - p * q


def assert_mv_pq(m: float, v: float, p: float, q: float, tol: float = 1e-6) -> dict:
    """VERIFY the MV = PQ exchange-velocity identity; REJECT a broken one."""
    resid = quantity_theory_residual(m, v, p, q)
    if abs(resid) > tol:
        raise DiscountError(
            f"REJECTED: MV=PQ identity broken (MV={m * v}, PQ={p * q}, residual={resid})"
        )
    return {"MV": m * v, "PQ": p * q, "residual": resid, "holds": True}


# --------------------------------------------------------------------------- #
# Social discount rate (Ramsey) + Stern-vs-Nordhaus sensitivity sweep.
# --------------------------------------------------------------------------- #
def ramsey_rate(delta: float, eta: float, g: float) -> float:
    """Ramsey social discount rate r = delta + eta * g."""
    return delta + eta * g


def present_value(future_qol: float, rate: float, horizon: float) -> float:
    """Present value of a future QoL gain: future_qol / (1 + rate)^horizon."""
    return future_qol / (1.0 + rate) ** horizon


@dataclass(frozen=True)
class DiscountScenario:
    name: str
    delta: float
    eta: float
    rate: float
    present_value: float


def discount_sensitivity(future_qol: float, horizon: float, g: float,
                         scenarios: list[dict]) -> list[DiscountScenario]:
    """Sweep the social discount rate over calibrations and value a fixed future QoL gain.

    Returns one ``DiscountScenario`` per calibration (its Ramsey rate and the present value
    of the future QoL). The MASTER-parameter sensitivity: a LOWER delta (Stern) yields a
    lower rate and a HIGHER present value on future QoL than a higher delta (Nordhaus)."""
    out = []
    for sc in scenarios:
        r = ramsey_rate(float(sc["delta"]), float(sc["eta"]), g)
        pv = present_value(future_qol, r, horizon)
        out.append(DiscountScenario(sc.get("name", "scenario"), float(sc["delta"]),
                                    float(sc["eta"]), r, pv))
    return out


def assert_sensitivity_reconciles(scenarios: list[DiscountScenario]) -> dict:
    """VERIFY the sweep reconciles: present value is monotonically DECREASING in the rate.

    Sorting the scenarios by discount rate, the present value of the future QoL gain must be
    non-increasing (a higher social discount rate weights future QoL LESS). In particular a
    low-rate Stern calibration weights the future MORE than a high-rate Nordhaus one. A sweep
    that violates this monotonicity is REJECTED (the discounting is internally inconsistent)."""
    ordered = sorted(scenarios, key=lambda s: s.rate)
    for lo, hi in zip(ordered, ordered[1:]):
        if hi.present_value > lo.present_value + 1e-12:
            raise DiscountError(
                "REJECTED: discount sensitivity does not reconcile -- higher rate "
                f"{hi.rate:.4f} gives HIGHER present value {hi.present_value:.6f} than "
                f"lower rate {lo.rate:.4f} ({lo.present_value:.6f}); PV must fall as r rises"
            )
    lowest, highest = ordered[0], ordered[-1]
    return {
        "monotone_decreasing_in_rate": True,
        "lowest_rate": {"name": lowest.name, "rate": lowest.rate,
                        "present_value": lowest.present_value},
        "highest_rate": {"name": highest.name, "rate": highest.rate,
                         "present_value": highest.present_value},
        "future_weighted_more_by_low_rate": lowest.present_value >= highest.present_value,
    }
