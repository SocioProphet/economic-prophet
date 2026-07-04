import json
import sys

from open_ep_framework.cli import main


def test_vdt_cli_emits_summary_and_audit(tmp_path, monkeypatch, capsys):
    audit_path = tmp_path / "vdt_audit.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "oepf",
            "--mode",
            "vdt",
            "--example",
            "examples/vdt_software_platforms.json",
            "--audit",
            str(audit_path),
        ],
    )

    main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["run_id"] == "vdt-software-platforms-001"
    assert payload["summary"]["kpi_count"] == 3
    assert abs(payload["summary"]["computed_total_value_uplift"] - 10201612.903225804) < 1e-3

    assert audit_path.exists()
    audit = json.loads(audit_path.read_text())
    assert audit["run_id"] == "vdt-software-platforms-001"
    assert audit["scenario"] == "software-platforms-value-driver-tree"
    assert audit["outputs"]["summary"]["projected_enterprise_value"] > 1_000_000_000
