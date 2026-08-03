import copy
import json

import pytest

from open_ep_framework.crypto.manipulation import (
    ManipulationError,
    evaluate_manipulation,
    gini,
    run_manipulation,
)
from open_ep_framework.validation import validate_json_file

WHALE_WASH = "examples/crypto_manipulation_whale_wash.json"
ATTESTED_CLEAN = "examples/crypto_manipulation_attested_clean.invalid.json"


def _spec():
    with open(WHALE_WASH) as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# schema
# --------------------------------------------------------------------------- #
def test_fixtures_validate_against_schema():
    assert validate_json_file(WHALE_WASH, "schemas/manipulation_signal.schema.json")
    assert validate_json_file(ATTESTED_CLEAN, "schemas/manipulation_signal.schema.json")


# --------------------------------------------------------------------------- #
# VERIFIES
# --------------------------------------------------------------------------- #
def test_whale_wash_raises_signal_with_evidence():
    result = run_manipulation(WHALE_WASH)
    assert result["verdict"] == "manipulated"
    assert result["severity"] >= 0.5
    # Evidence, not a bare verdict.
    indicators = {e["indicator"] for e in result["evidence"]}
    assert "concentration" in indicators
    assert "wash_trade" in indicators
    assert "mev" in indicators
    assert result["indicators"]["concentration"]["flag"] is True
    assert result["indicators"]["wash"]["flag"] is True
    assert result["indicators"]["mev"]["flag"] is True


def test_signal_is_shaped_for_gbrg_governance_plane():
    result = run_manipulation(WHALE_WASH)
    gbrg = result["gbrg"]
    assert gbrg["subject"] == "lowcap-token-synthetic"
    assert gbrg["containment"] == "quarantine_pending_review"
    assert gbrg["evidence_count"] >= 3
    assert "price_discovery" in gbrg["blast_radius"]


def test_adverse_selection_block_consumes_microstructure_contract():
    result = run_manipulation(WHALE_WASH)
    adv = result["indicators"]["adverse_selection"]
    # Glosten-Milgrom spread == 2 * pin * (value_high - value_low) = 2*0.5*20 = 20.
    assert adv["glosten_milgrom_spread"] == pytest.approx(20.0)
    # Kyle's lambda == sigma_v / (2*sigma_u) = 2/2 = 1.0.
    assert adv["kyle_lambda"] == pytest.approx(1.0)
    assert adv["consumes"] == "feat/microstructure-order-flow-contract"


def test_clean_asset_is_not_flagged():
    # A control that never fires is suspect: on a diffuse, honest book it must be CLEAN.
    spec = {
        "subject": "diffuse-honest-token",
        "concentration": {"holders": [1000, 1010, 990, 1005, 995, 1002, 998, 1001]},
        "volume": {"reported_volume": 1000000, "onchain_settled_volume": 990000, "self_trade_volume": 10000},
        "mev": {"mev_extracted": 100, "block_volume": 1000000},
        "adverse_selection": {"pin": 0.05, "value_high": 100.5, "value_low": 99.5, "sigma_v": 0.1, "sigma_u": 5.0},
    }
    result = evaluate_manipulation(spec)
    assert result["verdict"] == "clean"
    assert result["evidence"] == []
    assert result["gbrg"]["containment"] == "none"


def test_receipt_is_deterministic():
    r1 = run_manipulation(WHALE_WASH)
    r2 = run_manipulation(WHALE_WASH)
    assert r1["receipt_hash"] == r2["receipt_hash"]


# --------------------------------------------------------------------------- #
# REJECTS (teeth)
# --------------------------------------------------------------------------- #
def test_attested_clean_contradicted_by_concentration_is_rejected():
    with pytest.raises(ManipulationError, match="attested_clean contradicts"):
        run_manipulation(ATTESTED_CLEAN)


def test_attestation_of_a_genuinely_clean_book_is_allowed():
    # The rejection is precise: it fires only when the attestation is contradicted.
    spec = {
        "subject": "honest-attested",
        "attested_clean": True,
        "concentration": {"holders": [1000, 1010, 990, 1005, 995, 1002]},
        "volume": {"reported_volume": 1000000, "onchain_settled_volume": 1000000, "self_trade_volume": 0},
    }
    result = evaluate_manipulation(spec)
    assert result["verdict"] == "clean"


# --------------------------------------------------------------------------- #
# unit: gini
# --------------------------------------------------------------------------- #
def test_gini_monotone_in_concentration():
    equal = gini([100, 100, 100, 100])
    whale = gini([970, 10, 10, 10])
    assert equal < 0.05
    assert whale > equal
    assert 0.0 <= whale <= 1.0
