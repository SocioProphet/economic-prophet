"""PHASE 2 -- the empirical confrontation (the falsification pass).

Each mechanism/estimator from the "Silent Weapons" document is confronted with the cited
historical reference fixtures and graded with a VERDICT and a deterministic RECEIPT. The
verdicts are honest by construction:

  MECH-1  shock-test estimator                 -> RELABELING
          (reproduces the published cross-price elasticity within tolerance because it IS
           ordinary elasticity/IRF estimation; it does not BEAT the econometric baseline).

  MECH-2  doc's gasoline->headache/violence/    -> REJECTED_NO_OUT_OF_SAMPLE
          tavern behavioural coefficient         (asserted with no fitted coefficient and
                                                  no out-of-sample test -- unfalsifiable as
                                                  stated, so it earns no predictive credit).

  MECH-3  debt/GDP -> instability (WEAK form)   -> PARTLY_HOLDS
          (a super-critical high-debt fixture classifies turbulent via the flow-regime lens;
           but the SHARP 90% causal cliff is refuted -- Herndon-Ash-Pollin 2013).

  MECH-4  debt -> population-negation as the    -> FALSIFIED
          system-balancing "resistance" (STRONG   (every cited high-debt crisis resolved via
          form)                                    default / restructuring / inflation /
                                                   growth; none via depopulation).

A control that never fires is suspect, so the teeth run in BOTH directions -- see
``scripts/validate_silent_testbench.py`` and the tests. Deterministic, stdlib-only.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field

from . import fixtures
from .oscillation import classify_debt_regime, oscillation_taxonomy_agrees
from .shock_estimator import DemandSystem, shock_test

# Verdict vocabulary (fixed).
RELABELING = "RELABELING"
PARTLY_HOLDS = "PARTLY_HOLDS"
FALSIFIED = "FALSIFIED"
REJECTED_NO_OOS = "REJECTED_NO_OUT_OF_SAMPLE"
VERIFIED = "VERIFIED"

ELASTICITY_TOL = 1e-3       # the shock test must recover a published elasticity this closely


@dataclass
class MechanismVerdict:
    mechanism_id: str
    doc_claim: str
    verdict: str
    finding: str
    evidence: dict = field(default_factory=dict)
    sources: list = field(default_factory=list)
    receipt: str = ""

    def sign(self) -> "MechanismVerdict":
        payload = {k: v for k, v in asdict(self).items() if k != "receipt"}
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        self.receipt = "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()
        return self


# --------------------------------------------------------------------------- #
# MECH-1: the shock-test estimator reproduces, but does not beat, econometrics.
# --------------------------------------------------------------------------- #
def _one_good_system(own_price_elasticity: float) -> DemandSystem:
    """A minimal one-good log-linear demand system with a chosen own-price elasticity."""
    return DemandSystem(goods=("gasoline",), elasticities=[[own_price_elasticity]],
                        log_intercepts=[0.0])


def confront_shock_estimator() -> MechanismVerdict:
    """Run the doc's shock test on a published gasoline elasticity; grade RELABELING.

    We seed a demand system with the Hughes-Knittel-Sperling short-run elasticity, run the
    shock test, and confirm it recovers that same elasticity. We then compare the shock
    test's predicted quantity response to a 1979 gasoline price shock against the standard
    econometric baseline (the published elasticity applied directly): they are identical,
    so the doc's estimator does NOT beat the baseline -- it is a relabeling of it.
    """
    published = next(e for e in fixtures.GASOLINE_ELASTICITIES
                     if e.era == "2001-2006" and e.horizon == "short_run")
    system = _one_good_system(published.value)
    result = shock_test(system, base_prices=[3.0])
    recovered = result.recovered_elasticities[0][0]
    reproduces = abs(recovered - published.value) < ELASTICITY_TOL

    # Apply a documented shock and compare predictions. Baseline (econometrics) and the
    # shock-test estimator use the SAME elasticity -> the SAME prediction -> zero edge.
    shock = next(s for s in fixtures.OIL_SHOCKS if s.year == 1979)
    d_ln_p = math.log1p(shock.gasoline_pct_change)
    baseline_pred_d_ln_q = published.value * d_ln_p
    shocktest_pred_d_ln_q = recovered * d_ln_p
    prediction_edge = abs(shocktest_pred_d_ln_q - baseline_pred_d_ln_q)
    beats_baseline = prediction_edge > ELASTICITY_TOL   # expected: False

    verdict = RELABELING if (reproduces and not beats_baseline) else "INCONCLUSIVE"
    finding = (
        "The shock test recovers the published short-run gasoline elasticity "
        f"({recovered:.4f} vs {published.value:.4f}) and yields an IDENTICAL prediction to "
        "the econometric baseline (edge={:.2e}). The estimator IS cross-price-elasticity / "
        "impulse-response identification; it does not beat ordinary econometrics."
    ).format(prediction_edge)
    return MechanismVerdict(
        mechanism_id="MECH-1-shock-test-estimator",
        doc_claim="A shock test recovers a stable coefficient matrix [a_jk] that predicts "
                  "aggregate public reaction better than ordinary economics.",
        verdict=verdict, finding=finding,
        evidence={
            "seeded_published_elasticity": published.value,
            "shock_test_recovered_elasticity": recovered,
            "reproduces_within_tol": reproduces,
            "tolerance": ELASTICITY_TOL,
            "baseline_pred_d_ln_q": baseline_pred_d_ln_q,
            "shocktest_pred_d_ln_q": shocktest_pred_d_ln_q,
            "prediction_edge_over_baseline": prediction_edge,
            "beats_baseline": beats_baseline,
            "estimator_identity": "a_jk == e_jk == VAR impulse response (see shock_estimator)",
        },
        sources=[published.source, shock.source],
    ).sign()


# --------------------------------------------------------------------------- #
# MECH-2: the behavioural claim offers no fitted, out-of-sample coefficient.
# --------------------------------------------------------------------------- #
def confront_behavioral_claim() -> MechanismVerdict:
    """Grade the doc's gasoline->headache/violence/tavern claim: REJECTED (no OOS)."""
    claim = fixtures.DOC_BEHAVIORAL_CLAIM
    has_coeff = claim["offered_coefficient"] is not None
    has_oos = bool(claim["offered_out_of_sample_test"])
    verdict = REJECTED_NO_OOS if not (has_coeff and has_oos) else VERIFIED
    finding = (
        "The document asserts a stable link from a gasoline-price shock to behavioural "
        "outputs (headache, hostility, violence, tavern attendance) but offers NO fitted "
        "coefficient and NO out-of-sample test. A prediction asserted without an "
        "out-of-sample check earns no predictive credit and is rejected as stated."
    )
    return MechanismVerdict(
        mechanism_id="MECH-2-behavioral-shock-claim",
        doc_claim=claim["source"],
        verdict=verdict, finding=finding,
        evidence={
            "claimed_outputs": claim["claimed_outputs"],
            "offered_coefficient": claim["offered_coefficient"],
            "offered_out_of_sample_test": claim["offered_out_of_sample_test"],
        },
        sources=[claim["source"]],
    ).sign()


