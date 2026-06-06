from open_ep_framework.associated_surplus import run_associated_surplus
from open_ep_framework.validation import validate_json_file


def test_associated_surplus_measurement_fixture_validates():
    assert validate_json_file(
        "examples/associated_surplus_measurement.json",
        "schemas/associated_surplus.schema.json",
    )


def test_associated_surplus_summary_metrics_are_deterministic():
    output = run_associated_surplus("examples/associated_surplus_measurement.json")
    summary = output["summary"]

    assert summary["run_id"] == "associated-surplus-synthetic-001"
    assert summary["scenario"] == "education-community-governance-loop"
    assert summary["sphere_count"] == 5
    assert summary["community_count"] == 1
    assert summary["knowledge_ref_count"] == 2
    assert summary["governance_ref_count"] == 2
    assert summary["automation_ref_count"] == 1
    assert summary["evidence_ref_count"] == 3
    assert abs(summary["computed_knowledge_quality"] - 0.684) < 1e-12
    assert abs(summary["computed_knowledge_quality"] - summary["reported_knowledge_quality"]) < 1e-12
    assert abs(summary["component_knowledge_quality"] - summary["reported_knowledge_quality"]) < 1e-12
    assert abs(summary["computed_gross_associated_surplus"] - summary["reported_gross_associated_surplus"]) < 1e-12
    assert abs(summary["computed_net_associated_surplus"] - summary["reported_net_associated_surplus"]) < 1e-12
    assert abs(summary["total_deductions"] - 0.32) < 1e-12
    assert abs(summary["release_ratio"] - 0.74) < 1e-12
    assert abs(summary["admission_ratio"] - 0.82) < 1e-12
    assert abs(summary["residual_quantity"] - 0.26) < 1e-12
    assert summary["triparty_state"] == "Released"
    assert summary["measurement_boundary_mode"] == "doctrine_measurement_simulation_audit_only"
    assert summary["missing_required_non_goals"] == []
