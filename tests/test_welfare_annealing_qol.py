"""Per-tooth tests for the QoL welfare functional (WEA-1)."""
import pytest

from open_ep_framework.welfare_annealing.qol import (
    REQUIRED_DIMENSIONS, QoLDimensionError, WelfareGroup, group_capability,
    groups_from_records, hdi_subindex, qol_index, total_welfare,
)

_G = {"name": "A", "population": 10.0, "life_length": 0.6, "health": 0.7, "education": 0.5}


# --- TOOTH: a missing required dimension is REJECTED ----------------------- #
@pytest.mark.parametrize("dim", REQUIRED_DIMENSIONS)
def test_missing_dimension_rejected(dim):
    bad = {k: v for k, v in _G.items() if k != dim}
    with pytest.raises(QoLDimensionError):
        qol_index([bad])


def test_all_four_dimensions_required():
    assert set(REQUIRED_DIMENSIONS) == {"population", "life_length", "health", "education"}


# --- VERIFIES: geometric-mean aggregation + imbalance penalty -------------- #
def test_capability_is_geometric_mean():
    # gmean(0.6,0.7,0.5) = (0.21)^(1/3)
    assert group_capability(_G) == pytest.approx((0.6 * 0.7 * 0.5) ** (1 / 3))


def test_zero_dimension_collapses_index():
    # a capability the population entirely lacks -> zero contribution (HDI imbalance penalty)
    g = dict(_G, education=0.0)
    assert group_capability(g) == 0.0


def test_qol_index_population_weighted_sum():
    g2 = dict(_G, name="B", population=20.0)
    assert qol_index([_G, g2]) == pytest.approx(
        10.0 * group_capability(_G) + 20.0 * group_capability(g2))


# --- HDI normalization ----------------------------------------------------- #
def test_hdi_subindex_goalposts():
    # UNDP life-expectancy goalposts 20..85; a value of 52.5 -> 0.5
    assert hdi_subindex(52.5, 20.0, 85.0) == pytest.approx(0.5)
    assert hdi_subindex(10.0, 20.0, 85.0) == 0.0     # clamped below
    assert hdi_subindex(200.0, 20.0, 85.0) == 1.0    # clamped above


# --- welfare functional W(x) ---------------------------------------------- #
def test_marginal_welfare_is_decreasing():
    g = WelfareGroup("A", population=10.0, base=0.6, k=1.0)
    assert g.marginal_welfare(0.5) > g.marginal_welfare(5.0)  # diminishing returns


def test_total_welfare_matches_group_sum():
    groups = groups_from_records([_G, dict(_G, name="B", population=20.0)])
    alloc = [3.0, 5.0]
    assert total_welfare(groups, alloc) == pytest.approx(
        sum(g.welfare(x) for g, x in zip(groups, alloc)))
