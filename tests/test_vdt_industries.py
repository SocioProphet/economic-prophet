"""Every VDT industry profile validates, its tensor is a complete attribution
distribution (36 cells summing to 1.0), and its reported uplift equals what the
engine recomputes — the same self-consistency contract the Software profile holds,
so a new industry can't ship with a hand-miscomputed headline."""
import pytest

from open_ep_framework.validation import validate_json_file
from open_ep_framework.vdt import run_vdt

SCHEMA = "schemas/vdt_profile.schema.json"

INDUSTRY_EXAMPLES = [
    "examples/vdt_software_platforms.json",
    "examples/vdt_banks_financials.json",
    "examples/vdt_energy.json",
    "examples/vdt_real_estate.json",
    "examples/vdt_materials.json",
    "examples/vdt_consumer_staples.json",
]


@pytest.mark.parametrize("example", INDUSTRY_EXAMPLES)
def test_industry_profile_validates(example):
    assert validate_json_file(example, SCHEMA)


@pytest.mark.parametrize("example", INDUSTRY_EXAMPLES)
def test_industry_tensor_is_complete_distribution(example):
    summary = run_vdt(example)["summary"]
    assert summary["weight_cell_count"] == 36  # 6 drivers x 6 domains
    assert abs(summary["weight_sum"] - 1.0) < 1e-6


@pytest.mark.parametrize("example", INDUSTRY_EXAMPLES)
def test_industry_uplift_is_self_consistent(example):
    summary = run_vdt(example)["summary"]
    assert abs(summary["computed_total_value_uplift"] - summary["reported_total_value_uplift"]) < 1e-3
    assert abs(summary["computed_value_uplift_fraction"] - summary["reported_value_uplift_fraction"]) < 1e-9


def test_industries_are_distinct():
    industries = {run_vdt(e)["summary"]["industry"] for e in INDUSTRY_EXAMPLES}
    assert len(industries) == len(INDUSTRY_EXAMPLES)  # no duplicate industry ids
