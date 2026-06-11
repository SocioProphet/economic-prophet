# ValueFlows × MPCC × Economic Prophet × Energy Alignment

## Purpose

This note aligns Economic Prophet with ValueFlows, `mdheller/profit-mpcc`, Heller mesh measurement, and energy-flow semantics. The goal is to make Economic Prophet a measurement runtime for value movement, value storage, exchange, work, energy, commitments, proof, and profitability without collapsing those concepts into one overloaded object model.

## Pressure-test result

Economic Prophet is directionally aligned with ValueFlows, but the next layer must explicitly model **energy as value in motion and value in storage**.

A near-real-time profitability engine should not only ask:

```text
What is the economic profit of this instrument or relationship?
```

It should also ask:

```text
What flows of work, liquidity, collateral, computation, knowledge, risk, and energy created or consumed that value?
Where is the value stored?
Who can exchange, reserve, commit, transfer, or release it?
Which event/process/commitment changed its state?
```

## Layer separation

The clean separation is:

```text
ValueFlows       = economic graph grammar
Energy semantics = stored capacity, useful work, conversion, dissipation, scarcity, transfer
MPCC             = provenance, authority, causality, policy, and effect-control grammar
Economic Prophet = profitability measurement and audit runtime
Heller mesh      = specialized internal economic mechanics projection
```

Do not collapse these layers into one schema. Each layer should stay independently inspectable and composable.

## ValueFlows mapping

ValueFlows describes three connected levels:

```text
Knowledge -> Plan -> Observation
```

Knowledge contains resource specifications, recipe flows, and recipe processes. Plan contains intents, commitments, planned processes, and exchange agreements. Observation contains economic resources and economic events.

Economic Prophet maps these concepts as follows:

| ValueFlows concept | Economic Prophet mapping |
| --- | --- |
| Economic Agent | legal entity, LOB, customer, counterparty, desk, treasury, service provider |
| Agent Relationship | customer relationship, counterparty relationship, affiliate, guarantor, custodian |
| Economic Resource | cash, loan, deposit, collateral, funding source, hedge, liquidity, capital, compute, work capacity, knowledge asset, energy reserve |
| Resource Specification | account/instrument/collateral/funding/hedge/energy-resource schemas |
| Economic Event | transaction event, draw, payment, fee, mark, pledge, hedge settlement, capital allocation, FTP charge, work contribution, compute use, energy transfer |
| Process | origination, pricing, funding, expected-loss update, recovery update, capital allocation, attribution run, conversion process, production process |
| Commitment | undrawn facility, planned draw, funding promise, expected recovery, planned hedge, credit limit, promised work, reserved compute, reserved energy |
| Intent | pricing intent, relationship strategy, risk appetite, target hurdle, planned exchange, planned release |
| Recipe / Recipe Flow | FTP recipe, zero-EP pricing recipe, expected-loss recipe, recovery recipe, capital-charge recipe, transfer-price recipe, energy-conversion recipe |
| Exchange Agreement | loan agreement, deposit agreement, derivative agreement, collateral agreement, internal transfer-pricing agreement, service exchange, energy exchange |

## Energy as value store and exchange

Energy should be treated as a first-class economic concept, but not as a magical universal token. In the runtime, energy means measurable capacity to do useful work or cause state transition.

Energy-like stores include:

```text
cash liquidity
collateral capacity
capital headroom
compute capacity
human effort / labor capacity
knowledge quality
reputation / trust stock
reserve capacity
service capacity
Heller Micro/Credit/Reserve supply
```

Energy-like flows include:

```text
payments
loan draws
collateral pledges
hedge settlements
work contributions
compute usage
knowledge improvements
risk transfers
reserve releases
credit issuance or settlement
refunds, slashes, reversals, revocations
```

The important distinction is:

```text
stock  = stored capacity / resource state
flow   = event-mediated change in resource state
process = transformation function
exchange = agent-to-agent transfer or reciprocal flow
commitment = planned future event
recipe = repeatable process specification
```

## Store / flow / exchange invariants

Economic Prophet should enforce the following invariants as the runtime matures:

1. **Stocks change only through events.**
   A resource balance, collateral value, reserve stock, or Heller supply should not change without an economic event.

2. **Events must identify provider and receiver when value transfers.**
   Provider/receiver can be external agents, internal desks, treasury, reserve pools, or system processes.

3. **Processes transform resources but do not erase provenance.**
   A process may convert input resources into output resources, but the output must link backward to inputs, process, recipe, and event evidence.

4. **Commitments represent planned energy/value movement.**
   A credit line, planned hedge, promised service, reserved compute, or reserved energy is a planned event that has not happened yet.

5. **Exchange requires reciprocal or policy-recognized value movement.**
   An exchange may be direct, netted, delayed, triparty-cleared, policy-gated, or internal-transfer-priced.

6. **Dissipation and loss are first-class.**
   Work can decay, collateral can be impaired, reserves can be consumed, knowledge can stale, operational effort can be wasted, and credit exposure can produce loss.

7. **Measurement and transfer are separate.**
   Measuring value-energy does not imply external token issuance, redemption, or public settlement.

## MPCC mapping

`profit-mpcc` defines the primitive object as a typed event in a partially ordered event graph. Economic Prophet should reuse this event-envelope discipline for all consequential economic events.

Required MPCC-aligned envelope concepts include:

```text
event_id
actor_id
authority_context
workspace_id
branch_id
visibility_scope
wall_time
logical_time
causal_parents
trace_context
modality
raw_payload
canonical_payload
requested_effects
approved_effects
actual_effects
provenance_links
policy_labels
risk_labels
evaluation_metrics
```

