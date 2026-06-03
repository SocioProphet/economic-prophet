import copy
import json
from pathlib import Path

import pytest

from open_ep_framework.cli import main as cli_main
from open_ep_framework.policy_simulation import (
    PolicySimulationProfileError,
    run_policy_simulation_profile,
    validate_policy_simulation_profile_semantics,
)
from open_ep_framework.validation import validate_json_file


def _fixture() -> dict:
    return json.loads(Path("examples/policy_simulation_profile.json").read_text())


def test_policy_simulation_profile_fixture_validates():
    assert validate_json_file(
        "examples/policy_simulation_profile.json",
        "schemas/policy_simulation_profile.schema.json",
    )


def test_policy_simulation_profile_summary_metrics_are_deterministic():
    output = run_policy_simulation_profile("examples/policy_simulation_profile.json")
    summary = output["summary"]

    assert summary["profile_id"] == "policy-sim-source-intake-001"
    assert summary["scenario_id"] == "redistribution-transfer-release-synthetic"
    assert summary["actor_count"] == 2
    assert summary["component_count"] == 2
    assert summary["reward_functional_count"] == 1
    assert summary["triparty_face_count"] == 1
    assert summary["runtime_dependency"] is False
    assert summary["gross_quantity"] == 1.0
    assert summary["admitted_quantity"] == 0.8
    assert summary["released_quantity"] == 0.6
    assert summary["residual_quantity"] == 0.4
    assert abs(summary["admission_ratio"] - 0.8) < 1e-9
    assert abs(summary["release_ratio"] - 0.6) < 1e-9
    assert abs(summary["residual_ratio"] - 0.4) < 1e-9
    assert summary["replay_available"] is True


def test_policy_simulation_cli_writes_audit_pack(tmp_path, monkeypatch):
    audit_path = tmp_path / "policy_simulation_audit.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "oepf",
            "--mode",
            "policy-simulation",
            "--example",
            "examples/policy_simulation_profile.json",
            "--audit",
            str(audit_path),
        ],
    )

    cli_main()

    audit = json.loads(Path(audit_path).read_text())
    assert audit["run_id"] == "policy-sim-source-intake-run-001"
    assert audit["scenario"] == "redistribution-transfer-release-synthetic"
    assert audit["outputs"]["summary"]["runtime_dependency"] is False
    assert audit["outputs"]["summary"]["release_ratio"] == 0.6


def test_policy_simulation_semantic_gate_rejects_runtime_dependency():
    profile = _fixture()
    profile["donor_corpus"]["runtime_dependency"] = True
    with pytest.raises(PolicySimulationProfileError):
        validate_policy_simulation_profile_semantics(profile)


def test_policy_simulation_semantic_gate_rejects_release_authority():
    profile = _fixture()
    profile["reward_functionals"][0]["release_authority"] = "automatic_release"
    with pytest.raises(PolicySimulationProfileError):
        validate_policy_simulation_profile_semantics(profile)


def test_policy_simulation_semantic_gate_rejects_triparty_ordering():
    profile = _fixture()
    profile["triparty_faces"][0]["lambda_release"] = 0.9
    with pytest.raises(PolicySimulationProfileError):
        validate_policy_simulation_profile_semantics(profile)


def test_policy_simulation_semantic_gate_rejects_residual_mismatch():
    profile = copy.deepcopy(_fixture())
    profile["triparty_faces"][0]["residual"] = 0.1
    with pytest.raises(PolicySimulationProfileError):
        validate_policy_simulation_profile_semantics(profile)
