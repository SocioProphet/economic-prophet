# Jacob's Ladder of Assets (ALC-1)

A governed, **total and ordered** asset-class ontology — a *contract with teeth* —
that grounds the estate omnirisk `asset_class` axis in the real economy, from
tangible extraction (rung 0) up to pure digital services (rung 8).

- Schema: [`schemas/asset_class_ladder.schema.json`](../schemas/asset_class_ladder.schema.json)
- Canonical ladder: [`examples/asset_class_ladder.json`](../examples/asset_class_ladder.json)
- Checker (teeth): [`src/open_ep_framework/asset_ladder/ladder.py`](../src/open_ep_framework/asset_ladder/ladder.py)
- Gate: `make ladder` (deterministic, stdlib-only) and `tests/test_asset_class_ladder.py`

## Why a ladder replaces the thin enum

The estate omnirisk axis used a thin `{credit, equity, market, crypto}` enum.
Those are all *financial claims* — they name what a balance sheet holds **after**
value already exists, so they cannot say **where Revenue comes from**. This ladder
**REPLACES** that enum with the full value-transformation chain and supplies
economic-prophet's **value-genesis**: extraction (rungs 1 / 1′) and labor-mixing
(rung 2) are where Revenue *originates* before it becomes a financial claim
(rungs 3+). Financial claims do not vanish — they are simply the *upper*
half of a ladder whose lower half was previously invisible.

## The rungs

Every rung carries all structuring axes and binds a `valuation_model` plus a
`risk_F_family` that the **RM-1** risk kernel (`src/open_ep_framework/risk_measures.py`)
can consume.

| # | stage | asset class | tangibility | rivalry | renewability | process regime | labor | valuation_model | risk F-family (RM-1) |
|---|-------|-------------|-------------|---------|--------------|----------------|-------|-----------------|----------------------|
| 0 | 0 | natural_capital | tangible | rival | depleting_stock | monotone_absorbing | none | real_option | expected_shortfall |
| 1 | 1 | extractive_nonrenewable | tangible | rival | depleting_stock | monotone_absorbing | moderate | **hotelling_rent** | expected_shortfall |
| 1′ | 2 | renewable_harvest | tangible | rival | regenerating_flow | mean_reverting_ou | high | **sustainable_yield** | sortino |
| 2 | 3 | processed_goods | tangible | rival | regenerating_flow | mean_reverting_ou | high | labor_value_add | expected_shortfall |
| 3 | 4 | commodity_market | semi_tangible | rival | non_physical | non_physical | low | spot_futures_vol | spectral |
| 4 | 5 | labor_market | semi_tangible | rival | non_physical | non_physical | high | human_capital_wage | sortino |
| 5 | 6 | mercantile_trade | semi_tangible | rival | non_physical | non_physical | moderate | spatiotemporal_arbitrage | expected_shortfall |
| 6 | 7 | pure_service | intangible | rival | non_physical | non_physical | high | dcf | expected_shortfall |
| 7 | 8 | digital_asset | intangible | **non_rival** | non_physical | non_physical | low | network_memetic | expected_shortfall |
| 8 | 9 | digital_service | intangible | **non_rival** | non_physical | non_physical | moderate | economia_mentium | spectral |

`value_stage` is the ordered rung index; it is strictly increasing and
`tangibility` is monotone non-increasing tangible → digital. Rung **1′**
(renewable_harvest) is the regenerating sibling of the extractive rung — same
transformation band, opposite renewability.

### The valuation models (value-genesis, per rung)

