import copy
import json

import pytest

from open_ep_framework.crypto.behavioral_regime import (
    BehavioralRegimeError,
    evaluate_behavioral_regime,
    probability_weight,
    prospect_value,
    run_behavioral_regime,
)
from open_ep_framework.validation import validate_json_file

GREED = "examples/crypto_behavioral_regime_greed.json"
BADROWS = "examples/crypto_behavioral_regime_badrows.invalid.json"


def _spec():
    with open(GREED) as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# schema
# --------------------------------------------------------------------------- #
def test_fixtures_validate_against_schema():
    assert validate_json_file(GREED, "schemas/behavioral_regime.schema.json")
    assert validate_json_file(BADROWS, "schemas/behavioral_regime.schema.json")


# --------------------------------------------------------------------------- #
# VERIFIES
# --------------------------------------------------------------------------- #
def test_seeded_greed_series_classifies_higher_mean_and_vol():
    result = run_behavioral_regime(GREED)
    stats = result["regime_stats"]
    # The greed regime is euphoria: higher mean AND higher volatility.
    assert stats["n_greed"] > 0 and stats["n_fear"] > 0
    assert stats["greed_mean"] > stats["fear_mean"]
    assert stats["greed_vol"] > stats["fear_vol"]
    assert stats["greed_has_higher_mean"] is True
    assert stats["greed_has_higher_vol"] is True
    assert result["verdict"] == "verified"


def test_prospect_theory_distortion_reported():
    result = run_behavioral_regime(GREED)
    pt = result["prospect_theory"]
    assert pt["lambda"] > 1.0
    assert pt["loss_aversion_ratio"] > 1.0  # a unit loss hurts more than a unit gain
    assert pt["monotone_weighting"] is True
    # Probability weighting overweights small probabilities, underweights large ones.
    assert pt["w_at_0_1"] > 0.1
    assert pt["w_at_0_9"] < 0.9


def test_arrival_regime_binds_memory_characterizer_taxonomy():
    result = run_behavioral_regime(GREED)
    # Reflexive/self-exciting == the Hawkes arrival regime of the memory-mesh taxonomy.
    assert result["arrival_regime"] == "hawkes_self_exciting"
    assert result["memory_regime_ref"].startswith("memory-mesh:")


def test_receipt_is_deterministic():
    r1 = run_behavioral_regime(GREED)
    r2 = run_behavioral_regime(GREED)
    assert r1["receipt_hash"] == r2["receipt_hash"]


# --------------------------------------------------------------------------- #
# REJECTS (teeth)
# --------------------------------------------------------------------------- #
def test_nonstochastic_transition_matrix_is_rejected():
    with pytest.raises(BehavioralRegimeError, match="sums to|row-stochastic"):
        run_behavioral_regime(BADROWS)


def test_loss_aversion_lambda_must_exceed_one():
    spec = _spec()
    spec["prospect_theory"]["lambda"] = 0.9
    with pytest.raises(BehavioralRegimeError, match="loss aversion"):
        evaluate_behavioral_regime(spec)

    spec2 = _spec()
    spec2["prospect_theory"]["lambda"] = 1.0
    with pytest.raises(BehavioralRegimeError, match="loss aversion"):
        evaluate_behavioral_regime(spec2)


def test_nonmonotone_probability_weighting_is_rejected():
    spec = _spec()
    # gamma well below ~0.28 makes Tversky-Kahneman w(p) non-monotone.
    spec["prospect_theory"]["gamma"] = 0.20
    with pytest.raises(BehavioralRegimeError, match="non-monotone"):
        evaluate_behavioral_regime(spec)


def test_unknown_arrival_regime_is_rejected():
    spec = _spec()
    spec["arrival_regime"] = "not_a_taxonomy_regime"
    with pytest.raises(BehavioralRegimeError, match="arrival_regime"):
        evaluate_behavioral_regime(spec)


# --------------------------------------------------------------------------- #
# unit: prospect functions
# --------------------------------------------------------------------------- #
def test_prospect_value_is_loss_averse():
    lam = 2.25
    assert prospect_value(1.0, 0.88, 0.88, lam) > 0
    assert prospect_value(-1.0, 0.88, 0.88, lam) < 0
    # A symmetric $1 loss weighs more than a $1 gain by the loss-aversion factor.
    assert -prospect_value(-1.0, 0.88, 0.88, lam) > prospect_value(1.0, 0.88, 0.88, lam)


def test_probability_weight_endpoints():
    assert probability_weight(0.0, 0.61) == 0.0
    assert probability_weight(1.0, 0.61) == 1.0
