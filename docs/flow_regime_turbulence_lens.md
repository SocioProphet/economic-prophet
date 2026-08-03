# Flow-regime: ternary options ⟷ low-dimensional turbulence (FRT-1 / FRL-1)

The payload of a real synthesis: a **market process** and a **fluid flow** are read by
the *same* regime lens (the memory-mesh characterizer's taxonomy), and each regime
selects a different mechanism. Metaphor → mechanism, **not** numerology — every claim
carries a falsifying tooth, and an explicit no-overclaim guard fences the honest limit.

Home: `src/open_ep_framework/flow_regime/` (next to the risk kernel and vol surface it
consumes). Rationale: the trinomial pricer genuinely imports the estate Black-76 kernel
(`market_instruments`), so it belongs inside the `open_ep_framework` package where that
import is first-class; the Lorenz lens shares the module because it is the other half of
the same regime thesis.

## Consume-by-reference (not forked, not edited)

- **economic-prophet risk kernel + vol surface** (#43/#44): `market_instruments.bs_call`
  / `bs_put` (Black-76) are the Black-Scholes reference the trinomial must converge to
  (memoryless) and differ from (OU).
- **memory-mesh process/regime characterizer** (#50/#52 + the process-family crosswalk):
  - the **OU fit** (`estimate_ou` → θ, μ, half-life = ln2/θ) supplies the mean-reverting
    regime's reversion target and speed — `RegimeSpec.from_ou_characterization(θ, μ)`;
  - the **process → regime → option → archetype crosswalk** supplies the regime labels
    (`ornstein_uhlenbeck` → Vasicek/Heston, `fractional_brownian_motion` → rough-vol, …)
    reproduced in `trinomial.CROSSWALK`;
  - the **Lyapunov estimator + regime taxonomy** are consumed through an *injection seam*
    `classify_flow(..., lyapunov_fn=...)` — exactly the pattern `term_calculus` uses for
    the Hurst characterizer (`hurst_fn`). The memory-mesh `lyapunov_rosenstein` can be
    injected; the local Benettin exponent is the hermetic-CI fallback. The chaos
    threshold `CHAOS_LAMBDA = 0.30` is the memory-mesh value, kept identical so the two
    lenses agree by construction.

## Deliverable 1 — regime-aware trinomial (ternary) pricer (FRT-1)

A CRR binomial is two-state (up/down) and regime-blind → Black-Scholes. The **Boyle
trinomial** adds a third **stay** branch, and the middle branch projects to the regime's
stable point:

| regime kind | memory-mesh label | middle-branch semantics | anchor model |
|---|---|---|---|
| `memoryless` | `brownian_gbm` | plain martingale stay; **→ Black-Scholes** | Black-Scholes/76 |
| `mean_reverting` | `ornstein_uhlenbeck` | projects to the OU target **μ** (θ from the fit) | Vasicek / Hull-White / Heston |
| `trending` | `fractional_brownian_motion` | drift dominates, stay branch **weak** | rough volatility |
| `chaotic` | `chaotic` | leans to the attractor centroid μ; local instability flagged | — |

The memoryless tree is a moment-matched Boyle/Kamrad-Ritchken lattice; the mean-reverting
tree is a Hull-White trinomial centred on `x = ln μ`, so at μ (lattice level `j = 0`) the
drift vanishes and the ternary stay branch is symmetric and dominant — *the middle branch
projects to the stable point*. **Three = Fuller's tetra-3 fundamental cycle** (Synergetics
grammar, microstructure #46): a structural note; the mechanism (a middle branch that lands
on a regime-specific stable point) is what earns the ternary form.

**Teeth** (`tests/test_flow_regime_trinomial.py`, `scripts/validate_flow_regime.py`):

- **BS-LIMIT** (VERIFIES): memoryless price → Black-Scholes as steps grow (|diff| < 8e-3
  at 400 steps, error strictly shrinking).
- **OU-DIFFERS** (VERIFIES): a mean-reverting price differs from Black-Scholes — mean
  reversion is priced.
- **PROBS ∈ [0,1]** (REJECTS): every node's `(pu, pm, pd)` lies in [0,1] and sums to 1; a
  negative middle branch or a non-normalized triple is rejected (`prob-out-of-range`).
- **REGIME-REALLY-CONSUMED** (REJECTS): a "regime-aware" record whose price equals
  Black-Scholes across regimes is rejected — identical prices prove the regime was never
  consumed (`regime-blind-equals-bs`). This is the Deliverable-1 no-numerology guard.

## Deliverable 2 — low-dimensional flow-regime lens (FRL-1)

The **Lorenz (1963)** system is the canonical three-variable reduction of Rayleigh–Bénard
convection — a truncated Navier–Stokes flow:

```
dx/dt = σ(y − x);  dy/dt = x(ρ − z) − y;  dz/dt = xy − βz
```

We compute **fixed-point stability** (Jacobian eigenvalues, via the characteristic cubic)
and the **largest Lyapunov exponent** (Benettin, or an injected memory-mesh estimator) and
classify:

- **laminar** — a stable fixed point (all eigenvalue real parts < 0), λ ≤ 0;
- **turbulent** — a strange attractor, λ > 0.

**Teeth** (`tests/test_flow_regime_lorenz.py`, `scripts/validate_flow_regime.py`):

- **CLASSIC-TURBULENT** (VERIFIES): σ=10, ρ=28, β=8/3 → λ ≈ 0.92 (> 0), no stable fixed
  point → turbulent (literature λ ≈ 0.906).
- **LAMINAR** (VERIFIES): a sub-critical set (ρ < 1) → stable origin, λ < 0 → laminar;
  1 < ρ < ρ_Hopf(≈24.74) → stable convective pair C± → laminar.
- **SIGN-AGREEMENT** (VERIFIES + REJECTS): the Lyapunov-sign regime must match the
  memory-mesh taxonomy (chaotic ⟷ turbulent, stable ⟷ laminar); a mismatch is rejected
  (`sign-mismatch`).
- **NO-OVERCLAIM** (REJECTS): a record claiming to **solve or prove Navier–Stokes
  existence/smoothness** (Clay Millennium) is rejected (`claims-solves-navier-stokes`);
  the schema pins `scope` to `analogue_characterization_only` (`wrong-scope`).

### Vol-cascade ⟷ turbulent energy cascade (analogue)

The market **volatility cascade** — large-scale vol shocks fragmenting into small-scale
intermittent bursts, with multifractal scaling — is the statistical twin of Kolmogorov's
**turbulent energy cascade** (energy injected at large eddies, dissipated at the
microscale). Ghashghaie et al. (*Nature*, 1996) showed FX returns share the multifractal,
cascade-like statistics of hydrodynamic turbulence; rough volatility (Gatheral–Jaisson–
Rosenbaum, 2018) finds volatility is itself a fractional process with **H ≈ 0.1** — the
anti-persistent/intermittent end of the memory-mesh Hurst axis. The vol cascade maps to
the turbulent cascade *through that Hurst / multifractal axis*, unifying the long-memory
work with the #44 vol surface **by reference**. This is a characterization **lens**, not
an identity, and never a solution of Navier–Stokes.

## Honesty / no-overclaim (stated explicitly)

This module characterizes regimes. It does **not** solve, prove, or bear on the Navier–
Stokes existence-and-smoothness problem, and it does not claim the ternary/tetra form is
numerologically significant. Both guards are enforced as rejecting teeth, not just prose.

## Run

```
pip install -e . jsonschema
python -m pytest -q -k flow_regime          # per-tooth mutation tests
python scripts/validate_flow_regime.py      # VERIFIES + REJECTS + COHERENCE over fixtures
```
