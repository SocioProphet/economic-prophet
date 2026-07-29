# Integration roadmap: Gaia, Ontogenesis, and TritFabric

This document explains how the Open Auditable Economic Profit Framework layers into the broader SocioProphet ecosystem.

## Gaia integration

Gaia should act as the world-model and scenario context layer.

Gaia supplies:
- macro regime state
- sector and geography tags
- scenario overlays
- policy regime metadata
- synthetic or observed context for stressed and unstressed runs

The profitability engine consumes Gaia outputs to condition:
- PD nowcasts
- recovery surfaces
- liquidity and funding stress surcharges
- capital shadow prices
- relationship and portfolio scenario attribution

## Ontogenesis integration

Ontogenesis should act as the ontology and typed semantic layer.

Ontogenesis supplies:
- canonical object identities
- type relations among entity, relationship, account, instrument, transaction, collateral, funding source, and hedge sets
- lineage and mapping rules
- semantic constraints for aggregation and reconciliation

The profitability engine consumes Ontogenesis outputs to make the runtime object graph auditable and stable.

## TritFabric integration

TritFabric should act as the transport/orchestration fabric.

TritFabric supplies:
- event transport
- typed request / response movement
- streaming updates for market state and balance sheet events
- simulation job orchestration
- audit and report fanout

The profitability engine publishes and consumes typed events over TritFabric for:
- market updates
- FTP refreshes
- expected-loss refreshes
- recovery-state updates
- zero-EP pricing requests
- attribution runs
- audit-pack emission

## First-class modeling platform target

1. Ontogenesis provides canonical types and lineage.
2. Gaia provides macro regime and scenario state.
3. TritFabric moves events and orchestrates runs.
4. Economic Prophet computes profitability, pricing, capital charges, attribution, and audits.
