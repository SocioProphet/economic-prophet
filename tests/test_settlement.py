import json
from pathlib import Path

import pytest

from open_ep_framework.settlement import (
    SettlementError,
    check_conservation,
    run_settlement,
    settle,
)

ROOT = Path(__file__).resolve().parents[1]
BALANCED = str(ROOT / "examples" / "conservation_settlement_balanced.json")
NONCONSERVING = str(ROOT / "examples" / "conservation_settlement_nonconserving.invalid.json")


def test_schema_is_parseable_and_strict():
    schema = json.loads((ROOT / "schemas" / "conservation_settlement.schema.json").read_text())
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    for field in ["settlement_id", "conserved_quantity", "tolerance", "inflows", "outflows"]:
        assert field in schema["required"]


# --- Teeth, direction 1: a conserving settlement is ACCEPTED ---

def test_balanced_settlement_is_accepted():
    receipt = run_settlement(BALANCED)
    assert receipt["settlement_status"] == "settled"
    assert receipt["conservation"]["conserved"] is True
    assert receipt["conservation"]["sum_in"] == pytest.approx(1250000.0)
    assert receipt["conservation"]["sum_out"] == pytest.approx(1250000.0)
    assert abs(receipt["conservation"]["residual"]) <= receipt["conservation"]["tolerance"]


def test_settled_receipt_carries_sha256_spine():
    receipt = run_settlement(BALANCED)
    for key in ("input_hash", "output_hash", "receipt_hash"):
        assert receipt[key].startswith("sha256:")
        assert len(receipt[key]) == len("sha256:") + 64


def test_settlement_receipt_is_deterministic():
    assert run_settlement(BALANCED)["receipt_hash"] == run_settlement(BALANCED)["receipt_hash"]


# --- Teeth, direction 2: a non-conserving settlement is REJECTED ---

def test_nonconserving_settlement_is_rejected():
    with pytest.raises(SettlementError):
        run_settlement(NONCONSERVING)


def test_check_conservation_reports_residual_without_raising():
    data = json.loads(Path(NONCONSERVING).read_text())
    ledger = check_conservation(data)
    assert ledger["conserved"] is False
    assert ledger["residual"] == pytest.approx(-75000.0)


# --- Tolerance boundary ---

def test_within_tolerance_conserves_at_boundary():
    data = json.loads(Path(BALANCED).read_text())
    data["tolerance"] = 10.0
    data["outflows"][0]["amount"] += 10.0  # residual = -10, |residual| == tolerance
    receipt = settle(data)
    assert receipt["conservation"]["conserved"] is True


def test_just_over_tolerance_is_rejected():
    data = json.loads(Path(BALANCED).read_text())
    data["tolerance"] = 10.0
    data["outflows"][0]["amount"] += 10.01  # residual = -10.01, over tolerance
    with pytest.raises(SettlementError):
        settle(data)
