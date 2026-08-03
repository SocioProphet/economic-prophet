"""GAIA value-flow binding tests (WEA-1 -> gaia-world-model value-flow subsystem).

Validates the manifests this module EMITS against the gaia-owned schemas (vendored under
tests/fixtures/gaia/, consume-by-reference) and exercises each EP-side tooth that mirrors the
gaia contract: T1-CONST, T4-REGEN, T3-QOL, T2-CONSERVE, and T1-RESERVE (admit-with-flag).
"""
import copy
import json
from pathlib import Path

import pytest

# jsonschema is the Draft 2020-12 validator; only the dedicated welfare-annealing workflow
# installs it. Under the stdlib-only main CI job it is absent -> skip this module cleanly
# (the module's teeth are also covered by the pure-stdlib code paths elsewhere).
jsonschema = pytest.importorskip("jsonschema")
Draft202012Validator = jsonschema.Draft202012Validator

from open_ep_framework.welfare_annealing.contract import run_record
from open_ep_framework.welfare_annealing.gaia_binding import (
    GaiaBindingError, emit_manifests, emit_twin_scale_transfer, emit_value_flow_binding,
)

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "examples" / "welfare_annealing"
GAIA = ROOT / "tests" / "fixtures" / "gaia"

VFB_SCHEMA = Draft202012Validator(json.loads(
    (GAIA / "value_flow_binding.v1.schema.json").read_text()))
TSVT_SCHEMA = Draft202012Validator(json.loads(
    (GAIA / "twin_scale_transfer.v1.schema.json").read_text()))


def _valid_gaia():
    return json.loads((EX / "gaia_binding.subsystem.valid.json").read_text())["gaia"]


# --- CONFORMANCE: emitted manifests validate against the gaia-owned schemas ---------- #
def test_emitted_binding_is_gaia_conformant():
    binding = emit_value_flow_binding(_valid_gaia())
    errs = sorted(VFB_SCHEMA.iter_errors(binding), key=lambda e: str(e.path))
    assert not errs, errs[0].message if errs else ""
    assert binding["binding_type"] == "ValueFlowSubsystemBinding"
    assert binding["binding_version"] == "v1"
    # QoL value is computed from the real welfare objective, not hand-set
    assert binding["qol_index"]["value"] == pytest.approx(46.5)


def test_emitted_transfer_is_gaia_conformant():
    transfer = emit_twin_scale_transfer(_valid_gaia())
    errs = sorted(TSVT_SCHEMA.iter_errors(transfer), key=lambda e: str(e.path))
    assert not errs, errs[0].message if errs else ""
    assert transfer["scale_stack"] == [
        "galactic_space_twin", "world_economic_twin", "human_digital_twin"]
    assert transfer["conservation"]["rule"] == \
        "parent_value == sum(children) + sum(sinks) - sum(sources)"


def test_run_record_emits_both_manifests():
    rec = json.loads((EX / "gaia_binding.subsystem.valid.json").read_text())
    out = run_record(rec)["outputs"]
    assert VFB_SCHEMA.is_valid(out["value_flow_binding"])
    assert TSVT_SCHEMA.is_valid(out["twin_scale_transfer"])
    assert out["reserve_flags"] == []


# --- TOOTH T1-CONST: carrying-capacity source must be a world-model read -------------- #
def test_constant_carrying_capacity_rejected():
    g = _valid_gaia()
    g["carrying_capacity"]["source"] = {"kind": "constant"}
    with pytest.raises(GaiaBindingError, match="T1-CONST"):
        emit_value_flow_binding(g)


def test_world_model_read_without_ref_rejected():
    g = _valid_gaia()
    g["carrying_capacity"]["source"] = {"kind": "world_model_read"}  # no read_ref
    with pytest.raises(GaiaBindingError, match="T1-CONST"):
        emit_value_flow_binding(g)


# --- TOOTH T4-REGEN: renewable regeneration must be a world-model read ---------------- #
def test_constant_renewable_regeneration_rejected():
    g = _valid_gaia()
    g["ecosystem_assets"][0]["regeneration"]["source"] = {"kind": "constant"}
    with pytest.raises(GaiaBindingError, match="T4-REGEN"):
        emit_value_flow_binding(g)


