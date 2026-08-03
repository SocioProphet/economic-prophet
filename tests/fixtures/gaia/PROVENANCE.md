# Vendored GAIA economy schemas (test fixtures only)

These two JSON Schemas are **consumed by reference, not forked**. They are gaia-owned and
authoritative in `SocioProphet/gaia-world-model`. Copies are vendored here **only** so the
welfare-annealing test suite can validate the manifests this module emits against the exact
contract, hermetically (no network, no sibling checkout).

- `value_flow_binding.v1.schema.json`
- `twin_scale_transfer.v1.schema.json`

Source: `SocioProphet/gaia-world-model@2abb7a2afd66835879d13cff3e43e33b27c1fd78`
(branch `feat/value-flow-subsystem`, path `schemas/economy/`).

If the gaia contract revises these schemas, re-vendor from the pinned ref. Do not edit these
copies by hand.
