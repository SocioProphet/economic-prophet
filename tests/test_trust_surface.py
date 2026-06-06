from pathlib import Path

from open_ep_framework.validation import validate_instance
from open_ep_framework.yaml_lite import parse_yaml_lite


REQUIRED_NON_GOALS = {
    "live_money_movement",
    "external_token_issuance",
    "public_chain_settlement",
    "exchange_trading",
    "redemption_rights",
}


def test_trust_surface_contract_validates():
    trust_surface = parse_yaml_lite(Path("TRUST_SURFACE.yaml").read_text())
    schema = __import__("json").loads(Path("schemas/trust_surface.schema.json").read_text())

    assert validate_instance(trust_surface, schema)
    assert trust_surface["component"] == "economic-prophet"
    assert trust_surface["kind"] == "platform_service"
    assert trust_surface["requires_policy_admission"] is True
    assert REQUIRED_NON_GOALS.issubset(set(trust_surface["non_goals"]))
    assert "associated_surplus_measurement" in trust_surface["service_boundary"]["owns"]
    assert "hidden_reputation_scores" in trust_surface["cannot_write"]
    assert "source_output_hash" in trust_surface["projection_requirements"]["applications_must_preserve"]
