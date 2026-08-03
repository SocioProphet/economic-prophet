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
python -m open_ep_framework.cli --mode settlement --example examples/conservation_settlement_balanced.json --audit settlement_audit.json
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

## Risk-adjusted profit / RAROC contract (RAP-1)

The repository includes a risk-adjusted return contract that computes economic
profit and RAROC on top of the residual-value + conservation engine:
- model: `EP = revenue - expected_loss - expense - funding_costs + funding_credits - taxes - capital_charge`;
  `CapitalCharge = HurdleRate * EconomicCapital`; `RAROC = RiskAdjustedReturn / EconomicCapital`
  (compared to the hurdle, RORAC).
- `schemas/risk_adjusted_profit.schema.json`
- `examples/risk_adjusted_profit_economic.json` (decomposed org cut),
  `examples/risk_adjusted_profit_epistemic.json` (dual scoring),
  `examples/risk_adjusted_profit_nonreconciling.invalid.json`
- `src/open_ep_framework/risk_adjusted_profit.py` (RAP-1 contract)
- `src/open_ep_framework/risk_measures.py` (RM-1 unified risk-measure family)
- `tests/test_risk_adjusted_profit.py`, `tests/test_risk_measures.py`

Run it:

```bash
python -m open_ep_framework.cli --mode risk-adjusted-profit --example examples/risk_adjusted_profit_economic.json --audit rap_audit.json
```

It consumes, and does not reinvent:
- the EP identity (`uvmc.reconcile_ep_components`),
- the IC-1 conservation law and receipt spine (`settlement`, economic-prophet#39) —
  org/entity decomposition is reconciled AS a conservation settlement (parent EP is the
  inflow, each child EP an outflow); a cut whose children do not sum to the parent is
  rejected.

**Unified risk-measure family (RM-1).** Every measure is derived from one interface,
`risk(F, kernel, reference, horizon, ...)`, over the same fitted/simulated loss
distribution `F`:
- reward-to-risk: Sharpe -> Sortino (downside deviation about a MAR) -> Kappa_n
  (`(E[R]-tau)/LPM_n(tau)^(1/n)`; `n=0` shortfall-prob, `n=1` Omega, `n=2` Sortino, `n>2` extreme-averse);
- tail/coherent: VaR (non-coherent, flagged), Expected Shortfall / CVaR (coherent),
  spectral (coherent iff the spectrum is non-increasing; ES is the flat-tail spectrum).
  EconomicCapital for RAROC defaults to a coherent measure.
- `F` builders for two asset classes over the same interface: credit (PD·LGD·EAD under a
  one-factor common shock) and equity/market (fat-tailed Student-t returns with beta,
  drawdown). Risk is a horizon term structure (`risk_term_structure`) plus an LCR-style
  `largest_cumulative_gap`, not a scalar.
- structure/issuance: `structural_transform(F_pool, attach, detach)` derives a
  securitization tranche (equity = first-loss residual claim) from the pool; contiguous
  tranche ELs reconcile to the pool EL; `detach <= attach` is rejected.
- coherent allocation: `euler_allocation(...)` returns marginal (Euler) component
  capital; for a coherent measure the contributions sum to the total (the same IC-1
  conservation), which lets EconomicCapital aggregate up and allocate down a hierarchy.

**Calculus over (value x time) (TC-1).** The risk kernel is a calculus on two axes.
Measures and distributional moments (mean/variance/skewness/kurtosis, LPM_n, VaR, ES)
are INTEGRALS over the loss/return distribution F; WAL (`average_life`) and duration are
integrals over the cash-flow/loss-timing schedule F(t). Sensitivities are DERIVATIVES:
modified duration `= -(1/P) dP/dy`, convexity `= (1/P) d2P/dy2`, and generalized factor
Greeks, with analytic derivatives reconciled to finite-difference bump-and-reprice (so
optionality/prepayment uses the same operator numerically) and marginal/component capital
matching the numerical derivative of portfolio risk. The tenor curve carries a term regime
(upward/flat/inverted; persistent vs mean-reverting) read with a Hurst exponent on the
tenor dimension; `term_calculus.term_regime` exposes an injection seam (`hurst_fn`) so the
estate memory-regime characterizer's H is consumed rather than reimplemented (a local R/S
estimate is the fallback only when nothing is injected). See
`src/open_ep_framework/term_calculus.py` and `tests/test_term_calculus.py`.

