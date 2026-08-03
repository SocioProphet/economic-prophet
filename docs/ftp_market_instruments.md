# FTP + market-instruments layer (FTP-1 / HDG-1 / MKT-1)

This layer sits on the RAROC kernel (`risk_measures`, `term_calculus`,
`risk_adjusted_profit`, PR #43) and the IC-1 conservation law (`settlement`, #39).
It is consume-not-fork: nothing here reimplements the calculus, the risk-measure
family, the EP identity or the conservation invariant.

Measurement, simulation and audit only: no live money movement, curve/surface
feeds, token issuance, redemption, settlement rails or trading.

## 1. Matched-maturity Fund Transfer Pricing (`ftp_curve.py`, FTP-1)

- `FTPCurve` is the reference funding curve (SOFR/OIS/swap points by tenor) on the
  same tenor axis as `term_calculus` cash-flow schedules.
- `assign_ftp(schedule, curve)` prices each cash flow at the curve point matching its
  repricing/maturity tenor (a 5y flow at the 5y point, not overnight) and returns the
  PV-weighted transfer rate. `funding_cost` / `funding_credit` = transfer_rate x balance
  feed the EP identity's `funding_costs` / `funding_credits` legs.
- **Separation theorem** (`separation_decomposition`): net interest margin splits into
  per-unit spreads (lending spread and deposit spread to the curve) plus a Treasury
  residual (structural rate mismatch + liquidity + basis). The identity

  ```
  NIM = sum(unit spreads) + Treasury residual
  ```

  is reconciled AS an IC-1 conservation settlement.

**Teeth.** Matched-maturity is asserted (5y bullet -> 5y rate). A unit funded at an
off-market FTP rate (booked != matched) without booking the gap to Treasury is a hidden
cross-subsidy and is REJECTED. A Treasury residual whose declared components
(structural/liquidity/basis) do not reconcile to the computed residual is REJECTED.
Schema `schemas/ftp_separation.schema.json`; fixtures
`examples/ftp_separation_book.json` (valid) and
`examples/ftp_separation_cross_subsidy.invalid.json`; CLI `--mode ftp-separation`.

## 2. Swaps / futures as zeroing derivatives (`hedging.py`, HDG-1)

The hedge ratio is read from the calculus: the first derivative (DV01 / duration) sets
a DV01-neutral hedge, and the second derivative (convexity) is what a linear hedge
cannot neutralize.

- `dv01(schedule, y)` = modified_duration x price x 1bp.
- `hedge_notional(book, y, instrument, y)` = `-DV01_book / DV01_instrument_per_unit`.
- `net_first_derivative` / `net_second_derivative` / `hedged_pnl` reprice the hedged
  book by finite-difference bump.
- `futures_variation_margin` marks a margined linear futures hedge to market daily.

**Teeth.** A DV01-neutral hedge drives the net first derivative to ~0 (many orders of
magnitude below the unhedged book). A convexity-mismatched linear hedge still shows
2nd-order P&L (residual asserted). Futures daily variation margin sums to the linear
payoff.

## 3. Options, vol surface, Merton bridge, Ross seam (`market_instruments.py`, MKT-1)

Chain: **VolSurface -> (Breeden-Litzenberger) F_Q -> (Ross / Radon-Nikodym) physical F
-> LPM / Sortino / ES** downside measures in the risk kernel.

- `VolSurface` (implied vol by strike x tenor, with skew/smile). `validate()` rejects
  non-positive implied variance, calendar arbitrage (total variance falling in tenor)
  and butterfly arbitrage (call price non-convex in strike / negative density).
- `implied_distribution(surface, tenor, forward)` builds the risk-neutral density
  `q(K) = d2C/dK2` (Breeden-Litzenberger, using `term_calculus.second_difference`) and
  returns a `LossDistribution` F_Q the risk kernel can score.
- **Merton bridge**: `equity_as_call(V, D, sigma, T, r)` gives equity = call on assets,
  risky debt = risk-free - put, PD = N(-d2) and an endogenous recovery; `pd_from_structural`.
  EL reconciles via the estate `expected_loss` identity PD x LGD x EAD.
- **Ross recovery / Arrow-Debreu seam**: `physical_from_riskneutral(F_Q, kernel_fn)`
  maps risk-neutral to physical via a pricing kernel (dP/dQ proportional to 1/m). The
  identity kernel returns F_Q unchanged; a full Ross recovery (transition-independent
  kernel) plugs in here.

**Teeth.** A put-skew surface implies a fatter downside than a flat-vol lognormal.
Negative implied variance and calendar/butterfly violations are REJECTED. Merton
put-call parity holds; PD and recovery move inversely with leverage; EL reconciles.
The Ross transform with an identity kernel returns F_Q unchanged; a risk-averse kernel
lifts the physical mean above the risk-neutral mean (the equity premium).

## 4. Liquidity premium + information-pricing (Economia Mentium)

`liquidity_premium(volume, regime_hurst)` is a light reference: the premium falls with
traded volume and rises with a persistent (illiquid/trending) memory regime. It feeds
both the FTP curve (add to the rate) and the vol surface (add to vol). `regime_hurst`
is intended to be supplied by the estate memory-regime characterizer (injection, not a
fork), which shapes the surface term structure.

**Economia Mentium framing.** The same option/vol-surface machinery prices the upside
and downside of *information*: an implied-vol-style surface over knowledge states,
liquidity as a function of volume and reputation. Epistemic profit (RAP-1 dual scoring)
values the epistemic-delta return; this layer supplies the surface/skew and the
risk-neutral-to-physical transform for its downside measures.

## Follow-ups (@mdheller)

- **Live curve/surface feeds**: real SOFR/OIS/swap curve and listed-option vol surface
  ingestion + calibration (fitting `FTPCurve` and `VolSurface` to market quotes).
- **Full Ross recovery**: transition-independent pricing-kernel recovery to replace the
  identity/parametric-kernel seam.
- **Merton calibration**: back out asset value/vol from equity and reconcile the
  structural PD/LGD against the credit F builder end-to-end on real names.
- **Regime injection**: wire the estate memory-regime characterizer H into
  `liquidity_premium` and the surface term structure.

Cross-ref: economic-prophet #43 (RAROC kernel), #39 (IC-1), #42 (Basel capital), GKN#9.