# --------------------------------------------------------------------------- #
# MECH-3: debt/GDP -> instability, WEAK form, partly holds.
# --------------------------------------------------------------------------- #
def confront_debt_oscillation_weak() -> MechanismVerdict:
    """Grade the weak form: a high-debt near-critical fixture reads turbulent -> PARTLY_HOLDS.

    Uses the Greece 2012 peak debt/GDP as the high-debt fixture and a low-debt control; the
    flow-regime Lorenz lens (#54) classifies the high-debt load turbulent and the low-debt
    load laminar. But the SHARP 90% causal cliff is refuted (Herndon-Ash-Pollin 2013), so the
    verdict is PARTLY_HOLDS, not VERIFIED.
    """
    high = next(c for c in fixtures.DEBT_CRISES if c.episode.startswith("Greece"))
    high_v = classify_debt_regime(high.peak_debt_gdp)
    low_v = classify_debt_regime(0.20)
    weak_form_dynamics = (high_v.weak_form_holds and not low_v.flow.is_turbulent
                          and oscillation_taxonomy_agrees(high_v)
                          and oscillation_taxonomy_agrees(low_v))
    thr = fixtures.DEBT_GROWTH_THRESHOLD
    verdict = PARTLY_HOLDS if weak_form_dynamics else "INCONCLUSIVE"
    finding = (
        "Weak form (high debt -> instability) holds as a DYNAMICAL reading: the high-debt "
        f"fixture (debt/GDP={high.peak_debt_gdp}) maps super-critical and classifies "
        f"'{high_v.flow.regime}' (lambda={high_v.flow.lambda_max}), while the low-debt "
        f"control classifies '{low_v.flow.regime}'. But the SHARP 90% causal cliff is "
        "refuted (Herndon-Ash-Pollin 2013): corrected, above-90% growth is ~2.2%, not "
        "negative, and no sharp threshold survives. Hence PARTLY_HOLDS, not VERIFIED."
    )
    return MechanismVerdict(
        mechanism_id="MECH-3-debt-oscillation-weak",
        doc_claim="Excess public debt drives a self-destructive economic oscillation "
                  "(paper-inductance / near-critical instability).",
        verdict=verdict, finding=finding,
        evidence={
            "high_debt_gdp": high.peak_debt_gdp,
            "high_debt_regime": high_v.flow.regime,
            "high_debt_lambda": high_v.flow.lambda_max,
            "high_debt_super_critical": high_v.near_or_super_critical,
            "low_debt_regime": low_v.flow.regime,
            "sharp_90pct_cliff_status": thr.status,
        },
        sources=[high.source, thr.source, *thr.corrections],
    ).sign()


