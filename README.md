# economic-prophet

Open, auditable economic-profit framework and near-real-time profitability intelligence engine.

## Purpose

This repository layers the work from the economic-profit white paper into:
- canonical documentation
- machine-readable schemas
- a reference Python implementation
- synthetic examples and audit outputs

## Repository plan

### Phase 1 — framework as documentation
- `docs/whitepaper.md`
- `docs/product_spec.md`
- `docs/platform_service_boundary.md`
- `docs/integrations.md`
- `docs/associated_surplus.md`
- `schemas/`

### Phase 2 — framework as first-class modeling and simulation platform
- `src/open_ep_framework/`
- zero-EP pricing solver
- FTP engine
- expected-loss engine
- recovery surface engine
- capital charge engine
- attribution engine
- relationship portfolio effects
- relationship context outputs
- object graph runtime
- product object loaders
- instrument context outputs
- lineage-aware EP outputs
- context output schemas
- Heller mesh measurement runtime
- associated-surplus measurement runtime
- audit pack generation

## Quick start

```bash
python -m pip install -e . pytest
python -m pytest -q
python -m open_ep_framework.cli --example examples/synthetic_run.json --audit audit.json
python -m open_ep_framework.cli --mode instrument-context --example examples/synthetic_run.json --object-id instrument-loan-001 --audit instrument_context_audit.json
python -m open_ep_framework.cli --mode relationship --example examples/synthetic_relationship_runtime.json --audit relationship_audit.json
python -m open_ep_framework.cli --mode relationship-context --example examples/synthetic_relationship_runtime.json --relationship-object-id rel-synthetic-001 --audit relationship_context_audit.json
python -m open_ep_framework.cli --mode object-graph --example examples/object_graph.json --object-id instrument-loan-001 --audit object_graph_audit.json
python -m open_ep_framework.cli --mode object-context --object-id instrument-loan-001 --audit object_context_audit.json
python -m open_ep_framework.cli --mode heller-mesh --example examples/heller_mesh_measurement.json --audit heller_mesh_audit.json
python -m open_ep_framework.cli --mode associated-surplus --example examples/associated_surplus_measurement.json --audit associated_surplus_audit.json
```

The instrument CLI emits:
- FTP rate
- expected loss
- planning recovery
- market-implied recovery
- recovery wedge
- capital charge
- zero-EP break-even rate
- audit pack

The instrument-context CLI emits the same instrument calculation with joined object context: lineage, account, instrument, transaction event, collateral set, funding source, and hedge set.

The relationship CLI emits:
- weighted instrument break-even rate
- capital diversification credit
- collateral overlap charge
- utilization interaction charge
- franchise / cross-sell credit
- relationship required rate
- audit pack

The relationship-context CLI emits the same relationship calculation with relationship lineage from the object graph.

The object-graph CLI emits lineage-aware EP output for a selected object and writes the same auditable run record format. Object graph files are validated against `schemas/canonical_object.schema.json` during load.

The object-context CLI emits a joined runtime context for a selected instrument, including object lineage, account, instrument, transaction event, collateral set, funding source, and hedge set.

The Heller mesh CLI emits a validated internal measurement run for the Heller flywheel mechanics: sphere states, transfer-pricing edges, triparty faces, Micro/Credit/Reserve supply, reserve adequacy, credit utilization, gross-to-net compression, and auditable run hashes.

The associated-surplus CLI emits a validated doctrine/measurement/simulation/audit run for SocioProfit associated surplus: component scores, deductions, computed knowledge quality, gross and net associated surplus, triparty admission/release ratios, and non-goal boundary checks.

## Platform service boundary

Economic Prophet is a platform service, not an end-user application. Applications consume its measurement contracts, schemas, fixtures, CLI/API-compatible outputs, and audit packs. Platforms host it under explicit policy, authority, observability, and trust-surface boundaries.

See `docs/platform_service_boundary.md`.

## Context output schemas

The repository includes formal schemas for context-aware runtime outputs:
- `schemas/instrument_context_output.schema.json`
- `schemas/relationship_context_output.schema.json`
- `schemas/context_audit_record.schema.json`

These schemas make instrument and relationship context outputs testable as auditable product surfaces.

## Heller mesh measurement mechanics

The repository now includes a schema-first measurement boundary for the Heller flywheel economy:
- `docs/heller_mesh_measurement.md`
- `schemas/heller_mesh_measurement.schema.json`
- `examples/heller_mesh_measurement.json`
- `src/open_ep_framework/heller_mesh.py`
- `tests/test_heller_mesh.py`

This mode treats Economic Prophet as the measurement engine, Heller as the internal economic mechanics, and governed triparty netting as the release constitution. It does **not** implement live money movement, external token issuance, redemption rights, public-chain settlement, or exchange trading.

## Associated surplus doctrine

The repository now includes the SocioProfit associated-surplus doctrine:
- `docs/associated_surplus.md`
- `schemas/associated_surplus.schema.json`
- `examples/associated_surplus_measurement.json`
- `src/open_ep_framework/associated_surplus.py`
- `tests/test_associated_surplus.py`

This doctrine frames SocioProfit as profit from association, not extraction. It extends Economic Prophet from conventional economic-profit measurement toward auditable measurement of trained attention, knowledge quality, governance legitimacy, evidence reliability, coordination bandwidth, automation leverage, network surplus, extraction leakage, capture risk, uncertainty penalties, and coordination friction.

The associated-surplus boundary is doctrine, measurement, simulation, and audit only. It does **not** define live money movement, external token issuance, public-chain settlement, exchange trading, redemption rights, securities issuance, deposit-taking, or payment processing.

## Canonical object model

The runtime is moving toward a typed profitability graph:

```text
legal_entity -> line_of_business -> relationship -> account -> instrument -> transaction_event
```

Supporting objects include collateral sets, funding sources, hedge sets, scenarios, model versions, and parameter sets. See `docs/object_model.md`, `schemas/canonical_object.schema.json`, `schemas/lineage_ep_output.schema.json`, `examples/canonical_object.json`, `examples/object_graph.json`, and `src/open_ep_framework/object_graph.py`.

## Product object schemas and loaders

The repository includes first-pass product object contracts and loaders for:
- account
- instrument
- transaction event
- collateral set
- funding source
- hedge set

Each schema has a matching synthetic fixture under `examples/`, a validation test under `tests/test_product_object_schemas.py`, and loader/join coverage under `tests/test_product_object_loaders.py`.

## Relationship portfolio effects

The relationship engine demonstrates why relationship profitability is not a blind sum of transactions. It decomposes relationship required rate into:
- weighted instrument break-even rate
- capital diversification credit
- collateral overlap charge
- utilization interaction charge
- franchise / cross-sell credit

See `examples/synthetic_relationship_runtime.json`, `schemas/relationship.schema.json`, and `tests/test_relationship_cli.py`.

## Ecosystem integration

This reference implementation is designed to integrate with:
- **Gaia** for macro regime state and scenario conditioning
- **Ontogenesis** for canonical ontology, lineage, and semantic constraints
- **TritFabric** for typed event transport and simulation orchestration

## First artifacts to land

- integrated white paper draft
- product specification v1
- schema pack v1
- reference implementation skeleton v1
- synthetic audit example
