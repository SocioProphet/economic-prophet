"""Global quality-of-life welfare functional (the objective the anneal descends toward).

The Welfare-Annealing contract's objective is a HDI-generalized **global QoL index** --
the constructive inverse of "Silent Weapons"' elite-control objective over the SAME
conserved value-energy. Where the control objective maximizes an extraction/dominance
functional, this one maximizes population welfare:

    QoL_index(groups) = sum_i  population_i * gmean(life_length_i, health_i, education_i)

The four dimensions -- **population, life-length, health, education** -- are the required
axes (UNDP Human Development Index generalized: HDI is the geometric mean of a
life-expectancy index, an education index and an income index; we keep life/health/
education as the capability triad and weight each group by its population). The geometric
mean is deliberate: it is HDI's own aggregator and it PENALIZES imbalance (a group with
zero education contributes zero, so you cannot buy a high index by maxing one axis).

TOOTH: a QoL record missing ANY required dimension is REJECTED (``QoLDimensionError``).
An index that silently drops "health" or "education" is not a welfare measure -- it is a
different, unstated objective, and the contract fails closed rather than score it.

Welfare as a function of ALLOCATION (the anneal state):
    W(x) = sum_i  population_i * base_i * capability_i(x_i)
where ``base_i = gmean(life, health, education)`` is the group's structural capability and
``capability_i(x_i) = x_i / (x_i + k_i)`` is an increasing, strictly CONCAVE saturating map
of the value-energy allocated to group i (diminishing returns to resource). Concavity is
the load-bearing property: the marginal welfare ``dW/dx_i`` is strictly decreasing, so the
welfare-maximizing allocation under a FIXED total energy equalizes marginal welfare across
groups -- and the gains realized in getting there are a POTENTIAL DROP, not new substance
(the total energy ``sum_i x_i`` never changes; see ``anneal`` and ``energy``).

Deterministic and stdlib-only.
"""
from __future__ import annotations

from dataclasses import dataclass

# The four required QoL dimensions (population x life-length x health x education).
REQUIRED_DIMENSIONS = ("population", "life_length", "health", "education")

# The capability triad aggregated by the geometric mean (HDI-generalized).
CAPABILITY_DIMENSIONS = ("life_length", "health", "education")


class QoLDimensionError(ValueError):
    """Raised when a QoL record omits a required welfare dimension (REJECTED)."""


def _gmean(values) -> float:
    """Geometric mean (HDI aggregator). Zero on any non-positive component (imbalance
    penalty): a capability the population entirely lacks collapses the index."""
    prod = 1.0
    n = 0
    for v in values:
        if v <= 0.0:
            return 0.0
        prod *= float(v)
        n += 1
    if n == 0:
        return 0.0
    return prod ** (1.0 / n)


def require_dimensions(group: dict, where: str = "group") -> None:
    """Enforce the required-dimension tooth on a single group record."""
    for dim in REQUIRED_DIMENSIONS:
        if dim not in group:
            raise QoLDimensionError(
                f"REJECTED: {where} is missing required QoL dimension {dim!r}; "
                f"a welfare index must carry all of {REQUIRED_DIMENSIONS}"
            )


def group_capability(group: dict) -> float:
    """Structural per-capita capability = gmean(life_length, health, education).

    Each capability sub-index is expected on the HDI [0, 1] scale. Use ``hdi_subindex``
    to normalize a raw indicator (e.g. life expectancy in years) onto that scale."""
    return _gmean(group[d] for d in CAPABILITY_DIMENSIONS)


def group_qol_contribution(group: dict) -> float:
    """Population-weighted QoL contribution of one group (the term summed in the index)."""
    require_dimensions(group)
    return float(group["population"]) * group_capability(group)


def qol_index(groups: list[dict]) -> float:
    """Global QoL index = sum of population-weighted geometric-mean capabilities.

    REJECTS a group missing any of population / life-length / health / education."""
    return sum(group_qol_contribution(g) for g in groups)


def hdi_subindex(value: float, floor: float, ceiling: float) -> float:
    """HDI normalization of a raw indicator onto [0, 1]: (value - floor)/(ceiling - floor),
    clamped. E.g. life expectancy uses floor=20, ceiling=85 (UNDP goalposts)."""
    if ceiling <= floor:
        raise QoLDimensionError("HDI subindex ceiling must exceed floor")
    return max(0.0, min(1.0, (float(value) - floor) / (ceiling - floor)))


# --------------------------------------------------------------------------- #
# Welfare as a function of the allocation (the anneal objective W(x)).
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class WelfareGroup:
    """A population group in the allocation problem.

    ``base`` is the structural capability gmean(life, health, education) in [0, 1];
    ``k`` is the half-saturation constant of the concave capability map (the allocation
    at which the capability multiplier reaches 1/2). Larger population and larger base
    make a unit of value-energy more welfare-productive at the margin."""
    name: str
    population: float
    base: float
    k: float

    def capability(self, x: float) -> float:
        """Saturating, strictly concave capability multiplier c(x) = x/(x+k) in [0,1)."""
        return x / (x + self.k)

    def welfare(self, x: float) -> float:
        return self.population * self.base * self.capability(x)

    def marginal_welfare(self, x: float) -> float:
        """dW_i/dx_i = population * base * k / (x + k)^2 -- strictly decreasing in x
        (diminishing returns), which is what makes the welfare-max allocation unique."""
        return self.population * self.base * self.k / (x + self.k) ** 2


def groups_from_records(records: list[dict]) -> list[WelfareGroup]:
    """Build allocation groups from QoL records, enforcing the dimension tooth."""
    out = []
    for rec in records:
        require_dimensions(rec)
        out.append(
            WelfareGroup(
                name=rec.get("name", "group"),
                population=float(rec["population"]),
                base=group_capability(rec),
                k=float(rec.get("half_saturation", 1.0)),
            )
        )
    return out


def total_welfare(groups: list[WelfareGroup], allocation: list[float]) -> float:
    """W(x) = sum_i population_i * base_i * capability_i(x_i)."""
    return sum(g.welfare(x) for g, x in zip(groups, allocation))
