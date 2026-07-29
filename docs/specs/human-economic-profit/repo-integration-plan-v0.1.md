# Human Economic Profit — Repository Integration Plan v0.1

## Purpose

This plan stages the Human Economic Profit manuscript and companion specification bundle into `mdheller/economic-prophet` without disturbing the existing reference implementation. The first PR should be documentation and schema contracts only.

## Target path

```text
docs/specs/human-economic-profit/
```

## First PR scope

Include:

1. Directory README.
2. Schema contracts for the first implementation records.
3. Integration plan.

Do not include implementation code in the first PR.

## Follow-up import

The full local artifact bundle contains:

- `human_economic_profit_running_draft_v0_16.md`
- `human_economic_profit_spec_bundle_v0_1.md`
- `drive_capture_manifest_v0_1.md`
- schema files
- repo bundle README

Because the connector writes file-by-file, the safest next step is either a local Git push of the full bundle or a second PR that adds the large Markdown artifacts after this seed PR is reviewed.

## Recommended final layout

```text
docs/specs/human-economic-profit/
  README.md
  human-economic-profit-running-draft.md
  human-economic-profit-spec-bundle.md
  drive-capture-manifest.md
  repo-integration-plan-v0.1.md
  schemas/
    README.md
    event.schema.json
    ep-record.schema.json
    reputation-event.schema.json
    replay-row.schema.json
    heller-balance.schema.json
    civic-asset.schema.json
```

## Schema follow-up tests

Create tests that validate examples against:

- `event.schema.json`
- `ep-record.schema.json`
- `reputation-event.schema.json`
- `replay-row.schema.json`
- `heller-balance.schema.json`
- `civic-asset.schema.json`

## Invariant tests to add next

1. EP identity arithmetic must reconcile exactly.
2. Civic asset used capacity must not exceed capacity.
3. Heller closing balance must reconcile from opening balance, demurrage, mint, spend, and burn.
4. Replay row lower bound must not exceed upper bound.
5. Verifier credibility must remain in `[0,1]`.
6. Reputation half-life must be positive.

## Follow-up issues

### Issue: Add fixtures and schema validation tests

Add one positive fixture and one negative fixture for each schema.

### Issue: Add EP simulation harness

Implement a minimal harness for EP identity, expected loss, capital reservation, and liquidity costs.

### Issue: Add Heller demurrage simulation

Implement balance evolution under demurrage and velocity controls.

### Issue: Add historical replay row examples

Create Rome and founding-era replay-row fixtures with evidence-grade metadata.

### Issue: Add full manuscript artifact

Land the current running manuscript after review of the seed schema PR.

## Acceptance criteria for seed PR

- Markdown renders.
- JSON Schemas parse.
- No runtime code is changed.
- Existing tests should not be affected.