**Dual scoring (Economia Mentium).** The same contract computes economic profit and
epistemic profit: in `scoring_mode: "epistemic"` the return legs carry an epistemic-value
delta, EconomicCapital is GKN standing (epistemic capital), and the risk leg is
counter-test uncertainty.

**Teeth.** An EP with a real CapitalCharge and RAROC >= hurdle VERIFIES; a value-destroying
arm (RAROC < hurdle) is FLAGGED; a RAROC with no risk measure or no economic capital is
REJECTED; a non-coherent measure used as RAROC capital (or Euler-allocated) requires an
explicit override and emits a coherence warning; a fitted `F` with `n < 30` is flagged
provisional; an org-cut whose children do not reconcile to the parent is REJECTED under
IC-1. Every computation records its distribution + measure choice on a SHA-256 receipt.

The aggregation/allocation architecture across arbitrary org cuts (product cut
`business_unit -> subportfolio -> transaction` vs client-segment cut
`geography/segment -> obligor`) is a separate consuming layer (omnirisk ADR) that binds
this kernel: RAP-1/RM-1 provide the per-node kernel and marginal contributions; they do
not implement the hierarchy walker.

## FTP + market-instruments layer (FTP-1 / HDG-1 / MKT-1)

Building on the RAROC kernel (#43) and IC-1 conservation (#39), this layer adds funding
and market instruments (consume-not-fork; deterministic/stdlib). See
`docs/ftp_market_instruments.md`.

- **Matched-maturity FTP** (`src/open_ep_framework/ftp_curve.py`): an `FTPCurve` on the
  term-structure axis and `assign_ftp` that transfer-prices each cash flow at its
  matched tenor (5y flow -> 5y point, not overnight), feeding `funding_costs`/
  `funding_credits` in the EP identity. **Separation theorem**: NIM splits into unit
  spreads + Treasury residual (structural + liquidity + basis), reconciled AS an IC-1
  settlement. Teeth: a hidden cross-subsidy (off-market booked FTP not booked to
  Treasury) is REJECTED; a Treasury residual whose components don't reconcile is
  REJECTED; matched-maturity is asserted. Schema `schemas/ftp_separation.schema.json`;
  fixtures `examples/ftp_separation_book.json` and
  `examples/ftp_separation_cross_subsidy.invalid.json`; CLI `--mode ftp-separation`.
- **Swaps/futures as zeroing derivatives** (`hedging.py`): DV01/duration (1st derivative)
  and convexity (2nd) from `term_calculus` give the hedge ratio. Teeth: a DV01-neutral
  hedge drives the net first derivative to ~0 under a curve bump; a convexity-mismatched
  linear hedge still shows 2nd-order P&L. Futures = daily mark-to-market linear hedge.
- **Options + vol surface + Merton + Ross** (`market_instruments.py`): a `VolSurface`
  (skew/smile) -> Breeden-Litzenberger risk-neutral `F_Q` -> Ross/Radon-Nikodym physical
  F -> the risk kernel's downside measures. Teeth: put skew implies a fatter downside
  than flat vol; negative implied variance and calendar/butterfly arbitrage are REJECTED;
  the **Merton bridge** (`equity_as_call`/`pd_from_structural`) gives equity=call,
  risky debt = risk-free - put, PD & recovery inversely related, EL reconciled via
  PD*LGD*EAD; the **Ross seam** (`physical_from_riskneutral`) returns F_Q unchanged under
  an identity kernel and lifts the physical mean under a risk-averse kernel.
- **Liquidity/information pricing**: `liquidity_premium(volume, regime_hurst)` (light)
  feeds both curve and surface; the Economia Mentium framing prices information's
  upside/downside off an implied-vol-style surface, with the memory-regime H shaping the
  term structure (injection seam, not a fork).

Tests: `tests/test_ftp_curve.py`, `tests/test_hedging.py`, `tests/test_market_instruments.py`.

## Crypto as a distinct asset class (CAV-1 / BR-1 / MS-1)

Crypto is not credit and not equity: most tokens have no cash flows, exhibit extreme
reflexivity, and take value from network/narrative/psychology, so the DCF machinery
does not apply. This layer lands as a separate `crypto/` package
(`src/open_ep_framework/crypto/`) that gives crypto its own value criteria and its own
reflexive `F` while **reusing the regime + risk kernel by reference** (it does not
touch the #43/#44 FTP/RAROC files). See `docs/crypto_asset_class.md`.

- **CryptoAssetValuation (CAV-1)** (`crypto/valuation.py`): tokenomics + on-chain +
  **Metcalfe** value (∝ n²) + **NVT** (crypto P/E) + a **modified EP**
  `= fee_revenue − security_cost − emission_dilution − risk_capital`, where
  `risk_capital` is a coherent Expected-Shortfall charge over a **reflexive fat-tailed
  F consumed from RM-1**; plus an evidence-bound **memetic/information** value
  (Economia Mentium: value = epistemic delta, liquidity = attention). Teeth: a
  DCF model on a no-cash-flow token is REJECTED (wrong-model); unpriced emission
  (silent inflation) is REJECTED; a bare narrative score with no evidence is REJECTED;
  a fee-bearing chain gets a finite modified-EP and Metcalfe/NVT reconcile.
  Schema `schemas/crypto_asset_valuation.schema.json`; fixtures
  `examples/crypto_valuation_fee_bearing.json`,
  `examples/crypto_valuation_dcf_wrong_model.invalid.json`.
- **BehavioralRegime (BR-1)** (`crypto/behavioral_regime.py`): a 2-state greed/fear
  **Hamilton Markov regime-switching** overlay + **prospect theory** (loss aversion
  λ>1, TK probability weighting). Teeth: a seeded greed series classifies greed with
  higher mean AND vol; rows not summing to 1, λ≤1, or non-monotone weighting are
  REJECTED. The regime tags the memory-mesh **arrival-regime** taxonomy
  (`hawkes_self_exciting`/`long_memory`) by reference. Schema
  `schemas/behavioral_regime.schema.json`.
- **ManipulationSignal (MS-1)** (`crypto/manipulation.py`): adverse selection
  (Glosten-Milgrom / Kyle) extended with concentration (whale/Gini), wash-trade and
  MEV indicators, emitted in a **GBRG governance-plane** shape with evidence. Teeth: a
  whale+wash fixture raises the signal with evidence (and a diffuse book stays clean);
  an `attested_clean` claim contradicted by concentration is REJECTED. Schema
  `schemas/manipulation_signal.schema.json`.

**Three consume-by-reference hooks:** the reflexive fat-tailed F is shaped for the
RM-1 risk kernel's LPM/ES; the greed/fear regime reuses the memory-mesh characterizer's
arrival-regime taxonomy; the ManipulationSignal is shaped for the GBRG plane (and its
adverse-selection block for the in-flight order-flow contract).

Tests: `tests/test_crypto_valuation.py`, `tests/test_crypto_behavioral_regime.py`,
`tests/test_crypto_manipulation.py`.

## Asset-class ladder — Jacob's Ladder of Assets (ALC-1)

A governed, **total and ordered** asset-class ontology that grounds the estate
omnirisk `asset_class` axis in the real economy, from tangible extraction (rung 0)
to pure digital services (rung 8). It **REPLACES** the thin
`{credit, equity, market, crypto}` enum with the full value-transformation chain
and supplies EP's **value-genesis**: extraction (rungs 1/1′) and labor-mixing
(rung 2) are where Revenue originates before it becomes a financial claim.

Every rung binds a `valuation_model` (real-option / Hotelling / sustainable-yield /
Lockean labor-value-add / spot-futures-vol / human-capital-wage / spatiotemporal-
arbitrage / DCF / network-memetic / Economia-Mentium) and a `risk_F_family` that
the **RM-1** risk kernel consumes. The renewability axis is bound to a process
regime: `depleting_stock` ↔ `monotone_absorbing` (Hotelling), `regenerating_flow`
↔ `mean_reverting_ou`, `non_physical` ↔ `non_physical`.

Teeth (`make ladder`, deterministic / stdlib): VERIFIES totality + ordering,
farming ↔ `regenerating_flow`, mining ↔ `depleting_stock`, digital_service ↔
`non_rival`; REJECTS a renewable tagged `depleting_stock` (or mining as
`regenerating_flow`), a `digital_asset` priced by scarcity as if rival, a
non-renewable with no Hotelling model, a rung missing an axis, and a non-monotone
`value_stage` ordering.

- `docs/asset_class_ladder.md`
- `schemas/asset_class_ladder.schema.json`
- `examples/asset_class_ladder.json` (+ `examples/asset_class_ladder_*.invalid.json` teeth fixtures)
- `src/open_ep_framework/asset_ladder/` (ALC-1 checker), `tests/test_asset_class_ladder.py`

## Outcome-based wisdom-services pricing (OPX-1)

The **commercial layer**: it prices a customer engagement as a **risk-adjusted,
receipted value-transfer**, splits it across the provider mesh, and settles on a
real-asset-backed token unit — consuming the whole spine (EP kernel, RM-1 risk
measures, IC-1 conservation, TC-1 term calculus, Fisher-real, ALC-1 ladder) **by
reference**. Grounding frame: the **3-T Framework** (Ecosystem→Value→Knowledge)
and the **IBM Customer-Transformation value-driver tree**.

The price decomposes in six stages: **V** (outcome value = EP delta over the four
IBM value drivers) → **VoI** (Bayesian value-of-information truth price, graded by
the-assay: certified→full, speculative→discounted, false→clawback) → **RAROC**
(`E[V] − hurdle·EconomicCapital`, EconomicCapital = coherent-tail(F_outcome)) →
**discount** (Fisher-real over horizon τ × 3-T boundary-complexity friction) →
**equilibrium** (anneal to the Nash joint-surplus point between provider cost-floor
and client value-ceiling) → **mesh split** (Euler/marginal-contribution allocation
weighted by GKN standing, `Σ = P` proven by the IC-1 settlement, denominated in a
Jacob's-ladder real-asset-backed token unit; reputation = liquidity = capital).

Teeth (`make outcome-pricing`, deterministic / stdlib): VERIFIES a verified-outcome
engagement prices to a positive risk-adjusted value, the mesh contributions sum to
the price, certified truth earns full VoI; REJECTS a price not contingent on a
verified outcome-receipt (time-and-materials), truth priced above its VoI / on
uncertified knowledge (clawback), a split where `Σ ≠ P`, a price that ignores the
outcome distribution, and a false-graded outcome not clawed back.

**Bindings (bind-upward discipline):** the engagement value-transfer is a **value
flow in the world-economic-twin** and its real-asset settlement grounds in the
**Gaia carrying-capacity base**; its six new concepts route into **ontogenesis**
as governed Systema Concept Entries. See `docs/specs/outcome-pricing-opx1.md` and
`docs/systema/outcome_pricing_concept_entries.jsonld`.

- `docs/specs/outcome-pricing-opx1.md`
- `schemas/outcome_pricing.schema.json`
- `examples/outcome_pricing_engagement.json` (+ `examples/outcome_pricing_*.invalid.json` teeth fixtures)
- `src/open_ep_framework/outcome_pricing/` (OPX-1 engine), `tests/test_outcome_pricing.py`

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

## Conservation-law settlement

EP's additive value identity is a conservation law: a settlement re-attributes value
across ledger legs but does not create or destroy it. `--mode settlement`
(`src/open_ep_framework/settlement.py`, `schemas/conservation_settlement.schema.json`)
makes that law enforceable. A settlement conserves its declared quantity iff
`| sum(inflows.amount) - sum(outflows.amount) | <= tolerance`. A conserving ledger
returns a `settled` receipt carrying the conservation ledger plus `input_hash` /
`output_hash` / `receipt_hash` (SHA-256, estate receipt-spine convention). A
**non-conserving settlement is rejected** with `SettlementError` — the engine fails
closed, and no `settled` receipt is emitted. This is measurement, simulation, and
audit only; it does not define live money movement, token issuance, redemption
rights, or public-chain settlement (mirrors the associated-surplus boundary).

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
