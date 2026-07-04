import json
import sys

from open_ep_framework.cli import main


def test_associated_surplus_cli_emits_summary_and_audit(tmp_path, monkeypatch, capsys):
    audit_path = tmp_path / "associated_surplus_audit.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "oepf",
            "--mode",
            "associated-surplus",
            "--example",
            "examples/associated_surplus_measurement.json",
            "--audit",
            str(audit_path),
        ],
    )

    main()

    stdout = capsys.readouterr().out
    payload = json.loads(stdout)
    assert payload["summary"]["run_id"] == "associated-surplus-synthetic-001"
    assert payload["summary"]["missing_required_non_goals"] == []
    assert abs(payload["summary"]["computed_net_associated_surplus"] - 0.27493856174080006) < 1e-12

    assert audit_path.exists()
    audit = json.loads(audit_path.read_text())
    assert audit["run_id"] == "associated-surplus-synthetic-001"
    assert audit["scenario"] == "education-community-governance-loop"
    assert audit["outputs"]["summary"]["measurement_boundary_mode"] == "doctrine_measurement_simulation_audit_only"
