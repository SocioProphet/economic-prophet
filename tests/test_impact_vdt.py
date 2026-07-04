from open_ep_framework.impact_vdt import intervention_people, run_impact_vdt
from open_ep_framework.validation import validate_json_file

EXAMPLE = "examples/vdt_impact_energy_equity.json"


def test_impact_vdt_fixture_validates():
    assert validate_json_file(EXAMPLE, "schemas/impact_vdt.schema.json")


def test_intervention_people_is_linear_in_budget():
    iv = {"allocation_usd": 2_000_000, "people_per_million_low": 900, "people_per_million_high": 1600}
    p = intervention_people(iv)
    assert abs(p["low"] - 1800.0) < 1e-9   # 2 * 900
    assert abs(p["high"] - 3200.0) < 1e-9  # 2 * 1600
    assert abs(p["mid"] - 2500.0) < 1e-9   # 2 * 1250


def test_impact_summary_is_deterministic_and_self_consistent():
    summary = run_impact_vdt(EXAMPLE)["summary"]

    assert summary["run_id"] == "vdt-impact-energy-equity-001"
    assert summary["intervention_count"] == 8
    assert summary["driver_count"] == 4
    assert abs(summary["budget_usd"] - 10_000_000.0) < 1e-6
    assert abs(summary["allocated_usd"] - 10_000_000.0) < 1e-6
    assert abs(summary["unallocated_usd"]) < 1e-6

    assert abs(summary["computed_total_people_mid"] - 13742.5) < 1e-6
    assert abs(summary["computed_total_people_mid"] - summary["reported_total_people_mid"]) < 1e-9
    assert abs(summary["computed_total_equity_adjusted_people"] - 5835.25) < 1e-6
    assert abs(summary["computed_total_equity_adjusted_people"] - summary["reported_total_equity_adjusted_people"]) < 1e-9
    assert abs(summary["blended_cost_per_person_usd"] - (10_000_000.0 / 13742.5)) < 1e-6

    # Footfall tiles has the highest people-per-$1M yield → tops the ranking.
    assert summary["cost_effectiveness_ranking"][0] == "Footfall tiles for device autonomy"
    assert abs(summary["per_driver_people_mid"]["Locality & Resilience"] - 6475.0) < 1e-6
    assert summary["missing_required_non_goals"] == []