- **real_option** — scarcity × location × option-to-extract; the in-situ reserve as a real option.
- **hotelling_rent** — the Hotelling rule: the scarcity rent grows at the interest rate *r*; the optimal-depletion program empties a **depleting** stock.
- **sustainable_yield** — maximum-sustainable-yield on a **regenerating** flow; overharvesting collapses the flow. Weather / biological risk.
- **labor_value_add** — Lockean value-add = labor + capital + know-how mixed into extracted / harvested inputs (the peak of physical value-genesis).
- **spot_futures_vol** — spot + futures + a vol surface; consumes the merged economic-prophet market / vol-surface work (**#44**).
- **human_capital_wage** — human capital priced as a wage / productivity claim; references the Labor Network Charter (**prophet-workspace #109**).
- **spatiotemporal_arbitrage** — value from moving goods across space and time (no transformation of the good, only of its position).
- **dcf** — contract / cash-flow discounting; the traditional EP object.
- **network_memetic** — Metcalfe / NVT network value; **non-rival** (copying is free, so scarcity/DCF is the wrong model). Consumes the crypto asset-class contract in flight (CAV-1).
- **economia_mentium** — value = epistemic delta, liquidity = attention; **non-rival** and unbounded by physical stock.

## Renewability ↔ process-regime crosswalk

The renewability axis induces a stochastic-process regime the kernel's F-builder
can dispatch on (aligned with the TC-1 term-calculus persistence read, and the
OU / process crosswalk in flight):

| renewability | process regime | intuition |
|--------------|----------------|-----------|
| `depleting_stock` | `monotone_absorbing` | reserves drift toward an **absorbing barrier at zero**; the Hotelling depletion path is monotone. |
| `regenerating_flow` | `mean_reverting_ou` | the stock **mean-reverts** (Ornstein–Uhlenbeck) toward its sustainable yield. |
| `non_physical` | `non_physical` | a claim / service / digital asset — no physical stock; the process is chosen inside the valuation model. |

The checker enforces this crosswalk on **every** rung.

## Teeth

`make ladder` runs the deterministic, stdlib-only checker
(`open_ep_framework.asset_ladder`). It:

**VERIFIES**
- the ladder is **total + ordered** — all ten rungs present in order, every rung
  carrying tangibility + rivalry + renewability + process_regime + valuation_model
  + risk_F_family + value_stage;
- `value_stage` strictly increases and `tangibility` never increases (monotone
  tangible → digital);
- farming classifies `regenerating_flow`; mining classifies `depleting_stock`; a
  digital_service classifies `non_rival`.

**REJECTS** (one `.invalid.json` fixture each)
- a `renewable_harvest` tagged `depleting_stock` (or `mining` as `regenerating_flow`);
- a `digital_asset` priced by **scarcity** as if rival — non-rival economics: value
  is network / attention, not scarcity;
- a non-renewable with **no** depletion / Hotelling model;
- a rung **missing any required axis** (rejected by both the schema and the checker);
- a `value_stage` ordering that is **not monotone** tangible → digital.

## Integration with the kernel

Each rung binds a `valuation_model` + a `risk_F_family` that the economic-prophet
kernel consumes:

- **F-family** → **RM-1** unified risk-measure family (`risk_measures.py`): every
  `risk_F_family` is a known RM-1 kernel (`sharpe`/`sortino`/`kappa`/`var`/
  `expected_shortfall`/`spectral`/`stddev`) applied to a rung-appropriate loss
  distribution *F* (e.g. the digital_asset rung scores a **reflexive, fat-tailed**
  *F* with a coherent Expected-Shortfall charge, matching CAV-1).
- **Hotelling** for non-renewable extraction; **sustainable-yield** for renewable
  harvest; **DCF** for pure service; **network / memetic** and **Economia Mentium**
  for the non-rival digital rungs.
- **Value-genesis**: rungs 1/1′/2 are where Revenue is *born* (extraction +
  labor-mixing) before rungs 3+ turn it into a financial claim.

Binding the ladder into the kernel's F-builder dispatch and the entity/portfolio
`asset_class` field is tracked as a follow-up (see the repository issue).

## References

- Merged economic-prophet market / vol-surface contract — **#44** (FTP-1 / HDG-1 / MKT-1).
- Labor Network Charter — **prophet-workspace #109** (labor_market rung).
- Crypto asset-class contract in flight — **CAV-1** (`feat/crypto-asset-class`): the digital_asset rung.
- RM-1 unified risk-measure family — `src/open_ep_framework/risk_measures.py`.
- TC-1 term-calculus persistence (mean-reverting vs persistent) — `src/open_ep_framework/term_calculus.py`.
- Economia Mentium — value = epistemic delta (digital_service rung).
