# microstructure — order flow as a marked point process

A **contract-with-teeth** for market-microstructure order flow modeled as a
**marked point process** in event time, plus a mechanism-grounded reframing of
technical-analysis signals. Self-contained module: JSON Schema + a deterministic,
stdlib-only Python validator with per-tooth mutation coverage, valid/invalid
fixtures, a Makefile target, a path-filtered CI workflow, and docs. It touches
none of the in-flight risk-kernel / FTP files under `src/open_ep_framework/`.

## What it models

Order flow is a marked point process: events **arrive**, rest and are
**cancelled** (decay), and are **filled** (execution), each carrying a **mark**
(signed size).

| Layer | Model | Estimator |
|-------|-------|-----------|
| Arrival | Poisson → exponential-Hawkes → power-law-Hawkes → ACD | branching ratio `n` via the Fano factor; `poisson_vs_hawkes` discrimination; counting-process Hurst for the kernel |
| Decay | cancellation as a competing hazard (limit-order lifetime) | `fill_hazard/(fill_hazard+cancel_hazard)` |
| Execution | fill as a thinning conditional on queue position | `exp(-queue_ahead/depletion_rate)` |
| Marks | heavy-tailed (power-law) sizes | Hill tail index + excess kurtosis |
| LOB signals | order-flow imbalance (OFI), Kyle-λ price impact | OLS slope of price change on signed volume |

## Arrival family → memory regime (the key binding)

The arrival family is mapped onto the **estate memory-regime taxonomy** (from
memory-mesh's `MemoryRegimeCharacterization`, consumed **by reference**) in EVENT
time:

| Arrival family | Memory regime | Kernel |
|----------------|---------------|--------|
| Poisson (constant λ) | `memoryless` | `delta` |
| exponential-Hawkes | `short_decaying` | `exponential` |
| power-law-Hawkes | `long_memory` | `power_law` |
| near-critical (n→1) | `chaotic` (unstable edge) | `power_law` |

`n ≥ 1` is non-stationary — the **flash-crash guard** — and is refused unless a
record carries an explicit `unstable_override`.

## Consumed by reference (consume-not-fork)

- **Risk kernel** — the marks are exposed as `risk_distribution_F`, shaped for
  economic-prophet `risk_measures.risk(F, kernel, reference, horizon)` (LPM/ES
  lenses); a heavy-tailed marks F carries loss-side `samples` for
  `LossDistribution`.
- **Vol-surface / FTP** — `lob_signals` (Kyle-λ, OFI, effective volume,
  signed-flow Hurst) are shaped for `market_instruments.liquidity_premium(volume,
  regime_hurst, base_bps)`, which already expects a memory-regime Hurst injection.
- **Regime taxonomy + `risk_distribution_F` shape + SHA-256 receipt** — reused
  from memory-mesh's `MemoryRegimeCharacterization`, not redefined.

## Technical-analysis reframing

A `TrendSignal` is a LEARNED, receipted signal whose evidence is the mechanism:

- **Dow** — a *trend* must carry order-flow-persistence evidence (signed-flow
  Hurst > 0.5 or a Hawkes branching ratio); accumulation/distribution map to
  inventory-cycle evidence.
- **Edwards-Magee** — *support/resistance* must carry LOB-depth evidence.
- **Elliott** — a *wave_count* must carry MEASURED self-similarity across scale
  (multifractal-spectrum width / cross-scale Hurst), bound to the memory-regime
  multifractal spectrum by reference. Fibonacci ratios are a falsifiable scaling
  hypothesis, tested against the measured retracement — not assumed.
- **Fuller Synergetics** is the structural vocabulary: a cycle converges to a
  frequency (= scale/degree) at a tunable vertex, with a FINITE alphabet of
  fundamental closures `{tetra_3, octa_4, icosa_5}`. Elliott's 3-wave correction
  = `tetra_3`, 5-wave impulse = `icosa_5`, full 8 = tetra+icosa. One grammar
  governs both Elliott and the estate RBF/S¹ cycle work.

## Run

```
make -C microstructure validate
```

Deterministic and stdlib-only (`math` + `random`; numpy intentionally unused).
See `docs/order-flow-process.md`.
