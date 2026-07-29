# ValueFlows × MPCC × Economic Prophet Alignment

## Purpose

This note aligns Economic Prophet with ValueFlows and `mdheller/profit-mpcc` before we add more runtime code. The goal is to avoid building a banking-only object model that cannot represent broader value-flow semantics, provenance, causality, policy, and effect lineage.

## Pressure-test result

The current Economic Prophet runtime is directionally aligned with ValueFlows, but incomplete.

Economic Prophet already has:

- canonical object graph
- product object schemas
- economic/profit calculations
- instrument and relationship context outputs
- audit packs
- Heller mesh measurement mechanics

But it does not yet fully expose:

- ValueFlows-style Economic Agents
- Economic Resources
- Economic Events with action semantics
- Processes
- Commitments
- Recipes
- Exchange Agreements
- MPCC-style event envelopes for authority, causality, visibility, requested/approved/actual effects, and policy/risk labels

## Layer separation

The clean separation is:

```text
ValueFlows = economic grammar
MPCC       = provenance, authority, causality, policy, and event-control grammar
Economic Prophet = profitability measurement and audit runtime
Heller mesh = specialized internal economic mechanics projection
```

Do not collapse these layers into one schema. Each layer should stay independently inspectable and composable.

## ValueFlows mapping

The uploaded ValueFlows material describes three connected levels:

```text
Knowledge -> Plan -> Observation
```

Knowledge contains resource specifications, recipe flows, and recipe processes. Plan contains intents, commitments, planned processes, and exchange agreements. Observation contains economic resources and economic events.

Economic Prophet should map these as follows:

| ValueFlows concept | Economic Prophet mapping |
| --- | --- |
| Economic Agent | legal entity, LOB, customer, counterparty, desk, treasury, service provider |
| Agent Relationship | customer relationship, counterparty relationship, affiliate, guarantor, custodian |
| Economic Resource | cash, loan, deposit, collateral, funding source, hedge, liquidity, capital, service entitlement |
| Resource Specification | account/instrument/collateral/funding/hedge schemas |
| Economic Event | transaction event, draw, payment, fee, mark, pledge, hedge settlement, capital allocation, FTP charge |
| Process | origination, pricing, funding, expected-loss update, recovery update, capital allocation, attribution run |
| Commitment | undrawn facility, planned draw, funding promise, expected recovery, planned hedge, credit limit |
| Intent | pricing intent, relationship strategy, risk appetite, target hurdle |
| Recipe / Recipe Flow | FTP recipe, zero-EP pricing recipe, expected-loss recipe, recovery recipe, capital-charge recipe |
| Exchange Agreement | loan agreement, deposit agreement, derivative agreement, collateral agreement, internal transfer-pricing agreement |

## MPCC mapping

`profit-mpcc` defines the primitive object as a typed event in a partially ordered event graph. Its canonical event object includes:

- `event_id`
- `actor_id`
- `authority_context`
- `workspace_id`
- `branch_id`
- `visibility_scope`
- `wall_time`
- `logical_time`
- `causal_parents`
- `trace_context`
- `modality`
- `raw_payload`
- `canonical_payload`
- `speech_act`
- `claims`
- `entities`
- `topics`
- `requested_effects`
- `approved_effects`
- `actual_effects`
- `provenance_links`
- `policy_labels`
- `risk_labels`
- `evaluation_metrics`

Economic Prophet should reuse this event-envelope discipline for all consequential economic events.

## Combined event shape

The target combined event shape is:

```text
EconomicProphetEvent =
  MPCCEventEnvelope
  + ValueFlowsEconomicEventPayload
  + MeasurementOutputReference
```

Where:

```text
MPCCEventEnvelope
  = authority, causality, visibility, provenance, policy, risk, effects

ValueFlowsEconomicEventPayload
  = provider, receiver, action, resource, quantity, process, commitment, exchange

MeasurementOutputReference
  = EP delta, FTP delta, EL delta, capital delta, attribution, audit hash
```

