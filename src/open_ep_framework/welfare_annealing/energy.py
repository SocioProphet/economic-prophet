"""Value-energy conservation in exchange + the carrying-capacity / renewable source term.

Two physics facts of this framework, both consumed BY REFERENCE from existing estate
contracts (no fork):

1. **Exchange conserves value-energy.** A pure exchange creates no value-energy; it only
   re-attributes the SAME conserved substance across parties. This is exactly the IC-1
   conservation-settlement law (``settlement.check_conservation``): the sum of what leaves
   equals the sum of what arrives, within tolerance. We reuse that checker verbatim -- an
   exchange that reports a net creation of value-energy is a conservation VIOLATION and is
   REJECTED. The gains-from-trade an exchange delivers are therefore NOT new substance;
   they are a drop in the free-energy potential of the SAME conserved energy (a better
   allocation of it), which is what the ``anneal`` realizes.

2. **Only production is a source; and only the RENEWABLE increment is sustainable.**
   Exchange is a conservative FLOW (sum-preserving). The only legitimate way to raise total
   value-energy is PRODUCTION -- a Solow-style source term where labor mixes with materials
   (Lockean labor-mixing; the Jacob's-ladder value-genesis rung). But the materials sit on
   the ALC-1 asset ladder, split by renewability:
       * ``regenerating_flow``  (renewable) -> ``mean_reverting_ou``     -> SUSTAINABLE
       * ``depleting_stock``    (non-renewable) -> ``monotone_absorbing`` -> DRAWDOWN
   We consume the ALC-1 ``RENEWABILITY_REGIME`` crosswalk by reference. The sustainable
   growth of the period is ONLY the renewable increment (harvest at or below the
   regeneration rate). "Growth" funded by drawing down non-renewable stock is FALSE growth
   -- the constructive analog of Silent Weapons' "paper inductance" (an inductance with no
   real magnetic field): a number that rises on the ledger while the real natural-capital
   base falls. A path that books non-renewable drawdown as sustainable is FLAGGED.

Deterministic and stdlib-only.
"""
from __future__ import annotations

from dataclasses import dataclass

# Consume-by-reference: the IC-1 conservation-settlement checker (economic-prophet #39).
from ..settlement import check_conservation
# Consume-by-reference: the ALC-1 renewability <-> process-regime crosswalk (#52).
from ..asset_ladder import RENEWABILITY_REGIME

# The renewability labels that back real value-energy (from the ALC-1 ladder).
RENEWABLE = "regenerating_flow"
NON_RENEWABLE = "depleting_stock"


class ValueEnergyError(ValueError):
    """Raised when the value-energy accounting violates conservation or false-growth teeth."""


# --------------------------------------------------------------------------- #
# 1. Exchange conservation (reuse of the IC-1 settlement law).
# --------------------------------------------------------------------------- #
def exchange_conserves(exchange: dict) -> dict:
    """Check that a pure exchange conserves total value-energy (IC-1 law, by reference).

    ``exchange`` carries ``inflows``/``outflows`` legs (each with ``amount``), a
    ``conserved_quantity`` and a ``tolerance`` -- the IC-1 settlement shape. Returns the
    conservation ledger (``sum_in``, ``sum_out``, ``residual``, ``conserved``). Does not
    raise; use ``assert_exchange_conserves`` for the failing tooth."""
    settlement = {
        "conserved_quantity": exchange.get("conserved_quantity", "value_energy"),
        "inflows": exchange["inflows"],
        "outflows": exchange["outflows"],
        "tolerance": exchange.get("tolerance", 1e-9),
    }
    return check_conservation(settlement)


def assert_exchange_conserves(exchange: dict) -> dict:
    """VERIFIES pure exchange conserves value-energy; REJECTS a net creation/destruction.

    A model that reports value CREATED in pure exchange (sum_in != sum_out beyond
    tolerance) is a conservation violation -- the Silent-Weapons-style "value from
    nothing" move -- and is refused here."""
    ledger = exchange_conserves(exchange)
    if not ledger["conserved"]:
        raise ValueEnergyError(
            "REJECTED: pure exchange does not conserve value-energy "
            f"(sum_in={ledger['sum_in']} sum_out={ledger['sum_out']} "
            f"residual={ledger['residual']} > tolerance {ledger['tolerance']}). "
            "Exchange re-attributes conserved energy; it cannot create it."
        )
    return ledger


