# Platform Service Boundary

## Principle

Economic Prophet is a platform service, not an end-user application.

Applications consume services. Platforms host services. Services expose stable contracts, auditable behavior, policy boundaries, schemas, fixtures, and replayable outputs. Applications compose those services into user-facing workflows, dashboards, decisions, and domain-specific experiences.

This distinction is a hard architecture boundary for SocioProphet.

## Why this matters

If Economic Prophet is treated as an application, it will drift toward one-off workflows, UI-specific assumptions, hidden state, and brittle integrations. If it is treated as a platform service, it remains reusable by many applications while preserving measurement integrity.

Economic Prophet should therefore provide:

- canonical economic-profit measurement contracts;
- associated-surplus measurement contracts;
- Heller mesh measurement contracts;
- object graph and lineage contracts;
- deterministic runtimes;
- schemas and fixtures;
- CLI and service-compatible outputs;
- audit packs;
- explicit non-goals and safety boundaries.

Applications may provide:

- dashboards;
- decision cards;
- community workspaces;
- admin workflows;
- model-assisted explanation;
- scenario-building UI;
- governance review UI;
- reporting packs;
- marketplace/media/AppStore projections;
- domain-specific user experiences.

Applications must not become sovereign sources of truth over measurement state.

## Service versus application

| Layer | Responsibility | Example |
| --- | --- | --- |
| Platform | Hosts services, policy, identity, evidence, transport, deployment, observability | SocioProphet platform, SourceOS, TritFabric, policy fabric |
| Platform service | Exposes stable reusable capabilities through schemas, APIs, CLI, events, and audit outputs | Economic Prophet, Heller mesh measurement, associated surplus measurement |
| Application | Composes services into user-facing workflows | Noetica, SocioSphere dashboard, community valuation UI, governance console |
| Projection | A domain-specific view of service state | decision card, audit packet view, relationship-profitability card, associated-surplus card |

## Economic Prophet service boundary

Economic Prophet owns measurement logic and evidence output. It should not own all user workflows.

Economic Prophet should answer questions such as:

- What is the economic-profit result for this instrument or relationship?
- What is the lineage-aware profitability context for this object?
- What is the Heller mesh measurement summary for this synthetic or governed run?
- What is the associated-surplus measurement summary for this community/sphere run?
- What assumptions, limitations, schemas, inputs, outputs, and hashes support the result?

Economic Prophet should not decide alone:

- who is allowed to see a person-bound output;
- whether a community accepts a governance decision;
- whether a release becomes legally binding;
- whether money moves;
- whether an external token exists;
- whether a user interface should promote a result;
- whether a model explanation is adequate for a specific audience.

Those are platform and application responsibilities mediated by policy, consent, governance, and jurisdiction-specific review.

## Contract posture

Every Economic Prophet service surface should be contract-first.

Minimum service contract:

```text
input schema
runtime function
fixture
validation test
deterministic summary test
CLI or API mode
audit output
non-goal boundary, when relevant
```

The associated-surplus chain now follows this pattern:

```text
docs/associated_surplus.md
schemas/associated_surplus.schema.json
examples/associated_surplus_measurement.json
src/open_ep_framework/associated_surplus.py
tests/test_associated_surplus.py
tests/test_associated_surplus_cli.py
python -m open_ep_framework.cli --mode associated-surplus ...
```

## Application consumption pattern

Applications should consume Economic Prophet by contract, not by reaching into internal implementation details.

Preferred consumption forms:

1. CLI invocation for local/demo mode.
2. API wrapper for service mode.
3. Event or carrier envelope for platform mode.
4. Audit-pack ingestion for evidence/replay mode.
5. Schema imports for UI validation and form generation.

A consuming application should bind to:

- schema version;
- framework version;
- run ID;
- scenario;
- input hash;
- output hash;
- evidence refs;
- replay plan;
- policy/consent refs where applicable.

It should not bind to incidental Python internals unless it is a test or internal service adapter.

## Platform hosting pattern

The platform hosts Economic Prophet as a service with explicit authority.

A platform deployment should declare:

```yaml
service: economic-prophet
kind: platform_service
can_read:
  - measurement_fixtures
  - scenario_inputs
  - object_graphs
  - schemas
can_write:
  - audit_packs
  - measurement_outputs
cannot_write:
  - identity_roots
  - consent_grants
  - external_payment_state
  - token_supply
requires_policy_admission: true
non_goals:
  - live_money_movement
  - external_token_issuance
  - public_chain_settlement
  - exchange_trading
  - redemption_rights
```

This service declaration should eventually become a `TRUST_SURFACE.yaml` or equivalent platform authority manifest.

## Projection rule

Applications may project Economic Prophet outputs, but projection must preserve provenance.

A projection must carry:

```text
source_run_id
source_scenario
source_framework_version
source_input_hash
source_output_hash
source_schema_ref
source_audit_ref
projection_timestamp
projection_policy_ref
```

A projection that drops provenance is not a governed SocioProphet application surface.

## Associated surplus as service output

Associated surplus should be exposed as a service output, not as a social-media metric or engagement score.

The service computes or validates:

- component scores;
- deductions;
- knowledge quality;
- gross associated surplus;
- net associated surplus;
- triparty admission and release ratios;
- evidence refs;
- non-goal boundary compliance.

Applications may render those into:

- community decision cards;
- governance reviews;
- education loop dashboards;
- federation health reports;
- anti-capture diagnostics;
- associated-surplus trend views.

But applications must not convert associated surplus into a hidden reputation score, behavioral targeting metric, or extractive ranking primitive.

## Strategic rule

Platform services create durable, governed capability. Applications create situated human experience. The system fails if applications become ungoverned sources of truth, and it also fails if platform services hard-code all experience.

Therefore:

```text
services measure, validate, govern, emit evidence, and preserve replay.
applications compose, explain, deliberate, and act through policy.
platforms host, secure, route, observe, and enforce boundaries.
```

Economic Prophet remains a platform service. SocioProphet applications consume it.
