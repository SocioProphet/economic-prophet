import copy

import pytest

from open_ep_framework.policy_simulation import load_policy_simulation_profile
from open_ep_framework.policy_simulation_uvmc import (
    PolicySimulationMeasuredEntityError,
    policy_simulation_measured_entity,
    run_policy_simulation_measured_entity,
    validate_policy_simulation_measured_entity_semantics,
)
from open_ep_framework.validation import validate_json_file


def test_policy_simulation_measured_entity_fixture_validates():
    assert validate_json_file(
        "examples/policy_simulation_measured_entity.json",
        "schemas/policy_simulation_measured_entity.schema.json",
    )


def test_policy_simulation_profile_projects_to_uvmc_advisory_entity():
    output = run_policy_simulation_measured_entity("examples/policy_simulation_profile.json")
    entity = output["measured_entity"]

    assert entity["measured_entity_id"] == "policy-simulation-measured:policy-sim-source-intake-001"
    assert entity["advisory_status"] == "advisory_evidence_only"
    assert entity["source_ref"] == "SocioProphet/ai-economist"
    assert entity["measurement_context"]["domain"] == "policy_simulation"
    assert entity["governance_control"]["runtime_dependency"] is False
    assert entity["governance_control"]["release_authority"] == "advisory_only"
    assert entity["governance_control"]["live_policy_automation"] is False
    assert entity["governance_control"]["value_release_authorized"] is False
    assert entity["triparty_measurement"]["release_ratio"] == 0.6
    assert entity["triparty_measurement"]["residual_ratio"] == 0.4
    assert "economic_profit" not in entity


def test_policy_simulation_uvmc_semantic_gate_rejects_runtime_dependency():
    profile = load_policy_simulation_profile("examples/policy_simulation_profile.json")
    entity = policy_simulation_measured_entity(profile)
    entity["governance_control"]["runtime_dependency"] = True
    with pytest.raises(PolicySimulationMeasuredEntityError):
        validate_policy_simulation_measured_entity_semantics(entity)


def test_policy_simulation_uvmc_semantic_gate_rejects_economic_profit_claim():
    profile = load_policy_simulation_profile("examples/policy_simulation_profile.json")
    entity = policy_simulation_measured_entity(profile)
    entity["economic_profit"] = 1.0
    with pytest.raises(PolicySimulationMeasuredEntityError):
        validate_policy_simulation_measured_entity_semantics(entity)


def test_policy_simulation_uvmc_semantic_gate_rejects_residual_mismatch():
    profile = load_policy_simulation_profile("examples/policy_simulation_profile.json")
    entity = copy.deepcopy(policy_simulation_measured_entity(profile))
    entity["triparty_measurement"]["residual"] = 0.1
    with pytest.raises(PolicySimulationMeasuredEntityError):
        validate_policy_simulation_measured_entity_semantics(entity)
