import pytest

from open_ep_framework.validation import validate_json_file
from open_ep_framework.vdt import improvement_fraction, run_vdt

EXAMPLE = "examples/vdt_software_platforms.json"


def test_vdt_profile_fixture_validates():
    assert validate_json_file(EXAMPLE, "schemas/vdt_profile.schema.json")


def test_improvement_fraction_respects_polarity():
    assert abs(improvement_fraction(10.0, "higher_better") - 0.10) < 1e-12
    assert abs(improvement_fraction(2.0, "higher_better") - 0.02) < 1e-12
    # a falling lower_better metric (negative delta) is a positive improvement
    assert abs(improvement_fraction(-0.5, "lower_better") - 0.005) < 1e-12
    with pytest.raises(ValueError):
        improvement_fraction(1.0, "sideways")


def test_vdt_summary_is_deterministic_and_self_consistent():
    summary = run_vdt(EXAMPLE)["summary"]

    assert summary["run_id"] == "vdt-software-platforms-001"
    assert summary["industry"] == "GICS45_SoftwarePlatforms"
    assert summary["driver_count"] == 6
    assert summary["domain_count"] == 6
    assert summary["kpi_count"] == 3
    assert summary["weight_cell_count"] == 36
    # the tensor is a complete value-attribution distribution for the industry
    assert abs(summary["weight_sum"] - 1.0) < 1e-6

    # computed == reported (self-consistency), like the other measurement runtimes
    assert abs(summary["computed_total_value_uplift"] - summary["reported_total_value_uplift"]) < 1e-6
    assert abs(summary["computed_value_uplift_fraction"] - summary["reported_value_uplift_fraction"]) < 1e-12

    # known hand values against the GICS45 tensor + Software KPIs
    assert abs(summary["computed_total_value_uplift"] - 10201612.903225804) < 1e-3
    assert abs(summary["per_driver_uplift"]["RevenueGrowth"] - 9677419.354838708) < 1e-3
    assert abs(summary["projected_enterprise_value"] - 1010201612.9032258) < 1e-3
    assert summary["missing_required_non_goals"] == []

    # the lower_better security KPI contributes POSITIVELY (incidents fell)
    sec = next(k for k in summary["per_kpi_contribution"] if k["kpi"] == "security_incident_rate")
    assert sec["value_contribution"] > 0
