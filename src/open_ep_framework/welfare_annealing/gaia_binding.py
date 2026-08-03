"""Emit GAIA value-flow manifests from a welfare-annealing / EP run (upward binding).

The welfare-annealing spine is admissible as the *value-flow subsystem* of the GAIA world
model only if each run presents two manifests that conform to the gaia-world-model economy
contracts (branch ``feat/value-flow-subsystem``):

  * ``ValueFlowSubsystemBinding`` (``value_flow_binding.v1``) -- binds the carrying-capacity
    discount, the Jacob's-ladder natural-capital / renewable base, and the QoL objective
    UPWARD into the world-model substrate W by REFERENCE.
  * ``TwinScaleValueTransfer`` (``twin_scale_transfer.v1``) -- a value flow across an adjacent
    boundary of the twin hierarchy (galactic/space twin <-> world economic twin <-> human
    digital twin), conserved under IC-1.

This module *emits* those manifests AND enforces the same teeth on the EP side, so the
free-parameter smell fails HERE (on real EP runs), not only in gaia's fixture checks:

  T1-CONST    the carrying-capacity discount source MUST be a world-model read
              (``gaia://...``), never a hardcoded constant.
  T4-REGEN    a ``renewable_harvest`` regeneration rate MUST be a world-model read
              (constant / none is the free-parameter smell -> REJECTED).
  T3-QOL      every QoL dimension MUST be a twin-aggregate carrying its ``from_twin_dimension``
              (twin-derived, not exogenous).
  T2-CONSERVE the twin-scale transfer MUST conserve value:
              ``parent == sum(children) + sum(sinks) - sum(sources)`` within tolerance.
  T1-RESERVE  a non-renewable draw taking a stock BELOW the world-model reserve floor is
              ADMITTED WITH A FLAG (planetary-boundary breach; the paper-inductance
              false-growth analog) -- surfaced in provenance, not silently accepted.

Consume-not-fork: the gaia schemas are gaia-owned and referenced by pinned ref; the QoL
value is computed from the welfare-annealing objective (``qol.qol_index``) so the emitted
manifest is derived from the real run, not a hand-set number.

Deterministic and stdlib-only.
"""
from __future__ import annotations

from .qol import CAPABILITY_DIMENSIONS, qol_index, require_dimensions

WORLD_MODEL_READ = "world_model_read"
BINDING_VERSION = "v1"
TRANSFER_VERSION = "v1"
# The gaia twin hierarchy, outer-to-inner (schema-pinned, exactly three scales).
SCALE_STACK = ["galactic_space_twin", "world_economic_twin", "human_digital_twin"]
# The IC-1 conservation rule string, pinned by the twin_scale_transfer.v1 schema.
CONSERVATION_RULE = "parent_value == sum(children) + sum(sinks) - sum(sources)"
# The QoL dimensions the binding aggregates from human-twin state.
QOL_DIMENSIONS = CAPABILITY_DIMENSIONS  # (life_length, health, education)


class GaiaBindingError(ValueError):
    """Raised when an EP run cannot present an admissible GAIA value-flow manifest."""


def _require_world_model_read(source: dict, where: str, tooth: str) -> None:
    """A free parameter (constant / none) where a world-model read is required is REJECTED."""
    kind = source.get("kind")
    if kind != WORLD_MODEL_READ:
        raise GaiaBindingError(
            f"REJECTED ({tooth}): {where} source.kind must be {WORLD_MODEL_READ!r} "
            f"(a gaia:// world-model read), not {kind!r} -- the free-parameter smell."
        )
    if not source.get("read_ref"):
        raise GaiaBindingError(
            f"REJECTED ({tooth}): {where} world_model_read requires a resolvable read_ref."
        )