# --------------------------------------------------------------------------- #
# MECH-4: debt -> population-negation, STRONG form, FALSIFIED.
# --------------------------------------------------------------------------- #
def confront_debt_population_negation_strong() -> MechanismVerdict:
    """Grade the strong form: every high-debt crisis resolved financially -> FALSIFIED."""
    crises = fixtures.DEBT_CRISES
    resolved_financially = [c for c in crises if not c.population_negation]
    by_population_negation = [c for c in crises if c.population_negation]
    modes = sorted({c.resolution_mode for c in crises})
    # STRONG form predicts population-negation as the balancing resistance; the record shows
    # zero such episodes -> the claim is falsified by the historical resolution modes.
    falsified = (len(by_population_negation) == 0 and len(resolved_financially) == len(crises))
    verdict = FALSIFIED if falsified else "NOT_FALSIFIED"
    finding = (
        "Strong form (population-negation/genocide as the system-balancing 'resistance') is "
        f"FALSIFIED: all {len(crises)} cited high-debt crises resolved through financial "
        f"mechanisms ({', '.join(modes)}); ZERO resolved via population-negation. High debt "
        "is discharged by default, restructuring, inflation, growth, or financial repression "
        "-- not by depopulation."
    )
    return MechanismVerdict(
        mechanism_id="MECH-4-debt-population-negation-strong",
        doc_claim="The controller balances an over-indebted economy by negating (reducing) "
                  "the population -- the public is the resistor that dissipates the energy.",
        verdict=verdict, finding=finding,
        evidence={
            "n_crises": len(crises),
            "resolution_modes": modes,
            "episodes_resolved_by_population_negation": len(by_population_negation),
            "episodes": [{"episode": c.episode, "year": c.year,
                          "peak_debt_gdp": c.peak_debt_gdp,
                          "resolution_mode": c.resolution_mode} for c in crises],
        },
        sources=[c.source for c in crises],
    ).sign()


# --------------------------------------------------------------------------- #
# The full confrontation report.
# --------------------------------------------------------------------------- #
def run_confrontation() -> dict:
    """Run all mechanism confrontations and assemble the audit report."""
    verdicts = [
        confront_shock_estimator(),
        confront_behavioral_claim(),
        confront_debt_oscillation_weak(),
        confront_debt_population_negation_strong(),
    ]
    expected = {
        "MECH-1-shock-test-estimator": RELABELING,
        "MECH-2-behavioral-shock-claim": REJECTED_NO_OOS,
        "MECH-3-debt-oscillation-weak": PARTLY_HOLDS,
        "MECH-4-debt-population-negation-strong": FALSIFIED,
    }
    all_as_expected = all(v.verdict == expected[v.mechanism_id] for v in verdicts)
    return {
        "document": "Silent Weapons for Quiet Wars",
        "scope": "audit_only_falsification_not_operationalization",
        "phase": "phase-1-2-simulator-and-confrontation",
        "mechanisms": [asdict(v) for v in verdicts],
        "verdict_summary": {v.mechanism_id: v.verdict for v in verdicts},
        "all_verdicts_as_expected": all_as_expected,
        "honesty_note": (
            "Reproducing the document's mechanism is NOT confirming its conspiracy. The "
            "shock-test estimator is ordinary econometrics (RELABELING); the strong "
            "debt->depopulation claim is FALSIFIED by the historical record."
        ),
    }
