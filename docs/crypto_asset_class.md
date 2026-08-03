# Crypto as a distinct asset class (CAV-1 / BR-1 / MS-1)

Crypto is not credit and not equity. Most tokens have **no cash flows**, exhibit
**extreme reflexivity**, and derive value from **network, narrative and psychology**.
The credit/equity DCF machinery therefore does not directly apply: an asset class this
different needs its own value criteria and its own loss distribution `F`, while
**reusing the estate's regime + risk kernel by reference** rather than forking it.

This module lands as a separate `crypto/` package
(`src/open_ep_framework/crypto/`) and does **not** touch the just-merged FTP/RAROC
files (#43/#44) — it consumes them.

## 1. CryptoAssetValuation (CAV-1) — value criteria, not DCF

`src/open_ep_framework/crypto/valuation.py`, schema
`schemas/crypto_asset_valuation.schema.json`.

**Protocol / tokenomics:** circulating & max supply, emission rate, burn, staking
yield, and the **security budget** (hashrate/stake cost of attacking the chain).

**On-chain:** active addresses, TVL, **fee revenue**, annual transaction volume.

**Network value:**
- **Metcalfe value** ∝ n²: `metcalfe_value = k · active_addresses²`, with a
  Metcalfe-implied fair price and a `price_to_metcalfe` rich/cheap ratio.
- **NVT ratio** = network value ÷ transaction volume — the crypto **P/E**.

**Modified economic profit** (the crypto EP identity):

```
modified_ep = fee_revenue − security_cost − emission_dilution − risk_capital
```

- `fee_revenue` — the real, earned leg (a fee-bearing chain).
- `security_cost` — the security budget (issuance + fees to miners/validators).
- `emission_dilution` = `(circulating_supply·emission_rate − burn_tokens)·price`.
  Deflationary (burn > emission) makes this **negative** (accretive).
- `risk_capital` — a **coherent Expected-Shortfall** charge over a **reflexive,
  fat-tailed** loss distribution `F`, consumed from the RM-1 risk kernel. Reflexivity
  widens vol (`sigma_eff = sigma·(1 + reflexivity)`); a small Student-t `df` supplies
  the fat left tail. `risk_capital = ES_fraction(F) · risk_notional`.

**Memetic / information-theoretic value (Economia Mentium):** value as
attention/narrative, framed as an information-asset — value = epistemic delta,
liquidity = attention/volume. From an attention series it computes a **virality**
(replication) factor and an **epistemic delta** = `KL(attention ‖ uniform)` in bits
(`log2 T − H`). `information_value = virality · epistemic_delta`. A transparent,
testable scalar — **not** a hand-waved narrative number.

**Teeth**
- REJECTS a DCF/cash-flow model on a token with `cash_flow_bearing=false`
  (wrong-model guard) — must use network/fee/memetic criteria.
- REJECTS net positive emission with no price (unpriced dilution / silent inflation).
- REJECTS a memetic value asserted with no attention series / no evidence
  (learn-don't-match; no bare narrative scores).
- VERIFIES a fee-bearing chain gets a finite modified-EP; Metcalfe/NVT reconcile to
  inputs; more reflexivity ⇒ larger ES risk_capital (a control that moves).

## 2. BehavioralRegime (BR-1) — greed/fear + prospect theory

`src/open_ep_framework/crypto/behavioral_regime.py`, schema
`schemas/behavioral_regime.schema.json`.

A **2-state (greed/fear) Hamilton-style Markov regime-switching** model: a
row-stochastic transition matrix + per-regime Gaussian returns. A forward Hamilton
filter yields the posterior `P(greed)`; a point is greed when it exceeds 0.5.

A **prospect-theory** overlay: value function `v(x)=x^α` (gains) /
`−λ(−x)^β` (losses) with loss aversion `λ>1`, and Tversky-Kahneman probability
weighting `w(p)=p^γ/(p^γ+(1−p)^γ)^{1/γ}`.

**Teeth**
- VERIFIES a seeded greed-heavy series classifies greed with **higher mean AND higher
  volatility** (robust across seeds).
- REJECTS a transition matrix whose rows don't sum to 1.
- REJECTS loss aversion `λ ≤ 1`.
- REJECTS a non-monotone probability weighting (`γ` below ~0.28).

**Memory-regime binding (by reference):** each regime carries an `arrival_regime`
label from the memory-mesh characterizer taxonomy — the reflexive/self-exciting phase
is the `hawkes_self_exciting` (or `long_memory`) arrival regime, the same taxonomy the
memory mesh uses. The CAV-1 reflexive `F` corresponds to this self-exciting regime.

## 3. ManipulationSignal (MS-1) — predatory-cartel / information asymmetry

`src/open_ep_framework/crypto/manipulation.py`, schema
`schemas/manipulation_signal.schema.json`.

The honesty/governance layer. It extends adverse selection —
**Glosten-Milgrom** spread `= 2·PIN·(V_high − V_low)` and **Kyle's** λ `= σ_v/(2σ_u)` —
with crypto-native indicators:
- **Concentration:** whale risk via the **Gini** coefficient and top-holder share.
- **Wash trading:** self-trade share and volume-inflation (reported ÷ settled).
- **MEV:** maximal-extractable-value intensity = MEV extracted ÷ volume.

It emits a **ManipulationSignal** with severity, verdict and an **evidence** list.

**Teeth**
- VERIFIES a high-concentration + wash-trade fixture raises the signal with evidence
  (`verdict=manipulated`); and a diffuse, honest book stays `clean` (the control fires
  in both directions).
- REJECTS an `attested_clean` claim contradicted by concentration above threshold
  (an attestation cannot override on-chain evidence).

**GBRG plane (by reference):** the signal carries a `gbrg` block
(signal_id, subject, severity, evidence_count, `blast_radius`, `containment`) shaped
for the governed-blast-radius-graph governance/containment plane. The
adverse-selection block is shaped to consume the in-flight order-flow contract
(`feat/microstructure-order-flow-contract`).

## Three consume-by-reference hooks (do not fork)

| Hook | What crypto consumes | Where |
|------|----------------------|-------|
| **Risk kernel (RM-1)** | reflexive fat-tailed `F` → LPM / Expected Shortfall → `risk_capital` | `risk_measures.LossDistribution.simulate_equity`, `risk(...,"expected_shortfall")`, `lpm` |
| **Memory-regime characterizer** | greed/fear regime tags the `hawkes_self_exciting` / `long_memory` arrival regime | `behavioral_regime.ARRIVAL_REGIMES`, `arrival_regime` / `memory_regime_ref` fields |
| **GBRG governance plane** | ManipulationSignal emitted in a governed-blast-radius-graph shape | `manipulation` `gbrg` output block |

## Boundary

Deterministic and stdlib-only (analytic where possible, seeded PRNG otherwise), so CI
is reproducible. Measurement, simulation and audit only: no live on-chain feeds, token
issuance, custody, or trading.

Tests: `tests/test_crypto_valuation.py`, `tests/test_crypto_behavioral_regime.py`,
`tests/test_crypto_manipulation.py`. Fixtures: `examples/crypto_*.json` (valid) and
`examples/crypto_*.invalid.json` (schema-valid but contract-rejected).