## Combined event shape

The target combined event shape is:

```text
EconomicProphetEvent =
  MPCCEventEnvelope
  + ValueFlowsEconomicEventPayload
  + EnergyStateTransition
  + MeasurementOutputReference
```

Where:

```text
MPCCEventEnvelope
  = authority, causality, visibility, provenance, policy, risk, effects

ValueFlowsEconomicEventPayload
  = provider, receiver, action, resource, quantity, process, commitment, exchange

EnergyStateTransition
  = stock_before, flow_quantity, transformation, stock_after, dissipation/loss, reserve/release state

MeasurementOutputReference
  = EP delta, FTP delta, EL delta, capital delta, recovery delta, attribution, audit hash
```

## Example: loan draw as value/energy flow

```text
ValueFlows:
  Agent: borrower, bank
  Economic Event: draw / transfer
  Resource: cash and loan exposure
  Process: utilization / funding / risk update
  Commitment: revolver commitment partially fulfilled

Energy semantics:
  Stored capacity before: undrawn commitment + liquidity reserve
  Flow: cash transferred to borrower; credit exposure increases
  Dissipation/risk: expected loss, capital charge, liquidity cost
  Store after: lower undrawn commitment, higher EAD, changed liquidity/capital state

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

## Example: work contribution as value/energy flow

```text
ValueFlows:
  Agent: contributor
  Economic Event: work
  Resource: work effort, knowledge artifact, service output
  Process: production / review / publication
  Commitment: promised contribution or task assignment

Energy semantics:
  Stored capacity before: labor capacity + knowledge base
  Flow: effort converted into artifact or service
  Dissipation/risk: rework, review failure, quality loss, contradiction, policy block
  Store after: higher knowledge quality, reputation, service capacity, or discarded residual

MPCC:
  event envelope preserves authority, claims, provenance, approval, actual effect

Economic Prophet:
  delta_EP, productivity effect, cost, risk charge, attribution, audit hash
```

## Example: Heller mesh as internal energy/value mechanics

The Heller mesh measurement layer already defines internal sphere states, transfer-pricing edges, triparty faces, Micro/Credit/Reserve Heller supplies, reserve adequacy, credit utilization, gross-to-net compression, release correctness, and proof lineage.

The energy interpretation is:

| Heller concept | Energy/value interpretation | ValueFlows mapping | Economic Prophet mapping |
| --- | --- | --- | --- |
| Micro-Heller | fast-decaying utility/work/participation energy | Economic Resource + Economic Event | internal contribution measurement |
| Credit-Heller | staked obligation / medium-duration potential energy | Commitment / Exchange Agreement | exposure, collateral, capital, slashing risk |
| Reserve-Heller | long-duration collateral energy store | Economic Resource / reserve collateral | reserve adequacy / credit limit |
| Sphere momentum | accumulated directional productive energy | Process cluster state | EP and knowledge momentum |
| Transfer-price edge | energy/value transfer between spheres | Economic Event / Process edge | transfer price / internal FTP-like result |
| Triparty face | constitutionally gated exchange release | Exchange Agreement + Commitments | release/admission/residual measurement |

## Design guardrails

1. Do not replace Economic Prophet's current object graph immediately.
2. Do not force banking-specific concepts into ValueFlows core classes.
3. Do not treat energy as external token issuance.
4. Do not make Heller externally transferable in this alignment layer.
5. Do not treat MPCC as an economic ontology; it is the provenance/control envelope.
6. Keep stocks, flows, commitments, recipes, events, processes, and exchanges separately modeled.
7. Preserve auditability as a hard invariant.
8. Preserve the distinction between measurement, settlement, transfer, and legal entitlement.

## Near-term implementation sequence

### PR A: Alignment docs

This document.

### PR B: First ValueFlows-compatible schemas

Add:

- `schemas/economic_agent.schema.json`
- `schemas/economic_resource.schema.json`
- `schemas/economic_event.schema.json`
- `schemas/energy_state_transition.schema.json`
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
- stock/flow/state-transition tests

### PR D: MPCC adapter

Add:

- `src/open_ep_framework/mpcc_adapter.py`
- wrapper from Economic Prophet economic events into MPCC event envelopes
- policy/effect/provenance validation tests

### PR E: Heller crosswalk hardening

Add:

- Heller sphere/edge/triparty examples as ValueFlows economic events and exchange agreements
- energy state transition examples for Micro/Credit/Reserve Heller flows
- tests proving Heller measurement remains internal, auditable, and non-transferable

## Acceptance criteria

The alignment is acceptable when Economic Prophet can answer:

1. Which agent caused or participated in the economic event?
2. Which resource changed?
3. What stock existed before the event?
4. What flow or transformation happened?
5. What stock exists after the event?
6. Which process consumed or produced the resource?
7. Which commitment or agreement did the event fulfill?
8. Which recipe/model generated the measurement?
9. What authority, policy, and provenance envelope authorized the event?
10. What EP/FTP/EL/capital/recovery/attribution change followed?
11. Can the system traverse forward and backward through all of the above?

## Strategic conclusion

Economic Prophet should become a ValueFlows-compatible profitability and energy-flow graph for financial institutions, Heller-like internal economic systems, and eventually broader economic coordination surfaces.

ValueFlows supplies the economic graph grammar. Energy semantics clarify value storage, work, conversion, scarcity, transfer, and dissipation. MPCC supplies the event-control and provenance grammar. Economic Prophet supplies measurement. Heller supplies a specialized internal-economic mechanics projection.
