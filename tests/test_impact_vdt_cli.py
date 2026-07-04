import json
import sys

from open_ep_framework.cli import main


def test_impact_vdt_cli_emits_summary_and_audit(tmp_path, monkeypatch, capsys):
    audit_path = tmp_path / "impact_audit.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "oepf",
            "--mode",
            "vdt-impact",
            "--example",
            "examples/vdt_impact_energy_equity.json",
            "--audit",
            str(audit_path),
        ],
    )

    main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["run_id"] == "vdt-impact-energy-equity-001"
    assert abs(payload["summary"]["computed_total_people_mid"] - 13742.5) < 1e-6

    assert audit_path.exists()
    audit = json.loads(audit_path.read_text())
    assert audit["run_id"] == "vdt-impact-energy-equity-001"
    assert audit["scenario"] == "energy-equity-impact-value-driver-tree"
    assert audit["outputs"]["summary"]["cost_effectiveness_ranking"][0] == "Footfall tiles for device autonomy"
