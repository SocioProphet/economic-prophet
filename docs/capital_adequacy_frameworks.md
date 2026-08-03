# Capital-adequacy frameworks: three contracts with teeth

Three regulatory / aggregation frameworks made **explicit** in the estate omnirisk / EP
spine, aligned to the already-merged risk kernel (`risk_measures.py`, RM-1, #43/#44) and
the Basel regulatory-capital module (`regulatory_capital.py`, #42). Grounded on the
*McKinsey Working Papers on Risk* #27 (economic capital) and #38 (the regulatory floor).

All three are **consume-not-fork**: they import the kernel by reference and never
re-implement it. They are deterministic and stdlib-only, so CI is reproducible. They are
**measurement / simulation / audit only** — no live money movement, issuance, or rails.

Each follows the estate contract pattern: **JSON Schema + Python validator with per-tooth
mutation coverage + valid/invalid fixtures + a CLI mode wired into CI (smoke + teeth) +
this doc.**

## Home rationale

All three land in **economic-prophet** in one PR. The kernel they bind to lives here
(`risk_measures.structural_transform` / `euler_allocation`; `regulatory_capital`'s IRB
`8% x RWA` and `economic_capital_credit`), so D1/D2 are *real* consumers, not stubs.
D3 extends the GBRG cross-cut allocation concept, but its computation is cross-risk-type
EC aggregation — the same additive-vs-diversified aggregation `economic_vs_regulatory`
already performs here. The GBRG hierarchy walker
(`sociosphere:gbrg/governance/omnirisk_allocation.py`, OMNI-1) is referenced by **soft
reference** (a URN on each receipt), mirroring how that walker already soft-references
this kernel — which keeps CI self-contained and the PR single.

---

## D1 — R-Cap vs E-Cap with the regulatory floor (RFL-1)

`capital_floor.py` · `schemas/capital_floor.schema.json` · CLI `--mode capital-floor`

Two capital numbers per node, in parallel: **R-Cap** (Basel `target_ratio x RWA`, IRB or
standardized) and the kernel's diversified **E-Cap** Euler contribution, plus the
**E-Cap/R-Cap ratio**. The floor is enforced:

    allocated_capital = max(economic_capital_contribution, regulatory_floor)

**Teeth**
- **REJECTED** — a node whose diversified E-Cap is *below* its regulatory minimum but whose
  `declared_allocated_capital` is that sub-floor figure. You cannot diversify under the reg
  minimum silently (the #38 footnote).
- **REJECTED** — the E-Cap/R-Cap ratio does not reconcile to its inputs; the 8% target-ratio
  assumption is absent or inconsistent with `R-Cap = target_ratio x RWA`; a non-positive floor.
- **FLAGGED** — the regulatory floor binds (E-Cap < R-Cap): allocated at the floor, divergence
  recorded. The floor did its job.
- **VERIFIED** — E-Cap >= R-Cap; ratio reconciles.

The 8% Basel ratio is asserted on the receipt (`assumptions.target_capital_ratio`,
`basel_minimum`, `asserted`). The floor is applied per node, so the portfolio allocation can
never fall below either the summed economic *or* the summed regulatory capital.

---

## D2 — Going/gone-concern confidence ladder = capital waterfall (CLD-1)

`concern_ladder.py` · `schemas/concern_ladder.schema.json` · CLI `--mode concern-ladder`

An ordered ladder of scenarios `{name, confidence_alpha, horizon_days, trigger,
absorbing_capital_layer, concern, loss_at_alpha}`:

| rung | alpha | absorbing layer | concern |
|------|-------|-----------------|---------|
| Early-Warning | 0.80 (30/250d) | hidden reserves | going |
| Severe-Stress | 0.95 (250d) | retained earnings / Tier1 (CET1) | going |
| Resolution onset | 0.9998 | Tier2 / subordinated | gone |
| Liquidation | 1.00 | senior debt | gone |

Going-concern (survive) vs gone-concern (liquidation / creditor protection) is the alpha
range, split at `going_gone_boundary_alpha`; **CoCos convert at that boundary**. The capital
stack is a contiguous `[attach, detach]` partition of the loss axis, and each layer's absorbed
loss is computed by the kernel's `structural_transform` waterfall — loss hits equity → … →
senior debt in subordination order, and the partition conserves the pool loss.

**Teeth**
- **REJECTED** — alphas not strictly increasing down the ladder (`80 < 95 < 99.98 < 100`).
- **REJECTED** — a loss booked against a *senior* layer while junior layers are unpierced (out
  of subordination order).
- **REJECTED** — a gone-concern scenario mapped to a going-concern *soft* layer (hidden reserves
  cannot absorb a liquidation loss).
- **FLAGGED** — a scenario's absorbing capital < its loss at alpha (under-capitalized); a concern
  label inconsistent with the boundary; CoCo conversion off the boundary.
- **VERIFIED** — otherwise.

---

## D3 — Aggregation-methodology taxonomy + tail-dependence guard (AGG-1)

`aggregation_method.py` · `schemas/aggregation_method.schema.json` · CLI `--mode aggregation-method`

`AggregationMethod ∈ {summation, constant_diversification, variance_covariance, copula,
full_simulation}`, carried as an **explicit, receipted governed choice** with its stated
trade-off and limitation, over per-risk-type EC (credit / market / operational):

| method | trade-off | limitation |
|--------|-----------|------------|
| summation | conservative super-additive upper bound | ignores diversification |
| constant_diversification | single flat haircut | not risk-sensitive; arbitrary |
| variance_covariance | bilateral correlation | misses non-linearity / tail dependence |
| copula | captures tail dependence | hard to validate (model risk) |
| full_simulation | full joint loss distribution | false-precision risk |

`full_simulation` is a seeded Gaussian-copula Monte-Carlo; `copula` applies the declared upper-
tail dependence `lambda`, which interpolates the aggregate from the correlation-diversified
number (`lambda=0`) toward the comonotone summation bound (`lambda=1`).

**Teeth**
- **REJECTED** — any method whose aggregate exceeds the summation upper bound (super-additive —
  impossible for a legitimate diversification claim).
- **REJECTED** — a diversifying method with no declared correlation / copula / diversification
  assumption (no silent diversification).
- **FLAGGED** — a `variance_covariance` aggregate below a tail-dependent `copula` aggregate: the
  claimed diversification vanishes in the tail (the 2008 lesson).
- **VERIFIED** — otherwise; the choice, assumption and limitation are recorded on the receipt.

---

## Receipts and references

Every contract emits an `input_hash` / `output_hash` / `receipt_hash` on the estate receipt
spine (`settlement._sha256`, FIPS SHA-256, `sha256:` prefix) and records its soft references:
the kernel modules it consumes and `sociosphere:gbrg/governance/omnirisk_allocation.py`
(OMNI-1), the cross-cut walker to which these per-node/aggregate figures are inputs.
