# OrderFlowProcess + TrendSignal — architecture

Order flow is a **marked point process** in event time. This module makes that
model assertable: arrival / decay / execution / marks, the arrival-family →
memory-regime binding, the LOB → Kyle-λ → vol-surface/FTP hook, and the
technical-analysis → mechanism-evidence reframing — each with teeth in both
directions.

Everything is deterministic and stdlib-only (`math` + `random`, seeded), so CI is
reproducible. numpy is intentionally unused (the home package declares zero
runtime dependencies).

## 1. Arrival intensity family

A univariate self-exciting Hawkes process has conditional intensity

```
λ(t) = μ + Σ_{t_i < t} φ(t − t_i),     branching ratio  n = ∫₀^∞ φ(u) du
```

- **Poisson** — `φ = 0`, constant λ = μ, i.i.d. exponential interarrivals.
- **exponential-Hawkes** — `φ(t) = αe^{−βt}`, `n = α/β`. Finite-timescale
  (short) self-excitation. Simulated via the O(#events) exponential-kernel
  recursion (the excitation term decays deterministically and jumps by α at each
  accepted event).
- **power-law-Hawkes** — `φ(t) = k(t+c)^{−(1+γ)}`, `n = k c^{−γ}/γ`. Heavy-tailed
  (long-memory) self-excitation. Ogata thinning.
- **ACD** — `ψ_i = ω + a·x_{i−1} + b·ψ_{i−1}`, `x_i = ψ_i·ε_i`: durations are
  autocorrelated and over-dispersed, which an i.i.d.-exponential (Poisson) fit
  misses.

A bivariate (buy/sell) cross-exciting case is a documented extension; the
univariate case plus the signed marks is enough for the OFI/teeth here.

### Branching ratio from the Fano factor

For a stationary Hawkes process the index of dispersion for counts satisfies
`Var(N_T)/E(N_T) → (1 − n)^{−2}`, so

```
n̂ = 1 − 1/√(IDC),        IDC = Var(N)/E(N) over count windows.
```

A Poisson stream has `IDC = 1 ⇒ n̂ = 0`. The same IDC drives the
**Poisson-vs-Hawkes discrimination** (`IDC ≥ 1.5 ⇒ excitation present, a Poisson
fit is refused`).

### Exponential vs power-law kernel

The kernel is discriminated by the **Hurst exponent of the counting process**
(the same long-memory read the memory-mesh regime characterizer uses): an
ensemble of R/S and DFA over several adaptive bin scales. Exponential
self-excitation is short-range (`H < 0.62` even for long streams); a heavy
power-law kernel is long-memory (`H ≥ 0.62`).

**Honest limitation.** Finite-sample discrimination of an exponential from a
power-law Hawkes kernel is genuinely hard — sub-critical exponential clustering
exhibits *spurious* long-range dependence over a band of scales (Bacry–Muzy).
A single-scale Hurst does not separate them robustly; the estimator therefore
(a) uses long streams for the exponential case so `H → 0.5` emerges, (b)
averages R/S and DFA over multiple adaptive bin scales, and (c) uses
comfortably-in-region seeded exemplars for the regime-label VERIFIES teeth while
sweeping only the *robust* properties (excitation, `0 < n < 1`) across seeds.
The Fano factor also **under-estimates** `n` for a diffuse power-law kernel, so
the power-law teeth assert `long_memory + excited + 0 < n̂ < 1`, not an exact `n`.

## 2. Decay — cancellation as a competing hazard

A resting limit order faces two competing exponential hazards: fill and cancel.
Its lifetime is `Exp(fill_hazard + cancel_hazard)` and its fill probability is
`fill_hazard/(fill_hazard + cancel_hazard) ∈ [0,1]`. `kernel_decay` records the
Hawkes excitation decay (β for exponential, γ for power-law).

## 3. Execution — thinning conditional on queue position

Fills thin the arrival stream conditional on queue position:
`P(fill) = exp(−queue_ahead / depletion_rate) ∈ [0,1]`. A front-of-queue order
(`queue_ahead = 0`) fills with probability 1. A fill probability outside `[0,1]`
is refused.

## 4. Marks and the risk-kernel F

Event sizes are heavy-tailed. The Hill estimator reads the Pareto tail index α
from the top order statistics; excess kurtosis is a secondary heavy-tail signal.
The marks are exposed as `risk_distribution_F` — the SAME shape memory-mesh's
`MemoryRegimeCharacterization` exposes — with `family = empirical`,
`tail_class = fat_tailed`, and loss-side `samples` that feed economic-prophet's
`risk_measures.LossDistribution` and its `risk(F, kernel, reference, horizon)`
LPM/ES lenses. **A distribution declared `gaussian` while heavy-tailed is
refused** — it would feed the wrong F.

## 5. LOB micro-signals → vol-surface / FTP

- **OFI** — order-flow imbalance = Σ signed order sizes.
- **Kyle-λ** — price impact per unit signed volume = the OLS slope of price
  change on signed volume (≥ 0 for an adverse-selection book).

`lob_signals` (`kyle_lambda`, `order_flow_imbalance`, `effective_volume`,
`signed_flow_hurst`) is shaped for `market_instruments.liquidity_premium(volume,
regime_hurst, base_bps)`, which already expects a memory-regime Hurst injection
and feeds both the FTP curve and the vol surface.

## 6. Arrival family → memory regime

| Family | `regime` | `autocorr_kernel` |
|--------|----------|-------------------|
| Poisson | `memoryless` | `delta` |
| exponential-Hawkes | `short_decaying` | `exponential` |
| power-law-Hawkes | `long_memory` | `power_law` |
| near-critical n→1 | `chaotic` | `power_law` |

`n ≥ 1` ⇒ non-stationary ⇒ refused without explicit `unstable_override`
(flash-crash guard).

## 7. Technical analysis → mechanism evidence

`TrendSignal` grounds three schools in Fuller's Synergetics cycle grammar:

- **Dow** — a *trend* requires order-flow-persistence evidence (signed-flow
  H > 0.5 or Hawkes branching ratio). Accumulation/distribution require
  inventory-cycle evidence.
- **Edwards-Magee** — *support/resistance* requires LOB-depth evidence.
- **Elliott** — a *wave_count* requires MEASURED self-similarity across scale
  (multifractal-spectrum width ≥ 0.05 or cross-scale Hurst), bound to the
  memory-regime multifractal spectrum by reference. Fibonacci ratios
  (0.382/0.618/1.618) are falsifiable: a claim that misses the measured
  retracement beyond tolerance is flagged.
- **Fuller Synergetics** — a cycle converges to a **frequency** (= scale/degree,
  the multifractal-spectrum axis) at a tunable **vertex**, with a FINITE alphabet
  of fundamental closures `{tetra_3 (3), octa_4 (4), icosa_5 (5)}`. A wave-count
  must resolve to one of these; asserting any other closure — or an
  `event_count` that does not match — is refused (the wave-counting-subjectivity
  guard). Elliott's 3-wave correction = `tetra_3`; 5-wave impulse = `icosa_5`;
  full 8 = tetra+icosa (Fibonacci 3,5,8,13… falls out). One grammar governs both
  Elliott and the estate RBF/S¹ cycle work.

Provenance is a KE-contract class `{learned | human_authored | imported}`; a
`learned` signal must carry mechanism evidence.

## 8. Teeth (both directions)

**VERIFIES** — seeded Poisson → `memoryless`, n̂≈0; exponential Hawkes(n=0.6) →
`short_decaying`, excited, 0<n̂<1; power-law Hawkes → `long_memory`; ACD →
duration autocorrelation a Poisson fit misses; the Poisson-vs-Hawkes test fires
on excitation; Kyle-λ is recovered; power-law marks read heavy-tailed.

**REJECTS** — branching n≥1 without override (UNSTABLE); Poisson claimed while
excited; gaussian marks while heavy-tailed; fill probability > 1; negative
intensity; a trend with no order-flow-persistence evidence; support/resistance
with no LOB-depth evidence; a wave_count with no measured self-similarity or a
non-fundamental closure; a mismatched Fibonacci ratio; a tampered receipt; a
dropped required field.

**COHERENCE** — the marks F carries a `risk(F,…)` interface hint and (when
empirical) LossDistribution samples; the LOB signals carry the
`liquidity_premium(…)` interface and no negative liquidity input.

## Decision thresholds

| Constant | Value | Meaning |
|----------|-------|---------|
| `MIN_N` | 30 | below this a characterization is only `provisional` |
| `IDC_EXCITE` | 1.5 | index of dispersion above this ⇒ self-excitation present |
| `H_LONG` | 0.62 | ensemble counting-Hurst above this ⇒ long-memory (power-law) kernel |
| `N_CRITICAL` | 0.90 | branching ratio at/above this (but < 1) ⇒ near-critical edge |
| `DUR_AUTOCORR_SIGNIF` | 0.10 | lag-1 duration autocorr above this ⇒ ACD memory |
| `FAT_TAIL_KURTOSIS` | 1.5 | excess kurtosis above this ⇒ heavy-tailed marks |
| `HILL_TAIL_FINITE` | 4.0 | Hill tail index below this ⇒ a genuine power-law tail |

## Follow-ups (out of scope here)

- Live LOB feed adapter (replace the seeded generators with an observed stream).
- Multivariate / cross-exciting (buy↔sell) Hawkes calibration for a true OFI
  reflexivity model.
- The Economia-Mentium information-order-book application of this contract.
