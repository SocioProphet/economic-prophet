"""Per-tooth tests: the Phase-2 confrontation grades each mechanism honestly."""
from open_ep_framework.silent_testbench.confront import (
    FALSIFIED, PARTLY_HOLDS, REJECTED_NO_OOS, RELABELING, confront_behavioral_claim,
    confront_debt_oscillation_weak, confront_debt_population_negation_strong,
    confront_shock_estimator, run_confrontation,
)
from open_ep_framework.silent_testbench import fixtures


# --- TOOTH: MECH-1 is a RELABELING (reproduces but does not beat baseline) ---- #
def test_mech1_relabeling():
    v = confront_shock_estimator()
    assert v.verdict == RELABELING
    assert v.evidence["reproduces_within_tol"] is True
    assert v.evidence["beats_baseline"] is False
    assert v.evidence["prediction_edge_over_baseline"] < 1e-3
    assert v.receipt.startswith("sha256:")


# --- TOOTH: MECH-2 behavioural claim is REJECTED (no out-of-sample) ---------- #
def test_mech2_rejected_no_oos():
    v = confront_behavioral_claim()
    assert v.verdict == REJECTED_NO_OOS
    assert v.evidence["offered_coefficient"] is None
    assert v.evidence["offered_out_of_sample_test"] is False


# --- TOOTH: MECH-3 weak form PARTLY_HOLDS (turbulent regime, cliff refuted) --- #
def test_mech3_partly_holds():
    v = confront_debt_oscillation_weak()
    assert v.verdict == PARTLY_HOLDS
    assert v.evidence["high_debt_regime"] == "turbulent"
    assert v.evidence["low_debt_regime"] == "laminar"
    # the HAP correction must be cited in the sources
    assert any("Herndon" in s for s in v.sources)


# --- TOOTH: MECH-4 strong form FALSIFIED (no episode via population negation) -- #
def test_mech4_falsified():
    v = confront_debt_population_negation_strong()
    assert v.verdict == FALSIFIED
    assert v.evidence["episodes_resolved_by_population_negation"] == 0
    assert v.evidence["n_crises"] == len(fixtures.DEBT_CRISES)


# --- TOOTH: fixtures encode the counter-evidence (no depopulation resolution) -- #
def test_no_crisis_resolved_by_population_negation():
    assert all(c.population_negation is False for c in fixtures.DEBT_CRISES)
    modes = {c.resolution_mode for c in fixtures.DEBT_CRISES}
    assert modes <= {"default", "restructuring", "inflation", "growth", "financial_repression"}


# --- TOOTH: the sharp 90% cliff is recorded as refuted, not endorsed ---------- #
def test_debt_growth_threshold_records_correction():
    thr = fixtures.DEBT_GROWTH_THRESHOLD
    assert thr.status == "weak_association_survives_sharp_cliff_refuted"
    assert any("Herndon" in c for c in thr.corrections)


# --- TOOTH: the full report is all-as-expected and every verdict has a receipt  #
def test_full_confrontation_report():
    report = run_confrontation()
    assert report["all_verdicts_as_expected"] is True
    assert report["scope"] == "audit_only_falsification_not_operationalization"
    for mech in report["mechanisms"]:
        assert mech["receipt"].startswith("sha256:")
    assert report["verdict_summary"] == {
        "MECH-1-shock-test-estimator": RELABELING,
        "MECH-2-behavioral-shock-claim": REJECTED_NO_OOS,
        "MECH-3-debt-oscillation-weak": PARTLY_HOLDS,
        "MECH-4-debt-population-negation-strong": FALSIFIED,
    }