# --------------------------------------------------------------------------- #
# 2. Carrying-capacity discount + renewable source term (reuse of the ALC-1 ladder).
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Stock:
    """A real-asset stock backing value-energy, tagged by ALC-1 renewability.

    ``regeneration_rate`` is meaningful only for a ``regenerating_flow`` stock: the
    per-period increment the flow can yield without depleting (the sustainable-yield cap).
    """
    renewability: str
    level: float
    regeneration_rate: float = 0.0

    def __post_init__(self):
        if self.renewability not in RENEWABILITY_REGIME:
            raise ValueEnergyError(
                f"REJECTED: unknown renewability {self.renewability!r}; "
                f"must be one of the ALC-1 ladder labels {tuple(RENEWABILITY_REGIME)}"
            )

    @property
    def process_regime(self) -> str:
        """The ALC-1 process regime this renewability maps to (consumed by reference)."""
        return RENEWABILITY_REGIME[self.renewability]

    @property
    def is_renewable(self) -> bool:
        return self.renewability == RENEWABLE


def sustainable_yield(stock: Stock) -> float:
    """The sustainable per-period source from a stock.

    Renewable (``regenerating_flow`` -> ``mean_reverting_ou``): harvest up to the
    regeneration rate is sustainable. Non-renewable (``depleting_stock`` ->
    ``monotone_absorbing``): ZERO sustainable yield -- any draw is a drawdown toward the
    absorbing barrier."""
    return stock.regeneration_rate if stock.is_renewable else 0.0


def production_source(labor: float, materials: float, *, productivity: float = 1.0,
                      labor_share: float = 0.5) -> float:
    """Solow / Cobb-Douglas production source term with Lockean labor-mixing.

    ``source = A * labor^alpha * materials^(1-alpha)`` -- value GENESIS (a source), as
    opposed to exchange (a conservative flow). ``materials`` should be drawn from a
    renewable flow's sustainable yield for the source to be sustainable."""
    if labor < 0 or materials < 0:
        raise ValueEnergyError("REJECTED: negative labor/materials in production source")
    if not (0.0 < labor_share < 1.0):
        raise ValueEnergyError("REJECTED: labor_share must be in (0,1)")
    if labor == 0.0 or materials == 0.0:
        return 0.0
    return productivity * (labor ** labor_share) * (materials ** (1.0 - labor_share))


def classify_growth(period: dict) -> dict:
    """Split a period's growth into sustainable (renewable) vs false (drawdown).

    ``period`` carries ``renewable_delta`` (the sustainable production increment) and
    ``nonrenewable_drawdown`` (value-energy booked by liquidating depleting stock). The
    only sustainable growth is the renewable delta; any positive drawdown makes the
    reported growth partly FALSE."""
    renewable_delta = float(period.get("renewable_delta", 0.0))
    drawdown = float(period.get("nonrenewable_drawdown", 0.0))
    if drawdown < 0:
        raise ValueEnergyError("REJECTED: nonrenewable_drawdown cannot be negative")
    reported_growth = renewable_delta + drawdown
    return {
        "renewable_delta": renewable_delta,
        "nonrenewable_drawdown": drawdown,
        "reported_growth": reported_growth,
        "sustainable_growth": renewable_delta,
        "false_growth": drawdown,
        "is_sustainable": drawdown <= 0.0,
    }


def assert_sustainable(period: dict) -> dict:
    """FLAG false growth: a path claiming sustainability while funded by non-renewable
    drawdown is REJECTED (the paper-inductance analog).

    If the record asserts ``claim_sustainable: true`` but ``nonrenewable_drawdown > 0``,
    the claim is false and refused."""
    report = classify_growth(period)
    claim = bool(period.get("claim_sustainable", False))
    if claim and not report["is_sustainable"]:
        raise ValueEnergyError(
            "REJECTED (false-growth flag): growth claimed sustainable but "
            f"{report['false_growth']} of {report['reported_growth']} is funded by "
            "non-renewable drawdown (depleting_stock -> monotone_absorbing). Only the "
            "renewable increment is sustainable growth."
        )
    report["claim_sustainable"] = claim
    return report
