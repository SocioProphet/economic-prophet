# Human Economic Profit

Status: review-ready documentation and schema seed.

This directory stages the Human Economic Profit work as the value-calculus and proxy-hardening layer for `economic-prophet`.

The work aligns four frames:

1. the original Economic Profit / RAROC / FTP / economic-capital framework,
2. the Unified Value Measurement Calculus,
3. the World Economy Digital Twin bounded-corridor runtime model,
4. the SocioProphet value-measurement and reputation-exchange design.

## Core identity

```text
EP = V_plus - V_minus - EL + FCR - FC - Pi
```

The Unified Value Measurement Calculus preserves the legacy EP expression:

```text
EP_t = NOPAT_adj_t - HurdleRate_adj_t * Capital_adj_{t-1}
```

and extends it into the broader Human Economic Profit frame by requiring that every scalar EP term trace back to classed entities, value vectors, KPI leaves, knowledge quality, provenance, and corridor-level evidence custody.

## Key files in this folder

- `unified-value-class-entity-crosswalk-v0.1.md` — maps each major class/entity into EP, KPI, knowledge, NAICS/ISIC overlays, digital twin corridors, and repository object models.
- `digital-twin-alignment-v0.1.md` — aligns Human Economic Profit to the World Economy Digital Twin bounded corridor model.
- `repo-integration-plan-v0.1.md` — describes staged repository integration.

## Integration rule

Human Economic Profit is not a replacement for the existing `open_ep_framework` runtime. It is the next semantic and standards layer above it. The first implementation task is therefore documentation, schema contracts, and fixtures before runtime behavior changes.

## Immediate next work

1. Add JSON Schemas for class/entity records.
2. Add fixtures for banking, healthcare, and telecom examples.
3. Add invariant tests for additive EP, KPI tensor mapping, capital charge, and provenance completeness.
4. Map current canonical object graph entities to the Unified Value Measurement Calculus.