def test_none_renewable_regeneration_rejected():
    g = _valid_gaia()
    g["ecosystem_assets"][0]["regeneration"]["source"] = {"kind": "none"}
    with pytest.raises(GaiaBindingError, match="T4-REGEN"):
        emit_value_flow_binding(g)


def test_depleting_rung_may_have_none_regeneration():
    # the non-renewable rung is allowed regeneration source 'none'
    g = _valid_gaia()
    binding = emit_value_flow_binding(g)  # asset[1] is extractive_nonrenewable w/ none
    assert VFB_SCHEMA.is_valid(binding)


# --- TOOTH T3-QOL: every dimension must be twin-derived ------------------------------- #
def test_exogenous_qol_dimension_rejected():
    g = _valid_gaia()
    del g["qol"]["dimensions"][1]["from_twin_dimension"]  # drop health's twin ref
    with pytest.raises(GaiaBindingError, match="T3-QOL"):
        emit_value_flow_binding(g)


def test_missing_qol_dimension_rejected():
    g = _valid_gaia()
    g["qol"]["dimensions"] = [d for d in g["qol"]["dimensions"] if d["name"] != "education"]
    with pytest.raises(GaiaBindingError, match="T3-QOL"):
        emit_value_flow_binding(g)


# --- TOOTH T2-CONSERVE: value conserves across the twin scale ------------------------- #
def test_twin_scale_conservation_holds_with_sources_and_sinks():
    # parent 1000 == children(950) + sinks(80) - sources(30)
    transfer = emit_twin_scale_transfer(_valid_gaia())
    assert transfer["provenance"]["residual"] == pytest.approx(0.0)


def test_nonconserving_twin_scale_rejected():
    g = _valid_gaia()
    g["twin_scale"]["parent"]["value"] = 1200.0  # created value from nothing
    with pytest.raises(GaiaBindingError, match="T2-CONSERVE"):
        emit_twin_scale_transfer(g)


# --- TOOTH T1-RESERVE: a below-floor non-renewable draw is admitted WITH A FLAG ------- #
def test_reserve_floor_breach_admitted_with_flag():
    g = _valid_gaia()
    # push the oil draw below its world-model reserve floor (current 500, floor 100)
    g["ecosystem_assets"][1]["stock"]["non_renewable_draw"] = 450.0  # post = 50 < 100
    binding = emit_value_flow_binding(g)          # ADMITTED (not rejected)
    assert VFB_SCHEMA.is_valid(binding)           # still gaia-conformant
    flags = binding["provenance"]["reserve_flags"]
    assert len(flags) == 1
    assert flags[0]["tooth"] == "T1-RESERVE"
    assert flags[0]["disposition"] == "admitted_with_flag"
    assert flags[0]["shortfall"] == pytest.approx(50.0)


def test_reserve_floor_respected_no_flag():
    binding = emit_value_flow_binding(_valid_gaia())  # oil draw 50, post 450 >= floor 100
    assert binding["provenance"]["reserve_flags"] == []


# --- pins carried through (coordinator re-pins to merged SHAs post-merge) ------------- #
def test_refs_carried_into_binding():
    binding = emit_value_flow_binding(_valid_gaia())
    assert binding["world_model_ref"].startswith("SocioProphet/gaia-world-model@")
    assert binding["economic_spine_ref"].startswith("SocioProphet/economic-prophet@")
    assert binding["welfare_annealing_ref"] == \
        "SocioProphet/economic-prophet@feat/welfare-annealing"


def test_all_gaia_invalid_fixtures_rejected():
    for path in sorted(EX.glob("gaia_binding.*.invalid.json")):
        with pytest.raises(Exception):
            run_record(json.loads(path.read_text()))


def test_emit_manifests_bundles_both():
    m = emit_manifests(copy.deepcopy(_valid_gaia()))
    assert set(m) == {"value_flow_binding", "twin_scale_transfer", "reserve_flags"}
