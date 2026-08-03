"""Outcome-based wisdom-services pricing engine (OPX-1) -- a contract with teeth.

Grounding frame
---------------
The 3-T Framework reads an engagement as an exchange between two systems
(provider mesh <-> client) across three tiers -- Ecosystem -> Value -> Knowledge
-- governed by two order parameters: system-openness and boundary-complexity.
This engine prices that exchange, and it uses the IBM Customer-Transformation
value-driver tree (grow-revenue / manage-cost / utilize-capital / manage-risk)
as the client's Value tier.

An engagement price is a RISK-ADJUSTED, RECEIPTED VALUE-TRANSFER, decomposed in
six stages, each of which CONSUMES a merged estate piece by reference (no fork):

  1. Outcome value V   -- Delta(client value drivers) as an Economic-Profit delta,
                          via the EP kernel (``uvmc.reconcile_ep_components``).
                          Drivers = the four IBM value-driver-tree branches.
  2. Value-of-Information (truth price)
                       -- Bayesian VoI = E[decision value | knowledge]
                          - E[decision value | without]. The knowledge is graded
                          by the-assay 5-axis verdict (consumed by reference):
                          certified -> full VoI, speculative -> discounted,
                          false -> clawback.
  3. Risk-adjust (RAROC)
                       -- EconomicCapital = coherent-tail(F_outcome) via the
                          RM-1 risk kernel (ES / spectral). Risk-adjusted value
                          RAV = E[V] - hurdle * EconomicCapital.
  4. Complexity/time discount
                       -- Fisher-real discount over horizon tau (``inflation.
                          real_rate`` + ``term_calculus.price``) times a
                          complexity friction on the 3-T boundary-complexity axis.
  5. Equilibrium split -- anneal to the joint-surplus-maximizing (Nash bargaining)
                          point between the provider cost-floor and the client
                          value-ceiling. Value is conserved; the captured surplus
                          is the free-energy drop (welfare-annealing, transaction
                          scale, consumed as a soft-ref / injection seam).
  6. Mesh split        -- Euler / marginal-contribution allocation of the total
                          price P across providers, weighted by GKN standing, with
                          Sum == P enforced by the IC-1 conservation settlement.
                          Settled on a real-asset-backed token unit grounded in a
                          Jacob's-ladder real-asset rung (ALC-1). Reputation ==
                          liquidity == capital (Economia Mentium).

Teeth (both directions)
-----------------------
VERIFIES
  * an engagement with a VERIFIED outcome-receipt prices to a POSITIVE
    risk-adjusted value (joint surplus >= 0, price in [floor, ceiling]);
  * the mesh contributions SUM to the total price (conservation);
  * certified truth earns FULL VoI; speculative truth is DISCOUNTED.
REJECTS (raise ``OutcomePricingError``)
  * a price NOT contingent on a verified outcome-receipt -- that is
    time-and-materials, not outcome-based;
  * truth priced ABOVE its VoI, or full VoI charged on UNCERTIFIED knowledge
    (the clawback path);
  * a mesh split whose contributions do NOT sum to P (value created / lost in the
    split -- a conservation violation);
  * a price that IGNORES the outcome distribution (no coherent risk-adjustment);
  * a FALSE-graded outcome that is NOT clawed back.

Deterministic and stdlib-only. Measurement, simulation and audit only.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from ..inflation import real_rate
from ..risk_measures import COHERENT_KERNELS, LossDistribution, risk
from ..settlement import SettlementError, _canonical, _sha256, settle
from ..term_calculus import price as tc_discount_price
from ..uvmc import reconcile_ep_components
from ..validation import validate_json_file

_SCHEMA = "schemas/outcome_pricing.schema.json"

# --------------------------------------------------------------------------- #
# controlled vocabularies (the checker is the authority; the schema documents)
# --------------------------------------------------------------------------- #

# IBM Customer-Transformation value-driver tree -- the client's Value tier.
IBM_VALUE_DRIVERS = ("grow_revenue", "manage_cost", "utilize_capital", "manage_risk")

# Each value driver maps its improvement onto an EP-kernel component. A positive
# driver delta is value-accretive; the sign wiring makes that explicit so the EP
# identity (reconcile_ep_components) does the arithmetic, not this module.
_DRIVER_TO_EP = {
    "grow_revenue": ("revenue", +1.0),      # more revenue -> more EP
    "manage_cost": ("expense", -1.0),       # less expense -> more EP
    "utilize_capital": ("capital_charge", -1.0),  # less capital charge -> more EP
    "manage_risk": ("expected_loss", -1.0),  # less expected loss -> more EP
}

# the-assay projected grade (assay() -> ok / sad / bad) governs the VoI multiplier.
#   certified (ok)   -> full VoI
#   speculative(sad) -> discounted VoI (< full; clamped by an explicit factor)
#   false (bad)      -> clawback (VoI must be <= 0, and a clawback must be booked)
_ASSAY_GRADES = ("certified", "speculative", "false")


class OutcomePricingError(ValueError):
    """Raised when an engagement cannot be priced under the contract (REJECTED)."""


# --------------------------------------------------------------------------- #
# stage 1 -- outcome value V = Delta(client value drivers) as an EP delta
# --------------------------------------------------------------------------- #
def outcome_value(spec: dict) -> dict:
    """V = EP_after - EP_before, over the four IBM value-driver-tree branches.

    ``value_drivers`` supplies, per driver, the pre/post move of its EP component.
    The EP identity itself is NOT reimplemented here: both endpoints are reconciled
    through ``uvmc.reconcile_ep_components`` so V is a genuine Economic-Profit delta.
    """
    vd = spec["value_drivers"]
    unknown = set(vd) - set(IBM_VALUE_DRIVERS)
    if unknown:
        raise OutcomePricingError(
            f"REJECTED: unknown value driver(s) {sorted(unknown)}; the IBM tree is {list(IBM_VALUE_DRIVERS)}"
        )

    base = {
        "revenue": 0.0, "expected_loss": 0.0, "expense": 0.0,
        "funding_costs": 0.0, "funding_credits": 0.0, "taxes": 0.0,
        "capital_charge": 0.0,
    }
    before = dict(base)
    after = dict(base)
    per_driver: dict[str, float] = {}
    for driver in IBM_VALUE_DRIVERS:
        move = vd.get(driver)
        if move is None:
            per_driver[driver] = 0.0
            continue
        component, ep_sign = _DRIVER_TO_EP[driver]
        b = float(move.get("baseline", 0.0))
        a = float(move.get("post", 0.0))
        # Store the RAW component level; reconcile_ep_components applies the EP
        # sign (revenue adds, expense/loss/capital subtract). ``ep_sign`` is that
        # component's sign in the EP identity, used only to attribute V per driver.
        before[component] += b
        after[component] += a
        # the driver's contribution to V is the EP change from moving that leg.
        per_driver[driver] = ep_sign * (a - b)

    ep_before = reconcile_ep_components(before)
    ep_after = reconcile_ep_components(after)
    v = ep_after - ep_before
    return {
        "value_point": v,
        "ep_before": ep_before,
        "ep_after": ep_after,
        "per_driver": per_driver,
    }


# --------------------------------------------------------------------------- #
# stage 2 -- Value-of-Information (truth price), graded by the-assay
# --------------------------------------------------------------------------- #
def value_of_information(spec: dict) -> dict:
    """Bayesian VoI graded by the-assay verdict (consumed by reference).

    Raw VoI = E[decision value | knowledge] - E[decision value | without].
    The projected assay grade sets the fraction of raw VoI a wisdom-service may
    charge:
      * certified   -> full (multiplier == 1);
      * speculative -> discounted (0 <= multiplier < 1; the caller states the
                       explicit discount; full VoI on speculative knowledge is
                       REJECTED);
      * false       -> clawback (priced VoI must be <= 0 AND a clawback booked).

    Teeth:
      * truth priced above its (graded) VoI ceiling is REJECTED;
      * full VoI charged on UNCERTIFIED (non-certified) knowledge is REJECTED;
      * a false-graded outcome with no clawback is REJECTED.
    """
    know = spec["knowledge"]
    grade = know.get("assay_grade")
    if grade not in _ASSAY_GRADES:
        raise OutcomePricingError(
            f"REJECTED: knowledge.assay_grade must be one of {list(_ASSAY_GRADES)} "
            "(projected from the-assay 5-axis verdict)"
        )
    # the-assay + counter-test-gate + evidence receipts are consumed by reference:
    # any priced knowledge must cite the assay record, its counter-test and an
    # evidence receipt. A truth price with no provenance is not assayed truth.
    for ref in ("assay_ref", "counter_test_ref", "evidence_receipt_ref"):
        if not know.get(ref):
            raise OutcomePricingError(
                f"REJECTED: knowledge.{ref} is required -- a truth price must consume "
                "the-assay / counter-test-gate / evidence receipt by reference"
            )

    dv_with = float(know["decision_value_with"])
    dv_without = float(know["decision_value_without"])
    raw_voi = dv_with - dv_without

    priced = float(know.get("priced_voi", 0.0))
    speculative_discount = float(know.get("speculative_discount", 0.0))
    clawback = bool(know.get("clawback", False))

    if grade == "certified":
        ceiling = raw_voi  # full VoI
    elif grade == "speculative":
        if not (0.0 <= speculative_discount < 1.0):
            raise OutcomePricingError(
                "REJECTED: speculative knowledge requires speculative_discount in [0, 1) "
                "(full VoI on UNCERTIFIED knowledge is not permitted)"
            )
        ceiling = raw_voi * (1.0 - speculative_discount)
        # explicit uncertified-full-VoI tooth: a speculative grade that still
        # prices the full raw VoI is rejected even if discount==0 slipped through.
        if priced > ceiling + 1e-9:
            raise OutcomePricingError(
                "REJECTED: speculative (UNCERTIFIED) knowledge priced above its "
                f"discounted VoI ceiling ({priced} > {ceiling})"
            )
    else:  # false -> clawback path
        if not clawback:
            raise OutcomePricingError(
                "REJECTED: a FALSE-graded outcome must book a clawback "
                "(knowledge.clawback == true); it cannot be priced as value"
            )
        if priced > 0.0:
            raise OutcomePricingError(
                "REJECTED: FALSE-graded knowledge cannot carry a positive truth price "
                f"(priced_voi {priced} > 0); the clawback reverses it"
            )
        ceiling = min(raw_voi, 0.0)

    if priced > ceiling + 1e-9:
        raise OutcomePricingError(
            f"REJECTED: truth priced above its VoI ({priced} > ceiling {ceiling})"
        )

    return {
        "raw_voi": raw_voi,
        "grade": grade,
        "voi_ceiling": ceiling,
        "priced_voi": priced,
        "clawback": clawback,
    }


# --------------------------------------------------------------------------- #
# stage 3 -- risk-adjust: RAROC over the outcome distribution F_outcome
# --------------------------------------------------------------------------- #
def risk_adjust(spec: dict, v_point: float, voi_priced: float) -> dict:
    """RAV = E[V] - hurdle * EconomicCapital, EconomicCapital = coherent-tail(F).

    The outcome distribution F_outcome is the distribution of realised engagement
    value (value-driver delta + priced VoI). EconomicCapital is a COHERENT tail
    measure (Expected Shortfall / spectral) over F_outcome, via the RM-1 kernel.
    A price that ignores F_outcome, or gates capital on a NON-coherent measure,
    is REJECTED.

    Tooth: the deterministic value point (V + priced VoI) must equal E[F_outcome]
    within tolerance -- the value-driver delta IS the expected outcome, not a
    number bolted beside the distribution.
    """
    rm = spec.get("risk")
    if not rm or "outcome_samples" not in rm:
        raise OutcomePricingError(
            "REJECTED: no outcome distribution F_outcome supplied; a price that "
            "ignores the outcome distribution is not risk-adjusted (time-and-materials)"
        )
    kernel = rm.get("kernel", "expected_shortfall")
    if kernel not in COHERENT_KERNELS:
        raise OutcomePricingError(
            f"REJECTED: EconomicCapital requires a COHERENT tail measure "
            f"{sorted(COHERENT_KERNELS)}; {kernel!r} is not coherent"
        )
    alpha = float(rm.get("alpha", 0.975))
    hurdle = float(spec["hurdle_rate"])
    if hurdle < 0.0:
        raise OutcomePricingError("REJECTED: hurdle_rate must be non-negative")

    samples = [float(x) for x in rm["outcome_samples"]]
    F = LossDistribution.from_samples(samples)
    measure = risk(F, kernel, alpha=alpha)
    economic_capital = measure.value  # coherent tail capital magnitude
    expected_value = sum(samples) / len(samples)

    deterministic_value = v_point + voi_priced
    tol = float(rm.get("value_tolerance", 1e-6))
    if abs(deterministic_value - expected_value) > tol:
        raise OutcomePricingError(
            "REJECTED: value-driver delta + priced VoI "
            f"({deterministic_value}) does not equal E[F_outcome] ({expected_value}) "
            f"within tolerance {tol}; the outcome distribution is inconsistent with V"
        )

    rav = expected_value - hurdle * economic_capital
    raroc = expected_value / economic_capital if economic_capital > 0 else float("inf")
    return {
        "expected_value": expected_value,
        "economic_capital": economic_capital,
        "coherent": measure.coherent,
        "kernel": kernel,
        "alpha": alpha,
        "hurdle_rate": hurdle,
        "risk_adjusted_value": rav,
        "raroc": raroc,
        "distribution_id": measure.distribution_id,
        "provisional": measure.provisional,
    }


# --------------------------------------------------------------------------- #
# stage 4 -- complexity/time discount: Fisher-real over tau + boundary friction
# --------------------------------------------------------------------------- #
def complexity_time_discount(spec: dict, rav: float) -> dict:
    """Discount RAV by a Fisher-REAL rate over horizon tau and a 3-T complexity
    friction.

    The real discount rate is the exact Fisher separation
    ``real_rate(nominal, inflation)`` (consumed from ``inflation``); the horizon
    discount factor is ``term_calculus.price`` of a unit bullet at tenor tau (the
    TC-1 present-value operator, consumed rather than re-derived). The boundary-
    complexity axis of the 3-T frame adds a multiplicative friction
    ``exp(-kappa * boundary_complexity)`` in [0, 1].
    """
    disc = spec["discount"]
    nominal = float(disc["nominal_rate"])
    inflation = float(disc["inflation"])
    tau = float(disc["horizon_years"])
    if tau < 0.0:
        raise OutcomePricingError("REJECTED: discount.horizon_years must be non-negative")

    r_real = real_rate(nominal, inflation)  # exact Fisher (1+n)/(1+pi) - 1
    # term_calculus.price of a unit bullet at tenor tau == 1/(1+r_real)^tau.
    time_factor = tc_discount_price([{"tenor": tau, "amount": 1.0}], r_real)

    kappa = float(disc.get("complexity_kappa", 0.0))
    boundary_complexity = float(disc.get("boundary_complexity", 0.0))
    if kappa < 0.0 or boundary_complexity < 0.0:
        raise OutcomePricingError(
            "REJECTED: complexity_kappa and boundary_complexity must be non-negative "
            "(3-T boundary-complexity is a friction, never a subsidy)"
        )
    complexity_factor = math.exp(-kappa * boundary_complexity)

    discounted = rav * time_factor * complexity_factor
    return {
        "real_rate": r_real,
        "time_factor": time_factor,
        "complexity_factor": complexity_factor,
        "discounted_value": discounted,
    }


# --------------------------------------------------------------------------- #
# stage 5 -- equilibrium split: Nash bargaining (welfare-annealing at txn scale)
# --------------------------------------------------------------------------- #
def equilibrium_price(spec: dict, client_value_ceiling: float, anneal_fn=None) -> dict:
    """Anneal to the joint-surplus-maximizing (generalized-Nash) bargaining point.

    The provider cost-floor and the client value-ceiling bound the deal. Joint
    surplus S = ceiling - floor is the free-energy the exchange can dissipate; the
    annealer settles the price at the generalized-Nash split
    ``P = floor + beta * S`` (beta = provider bargaining weight; symmetric Nash is
    0.5). Value is conserved: floor + provider_surplus + client_surplus == ceiling.

    ``anneal_fn`` is an INJECTION SEAM for the welfare-annealing model (branch
    soft-ref): if supplied it returns the settled split fraction; otherwise the
    closed-form Nash point is used (the annealer's attractor).

    Tooth: a non-positive joint surplus means the verified outcome does NOT price
    to positive risk-adjusted value -- REJECTED (there is no deal to split).
    """
    eq = spec["equilibrium"]
    floor = float(eq["provider_cost_floor"])
    ceiling = float(client_value_ceiling)
    beta = float(eq.get("provider_bargaining_weight", 0.5))
    if not (0.0 <= beta <= 1.0):
        raise OutcomePricingError("REJECTED: provider_bargaining_weight must be in [0, 1]")

    surplus = ceiling - floor
    if surplus <= 0.0:
        raise OutcomePricingError(
            "REJECTED: client value-ceiling does not exceed provider cost-floor "
            f"(surplus {surplus} <= 0); a verified outcome must price to POSITIVE "
            "risk-adjusted value or there is no outcome-based engagement"
        )

    fraction = float(anneal_fn(floor, ceiling, beta)) if anneal_fn else beta
    if not (0.0 <= fraction <= 1.0):
        raise OutcomePricingError("REJECTED: annealed split fraction must be in [0, 1]")

    price = floor + fraction * surplus
    provider_surplus = price - floor
    client_surplus = ceiling - price
    # value conservation of the bargaining split (the free-energy drop == surplus).
    if abs((floor + provider_surplus + client_surplus) - ceiling) > 1e-6:
        raise OutcomePricingError("REJECTED: bargaining split does not conserve value")

    return {
        "provider_cost_floor": floor,
        "client_value_ceiling": ceiling,
        "joint_surplus": surplus,
        "bargaining_weight": beta,
        "price": price,
        "provider_surplus": provider_surplus,
        "client_surplus": client_surplus,
        "free_energy_drop": surplus,
    }


# --------------------------------------------------------------------------- #
# stage 6 -- mesh split: Euler/marginal-contribution allocation, Sum == P
# --------------------------------------------------------------------------- #
def mesh_split(spec: dict, total_price: float) -> dict:
    """Euler / marginal-contribution allocation of P across the provider mesh.

    Each provider carries a marginal contribution ``m_i`` (its Euler share of the
    value it helped create) and a GKN standing weight ``w_i`` (reputation ==
    liquidity == capital). The allocation is proportional to ``m_i * w_i`` and
    normalised so that ``Sum P_i == P`` exactly; the equality is then PROVEN by
    running it through the IC-1 conservation settlement (``settlement.settle``),
    which fails closed on any residual.

    The split is denominated in a real-asset-backed token unit whose base must be
    a Jacob's-ladder real-asset rung (ALC-1). A settlement unit that is not
    real-asset-backed is REJECTED (a pure claim cannot be the base of settlement).

    Tooth: a mesh split whose contributions do not sum to P (value created / lost
    in the split) is REJECTED by the conservation settlement.
    """
    mesh = spec["mesh"]
    providers = mesh["providers"]
    if not providers:
        raise OutcomePricingError("REJECTED: mesh split requires at least one provider")

    unit = mesh.get("settlement_unit", {})
    if not unit.get("real_asset_backed", False) or not unit.get("asset_ladder_rung"):
        raise OutcomePricingError(
            "REJECTED: settlement_unit must be real-asset-backed and cite a "
            "Jacob's-ladder asset_ladder_rung (ALC-1); reputation==liquidity==capital "
            "still settles on a REAL-asset base"
        )

    explicit = bool(mesh.get("explicit_allocations", False))
    allocations = []
    running = 0.0
    if explicit:
        # Teeth path: the fixture supplies each share verbatim (e.g. an externally
        # proposed split). The engine does NOT normalise it -- it is settled AS IS,
        # so a split whose shares do not sum to P is caught by the conservation
        # settlement below and REJECTED. This is where "Sum != P" actually fires.
        for p in providers:
            if "allocation" not in p:
                raise OutcomePricingError(
                    "REJECTED: explicit_allocations requires an 'allocation' per provider"
                )
            share = float(p["allocation"])
            running += share
            allocations.append({
                "provider": p["provider"],
                "marginal_contribution": float(p["marginal_contribution"]),
                "standing_weight": float(p["standing_weight"]),
                "allocation": share,
            })
    else:
        # Euler / marginal-contribution allocation weighted by GKN standing.
        weights = []
        for p in providers:
            m = float(p["marginal_contribution"])
            w = float(p["standing_weight"])
            if m < 0.0 or w < 0.0:
                raise OutcomePricingError(
                    "REJECTED: marginal_contribution and standing_weight must be non-negative"
                )
            weights.append(m * w)
        denom = sum(weights)
        if denom <= 0.0:
            raise OutcomePricingError(
                "REJECTED: total marginal-contribution * standing weight is zero; "
                "cannot allocate the price"
            )
        for i, (p, wt) in enumerate(zip(providers, weights)):
            # allocate exactly; the last provider absorbs the rounding residual so
            # the split conserves to the cent before the settlement even runs.
            if i < len(providers) - 1:
                share = total_price * wt / denom
            else:
                share = total_price - running
            running += share
            allocations.append({
                "provider": p["provider"],
                "marginal_contribution": float(p["marginal_contribution"]),
                "standing_weight": float(p["standing_weight"]),
                "allocation": share,
            })

    # PROVE conservation via the IC-1 settlement: P in, provider shares out.
    settlement = {
        "settlement_id": mesh.get("settlement_id", f"opx-mesh-{spec.get('contract_id', 'opx')}"),
        "as_of": spec.get("as_of", ""),
        "conserved_quantity": "engagement_price",
        "tolerance": float(mesh.get("tolerance", 1e-6)),
        "inflows": [{"party": "client", "amount": total_price}],
        "outflows": [{"party": a["provider"], "amount": a["allocation"]} for a in allocations],
    }
    try:
        receipt = settle(settlement)
    except SettlementError as exc:
        # A split that does not conserve is a value creation/loss -- REJECTED.
        raise OutcomePricingError(f"REJECTED: mesh split violates conservation (Sum != P): {exc}")

    return {
        "settlement_unit": unit,
        "allocations": allocations,
        "sum_allocated": running,
        "total_price": total_price,
        "conservation": receipt["conservation"],
        "settlement_receipt": receipt["receipt_hash"],
    }


# --------------------------------------------------------------------------- #
# the engine
# --------------------------------------------------------------------------- #
def price_engagement(spec: dict, *, anneal_fn=None) -> dict:
    """Price one engagement end-to-end and emit a receipted decomposition.

    The first tooth gates everything: without a VERIFIED outcome-receipt this is
    time-and-materials, not outcome-based pricing -- REJECTED before any value is
    computed.
    """
    outcome = spec.get("outcome_receipt", {})
    if not outcome.get("verified", False) or not outcome.get("receipt_id"):
        raise OutcomePricingError(
            "REJECTED: engagement price is not contingent on a VERIFIED "
            "outcome-receipt (missing outcome_receipt.verified / receipt_id); "
            "an unverified engagement is time-and-materials, not outcome-based"
        )

    v = outcome_value(spec)
    voi = value_of_information(spec)
    rav = risk_adjust(spec, v["value_point"], voi["priced_voi"])
    disc = complexity_time_discount(spec, rav["risk_adjusted_value"])

    # The client's willingness-to-pay ceiling is the discounted, risk-adjusted,
    # VoI-graded value of the outcome. (The priced VoI already sits inside
    # E[F_outcome]; the ceiling is the discounted risk-adjusted value.)
    ceiling = disc["discounted_value"]
    eq = equilibrium_price(spec, ceiling, anneal_fn=anneal_fn)
    mesh = mesh_split(spec, eq["price"])

    result = {
        "contract_id": spec.get("contract_id", "opx"),
        "as_of": spec.get("as_of", ""),
        "engagement": spec.get("engagement", ""),
        "outcome_receipt": outcome,
        "decomposition": {
            "outcome_value": v,
            "value_of_information": voi,
            "risk_adjust": rav,
            "complexity_time_discount": disc,
            "equilibrium": eq,
            "mesh_split": mesh,
        },
        "engagement_price": eq["price"],
        "measurement_boundary": spec.get(
            "measurement_boundary",
            {"mode": "doctrine_measurement_simulation_audit_only"},
        ),
    }
    body = {k: v for k, v in result.items() if k != "receipt_id"}
    result["receipt_id"] = _sha256(_canonical(body))
    return result


def run_outcome_pricing(path: str) -> dict:
    """Schema-validate an engagement fixture and price it (measurement only)."""
    validate_json_file(path, _SCHEMA)
    spec = json.loads(Path(path).read_text())
    return price_engagement(spec)


def main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Price an outcome-based wisdom-services engagement (OPX-1)."
    )
    parser.add_argument("--engagement", default="examples/outcome_pricing_engagement.json")
    parser.add_argument("--schema", default=_SCHEMA)
    parser.add_argument("--receipt", default=None, help="Optional path to write the receipt JSON.")
    args = parser.parse_args(argv)

    result = run_outcome_pricing(args.engagement)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.receipt:
        Path(args.receipt).write_text(text + "\n")
    print(text)
    return 0