def emit_value_flow_binding(gaia: dict) -> dict:
    """Emit a ``ValueFlowSubsystemBinding`` (value_flow_binding.v1) from a welfare run.

    Enforces T1-CONST (carrying-capacity source), T4-REGEN (renewable regeneration source)
    and T3-QOL (twin-aggregate dimensions); records T1-RESERVE reserve-floor breaches as
    admitted-with-flag entries in provenance. Returns the manifest dict."""
    # --- T1-CONST: carrying-capacity discount must be a world-model read ---------------- #
    cc = gaia["carrying_capacity"]
    _require_world_model_read(cc["source"], "carrying_capacity", "T1-CONST")

    # --- ecosystem assets: T4-REGEN + T1-RESERVE ---------------------------------------- #
    flags = []
    assets_out = []
    for asset in gaia["ecosystem_assets"]:
        rung = asset["rung"]
        regen = asset["regeneration"]
        if rung == "renewable_harvest":
            _require_world_model_read(
                regen["source"], f"ecosystem_asset[{rung}].regeneration", "T4-REGEN")
        stock = asset["stock"]
        reserve = stock["reserve"]
        # the reserve floor itself must be a world-model read (never a made-up floor)
        _require_world_model_read(reserve["source"], f"ecosystem_asset[{rung}].reserve",
                                  "T1-RESERVE")
        draw = float(stock.get("non_renewable_draw", 0.0))
        floor = float(reserve["floor"])
        post = float(stock["current"]) - draw
        if draw > 0.0 and post < floor:
            # ADMITTED WITH FLAG (planetary-boundary breach / false-growth analog)
            flags.append({
                "tooth": "T1-RESERVE",
                "asset": asset.get("biosphere_ref"),
                "reserve_floor": floor,
                "post_draw_stock": post,
                "shortfall": round(floor - post, 10),
                "disposition": "admitted_with_flag",
                "note": "non-renewable draw takes the stock below the world-model reserve "
                        "floor -- planetary-boundary breach (paper-inductance false growth)",
            })
        assets_out.append(asset)

    # --- T3-QOL: every dimension must be a twin-aggregate with from_twin_dimension ------- #
    qol_in = gaia["qol"]
    require_dimensions_declared(qol_in)
    groups = qol_in["groups"]
    for g in groups:
        require_dimensions(g, "qol.groups[]")
    population_ref = qol_in.get("population_ref")
    dims_out = []
    declared = {d["name"]: d for d in qol_in["dimensions"]}
    for name in QOL_DIMENSIONS:
        if name not in declared:
            raise GaiaBindingError(
                f"REJECTED (T3-QOL): QoL dimension {name!r} not declared; the index must "
                f"aggregate all of {QOL_DIMENSIONS} from human-twin state.")
        from_twin = declared[name].get("from_twin_dimension")
        if not from_twin:
            raise GaiaBindingError(
                f"REJECTED (T3-QOL): QoL dimension {name!r} has no from_twin_dimension "
                "(exogenous / free-parameter); it must be twin-derived.")
        dims_out.append({
            "name": name,
            "derivation": {
                "kind": "twin_aggregate",
                "from_twin_dimension": from_twin,
                **({"population_ref": population_ref} if population_ref else {}),
            },
        })

    # QoL value is computed from the REAL welfare objective (population-weighted gmean).
    qol_value = qol_index(groups)

    binding = {
        "binding_version": BINDING_VERSION,
        "binding_type": "ValueFlowSubsystemBinding",
        "binding_id": gaia["binding_id"],
        "world_model_ref": gaia["world_model_ref"],
        "economic_spine_ref": gaia["economic_spine_ref"],
        "carrying_capacity": {
            "source": cc["source"],
            "value_index": float(cc["value_index"]),
        },
        "ecosystem_assets": assets_out,
        "qol_index": {
            "value": round(qol_value, 10),
            **({"population_ref": population_ref} if population_ref else {}),
            "dimensions": dims_out,
        },
        "provenance": {
            "as_of": gaia.get("as_of", ""),
            "emitter": "open_ep_framework.welfare_annealing.gaia_binding",
            "method": "welfare_annealing_upward_binding",
            "reserve_flags": flags,
        },
        "classification": {
            "surface": "measurement_simulation_audit_only",
            "boundary": "value_flow_subsystem_of_gaia_world_model",
        },
    }
    if gaia.get("welfare_annealing_ref"):
        binding["welfare_annealing_ref"] = gaia["welfare_annealing_ref"]
    return binding


def require_dimensions_declared(qol_in: dict) -> None:
    if "dimensions" not in qol_in or "groups" not in qol_in:
        raise GaiaBindingError("REJECTED (T3-QOL): qol must carry 'groups' and 'dimensions'.")


def emit_twin_scale_transfer(gaia: dict) -> dict:
    """Emit a ``TwinScaleValueTransfer`` (twin_scale_transfer.v1); enforce T2-CONSERVE.

    Value must conserve across the twin scale:
    ``parent == sum(children) + sum(sinks) - sum(sources)`` within tolerance. A cross-scale
    flow that creates value from nothing is REJECTED."""
    ts = gaia["twin_scale"]
    parent = ts["parent"]
    children = ts["children"]
    sources = ts.get("declared_sources", [])
    sinks = ts.get("declared_sinks", [])
    tol = float(ts.get("tolerance", 1e-6))

    sum_children = sum(float(c["value"]) for c in children)
    sum_sources = sum(float(s["amount"]) for s in sources)
    sum_sinks = sum(float(s["amount"]) for s in sinks)
    expected_parent = sum_children + sum_sinks - sum_sources
    residual = float(parent["value"]) - expected_parent
    if abs(residual) > tol:
        raise GaiaBindingError(
            f"REJECTED (T2-CONSERVE): twin-scale value not conserved -- parent "
            f"{parent['value']} != sum(children)={sum_children} + sum(sinks)={sum_sinks} "
            f"- sum(sources)={sum_sources} = {expected_parent} (residual={residual}, "
            f"tolerance={tol}). A cross-scale flow cannot create value from nothing."
        )

    transfer = {
        "transfer_version": TRANSFER_VERSION,
        "transfer_type": "TwinScaleValueTransfer",
        "transfer_id": ts["transfer_id"],
        "scale_stack": list(SCALE_STACK),
        "parent": {k: parent[k] for k in ("scale", "ref", "value") if k in parent},
        "children": [{k: c[k] for k in ("scale", "ref", "value") if k in c} for c in children],
        "conservation": {"rule": CONSERVATION_RULE, "tolerance": tol},
        "provenance": {
            "as_of": gaia.get("as_of", ""),
            "emitter": "open_ep_framework.welfare_annealing.gaia_binding",
            "residual": round(residual, 12),
        },
        "classification": {
            "surface": "measurement_simulation_audit_only",
            "boundary": "twin_scale_value_transfer",
        },
    }
    if sources:
        transfer["declared_sources"] = [
            {"ref": s["ref"], "amount": float(s["amount"])} for s in sources]
    if sinks:
        transfer["declared_sinks"] = [
            {"ref": s["ref"], "amount": float(s["amount"])} for s in sinks]
    return transfer


def emit_manifests(gaia: dict) -> dict:
    """Emit BOTH gaia manifests from a welfare-annealing run, all EP-side teeth enforced."""
    binding = emit_value_flow_binding(gaia)
    transfer = emit_twin_scale_transfer(gaia)
    return {
        "value_flow_binding": binding,
        "twin_scale_transfer": transfer,
        "reserve_flags": binding["provenance"]["reserve_flags"],
    }
