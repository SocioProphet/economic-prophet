# Upward bindings — IRB-1 / RVO-1

Per the estate bind-upward discipline (`feedback_bind_upward_worldmodel_ontogenesis`),
the two contracts declare where they sit in the world model and route their new concepts
into governed ontology. Both bindings are **soft-ref only** — nothing in the referenced
repos is edited or vendored here.

## Binding 1 — frames/markets are value-flow frames in the world-economic-twin

The RVO-1 **price frames** (market / venue / currency) are **value-flow frames** in the
GAIA world-economic-twin, and the RVO-1 **causal order composes with the twin-scale
value transfers**.

- **Upward target:** `SocioProphet/gaia-world-model#41` — the economic spine becomes the
  **value-flow subsystem of the world model** (landed in GAIA per **ADR-0002**; GAIA owns
  world-model layer/composition contracts). The established GAIA↔EP soft-ref surface is
  `schemas/economy/economy_observation.v1` (`economy_observation`).
- **Composition:** each RVO-1 `Observation` is a frame-local value event; the vector-clock
  partial order over observations is the causal order in which the world model's
  twin-scale value transfers become globally (eventually) consistent. A GAIA
  `economy_observation` in a given frame maps 1:1 to an RVO-1 per-frame observation; the
  RVO-1 converged view is the value-flow subsystem's eventually-consistent global state.
  IRB-1 supplies the same subsystem's **cross-frame comparability layer**: only the
  dimensionless idiosyncratic differential crosses a frame boundary, never an absolute
  level.
- **Consume-not-fork:** GAIA and economic-prophet kernels are referenced by pinned
  soft-ref; this PR touches neither.

## Binding 2 — the new concepts become governed Systema Concept Entries

The new concepts are routed into **ontogenesis** as governed **Systema Concept Entries**
(SourceAnchored, provenance-classed, versioned, receipted).

- **Upward target:** `SocioProphet/ontogenesis` Systema Concept Entry model (spec
  `docs/specs/systema-concept-entry-v0.md`, parent `SocioProphet/ontogenesis#63`; shape
  `shapes/systema_concept_entry.shacl.ttl`; context
  `contexts/systema-concept.context.jsonld`).
- **Routed concepts:** `baseline_index`, `idiosyncratic_differential`,
  `systematic_idiosyncratic_decomposition`, `price_frame`,
  `eventual_consistency_value_order`, `causal_partial_value_order`.
- **Where:** [`docs/concepts/systema_concept_entries.jsonld`](../concepts/systema_concept_entries.jsonld)
  holds the six `ConceptEntry` records in the ontogenesis shape, each source-anchored to
  the concrete IRB-1 / RVO-1 implementation surface in this repo, with an operational
  definition, allowed/forbidden uses, an evidence requirement, and a v0.1 revision. The
  authoritative promotion of these entries **into the ontogenesis ledger** is a follow-up
  PR in that repo (see below) — consistent with consume-by-reference: economic-prophet
  declares the source-anchored candidates; ontogenesis governs promotion.

## Follow-ups for @mdheller

1. **ontogenesis:** open a PR landing the six concept entries from
   `docs/concepts/systema_concept_entries.jsonld` into the Systema ledger
   (`ledger/ledger.csv` + `examples/systema/`), running the SHACL shape
   (`shapes/systema_concept_entry.shacl.ttl`) so promotion is receipted. `sourceAnchor`
   already points at `SocioProphet/economic-prophet:src/open_ep_framework/{benchmarking,value_ordering}`.
2. **gaia-world-model:** wire the RVO-1 per-frame `Observation` ↔ `economy_observation.v1`
   crosswalk on issue #41's value-flow subsystem surface (pinned soft-ref to
   `schemas/value_frame_observation.schema.json`), so the twin-scale value transfers read
   the RVO-1 converged view as the value-flow global state.
3. **receipt spine:** register the RVO-1 hash-chain (`chain_receipt`) as a value-event
   clock producer against the canonical estate receipt-spine surface, so RVO-1 receipts
   join the hash-chained audit spine rather than a module-local chain.
