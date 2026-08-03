# Silent-Weapons falsification testbench (`silent_testbench`)

**Audit-only. This is a falsification study, not an operationalisation.** The module
implements the mechanisms described in the pamphlet *"Silent Weapons for Quiet Wars"* on
this repo's existing engines **by reference**, then confronts each with cited historical
reference data and grades it with a verdict + a deterministic receipt. Nothing here
operationalises control of anything; the point is to test the document's specific claims and
show, honestly, where they reduce to ordinary economics and where they are false.

> A control that never fires is suspect: the teeth run in **both** directions — they
> VERIFY what reproduces and REJECT/FLAG what overclaims. Reproducing the document's
> *mechanism* is **not** confirming its *conspiracy*, and a record that says so is rejected.

## Phase 1 — the executable simulator

### The shock-test estimator (SILENT pp.26-29) IS cross-price elasticity / VAR impulse response

`shock_estimator.py` implements the document's procedure literally: model `P = Σ a_jk X_k`,
shock a price, measure `ΔP`, recover `a_jk = ∂P/∂X_k`, assemble `[a_jk]`, solve
`[a_jk][X_k] = [Y_j]`, and invert to `[b_kj]`. It then **demonstrates numerically** that the
recovered matrix is identical (to ~1e-13) to:

| doc term | standard econometrics |
| --- | --- |
| shock a price, read `ΔP` | partial derivative `∂lnQ_j/∂lnP_k` = cross-price **elasticity** |
| assemble `[a_jk]` | demand-system impact matrix = **VAR** contemporaneous **impulse-response** matrix |
| solve `[a_jk][X_k]=[Y_j]` | solving the linear structural system |
| invert to `[b_kj]` | recovering the structural (A/B) matrix — **SVAR identification** |

`demonstrate_estimator_is_var()` recovers the same matrix three ways — the doc's
finite-difference shock test, an OLS regression on a designed price panel, and a VAR(1)
horizon-0 impulse response — and asserts they coincide. **There is no superior predictor
hiding in the pamphlet; it is undergraduate demand-system econometrics.**

### Paper-inductance oscillation → the near-critical / limit-cycle regime

`oscillation.py` reads the "excess debt → self-destructive oscillation" claim as a
second-order damped oscillator (RLC analogue) whose damping ratio sets the regime
(laminar / limit-cycle / unstable), and maps a debt/GDP load onto the Lorenz drive `rho`,
reusing the **flow_regime Lorenz lens (#54)** and its Lyapunov/regime taxonomy **by
reference**. A super-critical (high-debt) load classifies **turbulent**; a low-debt control
classifies **laminar**.

## Phase 2 — the empirical confrontation (falsification pass)

Fixtures (`fixtures.py`) encode documented, cited reference figures (sources stated in-file):
1973/1979/2008 oil-shock magnitudes and published gasoline demand elasticities
(Hughes-Knittel-Sperling 2008; Espey 1998; Brons et al. 2008), and Reinhart-Rogoff debt/GDP
crisis episodes with their **resolution modes** — **including the Herndon-Ash-Pollin (2013)
correction** to the 90% "cliff".

| mechanism | verdict | why |
| --- | --- | --- |
| **MECH-1** shock-test estimator | **RELABELING** | reproduces the published gasoline elasticity within tolerance and gives an identical prediction to the econometric baseline — it *is* the baseline, it does not beat it |
| **MECH-2** gasoline→headache/violence/tavern behavioural claim | **REJECTED (no out-of-sample)** | the document offers no fitted coefficient and no out-of-sample test |
| **MECH-3** debt/GDP → instability (weak form) | **PARTLY_HOLDS** | a high-debt fixture classifies turbulent via the regime lens, but the sharp 90% causal cliff is refuted (HAP 2013) |
| **MECH-4** debt → population-negation as system-balancing (strong form) | **FALSIFIED** | every cited high-debt crisis resolved via default / restructuring / inflation / growth — **zero** via depopulation |

## Running it

```bash
# per-tooth tests
python -m pytest -q tests/test_silent_testbench_*.py
# contract teeth (VERIFIES + REJECTS over the claim fixtures)
python scripts/validate_silent_testbench.py
# emit the audit receipt (audit-only)
python -m open_ep_framework.silent_testbench --audit silent_testbench_audit.json
```

Deterministic and stdlib-only (hermetic CI; `jsonschema` only for the schema check).
The reference figures are static fixtures; a follow-up issue tracks wiring live EIA / BLS /
IMF / Reinhart-Rogoff feeds. This module feeds the **Phase-4 firewall synthesis**.