## Example: loan draw

```text
ValueFlows:
  Agent: borrower, bank
  Economic Event: draw / transfer
  Resource: cash and loan exposure
  Process: utilization / funding / risk update
  Commitment: revolver commitment partially fulfilled

MPCC:
  event_id
  actor_id
  authority_context
  causal_parents
  requested_effects
  approved_effects
  actual_effects
  policy_labels
  provenance_links

Economic Prophet:
  delta_balance
  delta_EAD
  delta_FTP
  delta_EL
  delta_capital_charge
  delta_EP
  attribution
  audit hash
```

## Heller mesh crosswalk

The Heller mesh measurement layer already extends Economic Prophet with internal sphere states, transfer-pricing edges, triparty faces, Micro/Credit/Reserve Heller supplies, reserve adequacy, credit utilization, gross-to-net compression, release correctness, and proof lineage.

The Heller layer should be treated as a specialized projection over ValueFlows + MPCC + Economic Prophet:

| Heller concept | ValueFlows mapping | MPCC mapping | Economic Prophet mapping |
| --- | --- | --- | --- |
| Sphere | Agent / Process cluster | workspace / branch context | LOB / sphere object |
| Transfer-pricing edge | Economic Event / Process edge | causal effect | FTP / transfer-price result |
| Triparty face | Exchange Agreement | approved/released effects | release/admission measurement |
| Micro-Heller | internal resource / utility unit | policy-constrained event payload | internal measurement only |
| Credit-Heller | commitment / staked obligation | effect with slashing/release state | exposure / collateral / capital measurement |
| Reserve-Heller | economic resource / collateral | proof-linked reserve state | collateral / reserve adequacy |

## Design guardrails

1. Do not replace Economic Prophet's current object graph immediately.
2. Do not force banking-specific concepts into ValueFlows core classes.
3. Do not make Heller externally transferable in this alignment layer.
4. Do not treat MPCC as an economic ontology; it is the provenance/control envelope.
5. Keep recipes, commitments, and events separately modeled.
6. Preserve auditability as a hard invariant.

## Near-term implementation sequence

### PR A: Alignment docs

This document.

### PR B: First ValueFlows-compatible schemas

Add:

- `schemas/economic_agent.schema.json`
- `schemas/economic_resource.schema.json`
- `schemas/economic_event.schema.json`
- `schemas/process.schema.json`
- `schemas/commitment.schema.json`
- `schemas/resource_specification.schema.json`
- `schemas/exchange_agreement.schema.json`
- `schemas/mpcc_event_envelope.schema.json`

### PR C: Value-flow graph runtime

Add:

- `src/open_ep_framework/value_flow_graph.py`
- forward traversal tests
- backward traversal tests
- resource continuity tests

### PR D: MPCC adapter

Add:

- `src/open_ep_framework/mpcc_adapter.py`
- wrapper from Economic Prophet economic events into MPCC event envelopes
- policy/effect/provenance validation tests

### PR E: Heller crosswalk hardening

Add:

- Heller sphere/edge/triparty examples as ValueFlows economic events and exchange agreements
- tests proving Heller measurement remains internal, auditable, and non-transferable

## Acceptance criteria

The alignment is acceptable when Economic Prophet can answer:

1. Which agent caused or participated in the economic event?
2. Which resource changed?
3. Which process consumed or produced the resource?
4. Which commitment or agreement did the event fulfill?
5. Which recipe/model generated the measurement?
6. What authority, policy, and provenance envelope authorized the event?
7. What EP/FTP/EL/capital/recovery/attribution change followed?
8. Can the system traverse forward and backward through all of the above?

## Strategic conclusion

Economic Prophet should become a ValueFlows-compatible profitability graph for financial institutions and Heller-like internal economic systems. ValueFlows supplies the economic graph grammar. MPCC supplies the event-control and provenance grammar. Economic Prophet supplies measurement. Heller supplies a specialized internal-economic mechanics projection.
