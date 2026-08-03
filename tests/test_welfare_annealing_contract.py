"""End-to-end WEA-1 contract tests over the committed fixtures + receipt spine."""
import json
from pathlib import Path

import pytest

from open_ep_framework.welfare_annealing.contract import (
    CONTRACT, WelfareAnnealingError, emit_receipt, run_record,
)

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "examples" / "welfare_annealing"


def _load(name):
    return json.loads((EX / name).read_text())


def test_all_valid_fixtures_accepted():
    for path in sorted(EX.glob("*.valid.json")):
        audit = run_record(json.loads(path.read_text()))
        assert audit["contract"] == CONTRACT
        assert audit["outputs"]["verdict"] == "verified"


def test_all_invalid_fixtures_rejected():
    for path in sorted(EX.glob("*.invalid.json")):
        with pytest.raises(Exception):
            run_record(json.loads(path.read_text()))


def test_unknown_record_kind_rejected():
    with pytest.raises(WelfareAnnealingError):
        run_record({"record_kind": "not_a_kind"})


# --- receipt spine: estate sha256 convention, deterministic ---------------- #
def test_receipt_spine_hashes_are_deterministic():
    rec = _load("exchange.conserving.valid.json")
    r1 = emit_receipt(rec)
    r2 = emit_receipt(rec)
    for key in ("input_hash", "output_hash", "receipt_hash"):
        assert r1[key] == r2[key]
        assert r1[key].startswith("sha256:")


def test_receipt_changes_when_record_changes():
    a = emit_receipt(_load("exchange.conserving.valid.json"))
    rec = _load("exchange.conserving.valid.json")
    rec["exchange"]["inflows"][0]["amount"] += 1.0  # now non-conserving
    with pytest.raises(Exception):
        emit_receipt(rec)  # a mutated (non-conserving) record cannot receipt
    assert a["receipt_hash"].startswith("sha256:")


def test_anneal_fixture_reports_laminar_and_gain():
    audit = run_record(_load("anneal.laminar_healthy.valid.json"))
    out = audit["outputs"]
    assert out["regime"] == "laminar"
    assert out["monotone_descent"] is True
    assert out["energy_conserved"] is True
    assert out["welfare_gain"] > 0.0
    assert out["free_energy_end"] < out["free_energy_start"]
