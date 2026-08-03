# Outcome-based wisdom-services pricing (OPX-1)

The commercial layer of the estate: it prices a customer engagement as a
**risk-adjusted, receipted value-transfer**, splits it coherently across the
provider mesh, and settles on a real-asset-backed token unit. It **consumes** the
economic-prophet financial spine and the estate epistemic/mesh contracts **by
reference** — it adds no new physics, it *denominates a commercial price* in the
invariants the spine already enforces.

- Module: `src/open_ep_framework/outcome_pricing/` (`pricing.py`, `__main__.py`)
- Schema: `schemas/outcome_pricing.schema.json`
- Fixtures: `examples/outcome_pricing_engagement.json` (+ 5 `*.invalid.json`)
- Tests: `tests/test_outcome_pricing.py`
- CLI: `oepf --mode outcome-pricing` · module: `python -m open_ep_framework.outcome_pricing`
- Make: `make outcome-pricing`, `make outcome-pricing-receipt`

Deterministic and stdlib-only. **Measurement, simulation and audit only**: no live
money movement, token issuance, redemption rights, or settlement rails.

## Grounding frame

The **3-T Framework** reads an engagement as an exchange between two systems (the
provider mesh ⟷ the client) across three tiers — **Ecosystem → Value → Knowledge**
— governed by two order parameters: **system-openness** and **boundary-complexity**.
The client's Value tier is the **IBM Customer-Transformation value-driver tree**:
grow-revenue / manage-cost / utilize-capital / manage-risk.

## Price decomposition (six stages, each consuming a merged estate piece)

| Stage | Quantity | Consumed by reference |
|------|----------|-----------------------|
| 1. Outcome value **V** | `V = EP_after − EP_before` over the four IBM value drivers | EP kernel — `uvmc.reconcile_ep_components` |
| 2. Value-of-Information (**truth price**) | Bayesian `VoI = E[dv│knowledge] − E[dv│without]`, graded by the-assay | the-assay 5-axis verdict · counter-test-gate · evidence receipts |
| 3. Risk-adjust (**RAROC**) | `RAV = E[V] − hurdle·EconomicCapital`, `EconomicCapital = coherent-tail(F_outcome)` | RM-1 risk measures (ES / spectral) |
| 4. Complexity/time **discount** | Fisher-real discount over horizon τ × 3-T boundary-complexity friction | `inflation.real_rate` (Fisher) · `term_calculus.price` (TC-1) |
| 5. **Equilibrium split** | anneal to the joint-surplus-maximizing (Nash) point `P = floor + β·S` | welfare-annealing (branch soft-ref / injection seam) |
| 6. **Mesh split** | Euler / marginal-contribution allocation of P, weighted by GKN standing, `Σ = P` | IC-1 conservation settlement · GKN standing · ALC-1 Jacob's-ladder real-asset base |

`assay grade`: **certified → full VoI**, **speculative → discounted**, **false → clawback**.
Reputation = liquidity = capital (Economia Mentium): GKN standing weights the split.

## Teeth (both directions)

**VERIFIES**
- an engagement with a **verified outcome-receipt** prices to a **positive**
  risk-adjusted value (joint surplus ≥ 0; price ∈ [floor, ceiling]);
- the mesh contributions **sum to the total price** (IC-1 conservation);
- **certified** truth earns **full** VoI; **speculative** truth is **discounted**.

**REJECTS**
- a price **not contingent on a verified outcome-receipt** — that is
  time-and-materials, not outcome-based;
- truth priced **above its VoI**, or full VoI on **uncertified** knowledge
  (the clawback path);
- a mesh split whose contributions **do not sum to P** (value created/lost);
- a price that **ignores the outcome distribution** (non-coherent capital);
- a **false-graded** outcome that is **not clawed back**.

Each `*.invalid.json` fixture exercises exactly one REJECT tooth; CI fails if any
is accepted.

## Bindings (bind-upward discipline)

This capability is **not shipped as a silo**. It declares two bindings, as
reflexively as the teeth.

### 1. UP into the world model / twin hierarchy

An engagement value-transfer **is a value flow** in the **world-economic-twin /
value-flow-mechanics** layer of the twin hierarchy
(galactic/space twin ⟷ **world economic twin** ⟷ human digital twin). The
provider-mesh ⟷ client exchange is one edge of that value-flow graph, and the
engagement price is the flow magnitude on that edge.

The **real-asset settlement** (stage 6) grounds in the **Gaia carrying-capacity
base**: the settlement unit must cite a **Jacob's-ladder (ALC-1) real-asset rung**,
whose natural-capital rungs bind to the `WorldModelSubstrate W`
(biosphere / carrying capacity) of `SocioProphet/gaia-world-model`. A token unit
that is not real-asset-backed is rejected — settlement cannot float free of the
world-state that supports it. This closes the gap named in
`feedback_bind_upward_worldmodel_ontogenesis`: the price is not a free parameter,
it is a world-state-grounded value flow.

Binding targets (by reference): `SocioProphet/gaia-world-model`
(`WorldModelSubstrate W`, carrying capacity), the world-economic-twin value-flow
layer, and the ALC-1 ladder natural-capital ⟷ biosphere crosswalk.

### 2. Through ontogenesis (governed Systema Concept Entries)

The six new concepts are routed into **`SocioProphet/ontogenesis`** as governed
**Systema Concept Entries** — SourceAnchored, provenance-classed, versioned and
receipted — not left as local schema-only vocabulary:

1. **outcome-value** · 2. **value-of-information price** ·
3. **risk-adjusted engagement price** · 4. **marginal-contribution mesh split** ·
5. **wisdom-service** · 6. **reputation = liquidity**.

Authored for promotion in `docs/systema/outcome_pricing_concept_entries.jsonld`
(shape: `ontogenesis/Platform/Systema/systema-concept-entry.ttl` +
`shapes/systema_concept_entry.shacl.ttl`). economic-prophet is the
**implementation-surface** owner; ontogenesis is the **concept-governance** owner.
`promotionState = extracted_candidate` until an ontogenesis owner promotes them.

**Concept-entry bundle receipt** (FIPS SHA-256 over the canonical 6-entry graph,
reproducible via the OPX-1 receipt spine):

```
sha256:a7f5d9fe2ac90d3002d89a492cc1787e8f303d67e7b5bf83c811c7bd5b8f1a10
```

## Consumed by reference (do not edit)

EP kernel (`uvmc`) · risk measures (`risk_measures`, RM-1) · conservation
settlement (`settlement`, IC-1) · term calculus (`term_calculus`, TC-1) ·
Fisher-real separation (`inflation`) · Jacob's-ladder asset base (`asset_ladder`,
ALC-1) · the-assay 5-axis verdict (`SourceOS-Linux/sourceos-spec`) ·
counter-test-gate (`Noetica`) · evidence receipts
(`SocioProphet/evidence-intake-kernel`) · GKN standing
(`SocioProphet/guild-knowledge-network`) · welfare-annealing (branch soft-ref) ·
world model (`SocioProphet/gaia-world-model`) · concept governance
(`SocioProphet/ontogenesis`).
