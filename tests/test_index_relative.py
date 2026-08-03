"""Per-tooth mutation tests for the index-relative benchmarking contract (IRB-1)."""
import pytest

from open_ep_framework.benchmarking.index_relative import (
    Decomposition, IndexRelativeError, check_book, check_reconciliation,
    compare_cross_frame, cross_sectional_ranks, decompose, idiosyncratic_differential,
    reject_absolute_cross_frame, require_baseline, require_decomposed, run_cohort,
)

BASE = [0.012, 0.009, 0.015, 0.011, 0.008, 0.013, 0.010, 0.014]
MEAS = [0.020, 0.014, 0.026, 0.019, 0.012, 0.023, 0.017, 0.024]


# --- TOOTH: the split reconciles in LEVEL and in VARIANCE (VERIFIES) -------- #
def test_decomposition_reconciles_level_and_variance():
    d = decompose(MEAS, BASE)
    check_reconciliation(d, MEAS)  # must not raise
    # level: beta*B_t + eps_t == X_t exactly
    for st, et, xt in zip(d.systematic, d.epsilon, MEAS):
        assert abs(st + et - xt) < 1e-12
    # variance: beta^2 var(B) + var(eps) == var(X)
    assert abs(d.beta ** 2 * d.var_baseline + d.var_epsilon - d.var_total) < 1e-12
    assert abs(d.systematic_share + d.idiosyncratic_share - 1.0) < 1e-12


# --- TOOTH: a non-reconciling split is REJECTED (mutation) ------------------ #
def test_non_reconciling_variance_rejected():
    d = decompose(MEAS, BASE)
    # mutate: keep the level identity but break orthogonality by inflating var_epsilon
    broken = Decomposition(
        beta=d.beta, alpha=d.alpha, epsilon=d.epsilon, systematic=d.systematic,
        var_baseline=d.var_baseline, var_epsilon=d.var_epsilon * 2.0,
        var_total=d.var_total, n=d.n,
    )
    with pytest.raises(IndexRelativeError):
        check_reconciliation(broken, MEAS)


def test_non_reconciling_level_rejected():
    d = decompose(MEAS, BASE)
    mutated_x = list(MEAS)
    mutated_x[0] += 0.05  # X no longer equals beta*B + eps at t=0
    with pytest.raises(IndexRelativeError):
        check_reconciliation(d, mutated_x)


# --- TOOTH: a cohort with no baseline index is REJECTED --------------------- #
def test_missing_baseline_rejected():
    cohort = {"key": {"asset_class": "corporate_credit", "market": "us_ig"},
              "measure": {"series": MEAS}}
    with pytest.raises(IndexRelativeError):
        require_baseline(cohort)


def test_missing_required_key_axis_rejected():
    cohort = {"key": {"asset_class": "corporate_credit"},  # no market
              "baseline_index": {"series": BASE}}
    with pytest.raises(IndexRelativeError):
        require_baseline(cohort)


# --- TOOTH: a measure not decomposed is REJECTED ---------------------------- #
def test_measure_not_decomposed_rejected():
    with pytest.raises(IndexRelativeError):
        require_decomposed({"decomposed": False, "series": MEAS}, "c")
    with pytest.raises(IndexRelativeError):
        require_decomposed({"series": []}, "c")
    # a decomposed measure with a series is admitted
    require_decomposed({"decomposed": True, "series": MEAS}, "c")


# --- TOOTH: a flat baseline (no systematic factor) is REJECTED -------------- #
def test_flat_baseline_rejected():
    with pytest.raises(IndexRelativeError):
        decompose(MEAS, [0.01] * len(MEAS))


# --- TOOTH: the idiosyncratic differential is UNIT-FREE (scale-invariant) --- #
def test_idiosyncratic_z_is_scale_invariant():
    d1 = decompose(MEAS, BASE)
    z1 = idiosyncratic_differential(d1).idiosyncratic_z
    # scale the whole measure by 1000 (e.g. a different currency's absolute level):
    d2 = decompose([m * 1000 for m in MEAS], BASE)
    z2 = idiosyncratic_differential(d2).idiosyncratic_z
    assert abs(z1 - z2) < 1e-9  # the dimensionless differential does not move


def test_cross_sectional_ranks():
    assert cross_sectional_ranks([0.3, 0.1, 0.2]) == [3.0, 1.0, 2.0]
    # ties share the average rank
    assert cross_sectional_ranks([0.5, 0.5, 0.9]) == [1.5, 1.5, 3.0]


# --- TOOTH: a cross-frame comparison on an ABSOLUTE basis is REJECTED ------- #
def _receipts():
    return {
        "us": {"key": {"region": "US", "market": "us_ig"}, "currency": "USD",
               "differential": {"idiosyncratic_z": 1.2, "spread_to_baseline": 0.01}},
        "eu": {"key": {"region": "EU", "market": "eu_ig"}, "currency": "EUR",
               "differential": {"idiosyncratic_z": 0.7, "spread_to_baseline": 0.008}},
    }


def test_absolute_cross_frame_rejected():
    r = _receipts()
    with pytest.raises(IndexRelativeError):
        reject_absolute_cross_frame({"left": "us", "right": "eu", "basis": "absolute_level"}, r)


def test_dimensionless_cross_frame_admitted():
    r = _receipts()
    out = compare_cross_frame({"left": "us", "right": "eu", "basis": "idiosyncratic_z"}, r)
    assert out["cross_frame"] is True and out["unit_free"] is True
    assert abs(out["differential"] - 0.5) < 1e-9


def test_absolute_same_frame_admitted():
    # absolute is fine WITHIN a single frame (same currency/region/market)
    r = {
        "a": {"key": {"region": "US", "market": "us_ig"}, "currency": "USD",
              "differential": {"idiosyncratic_z": 1.0, "spread_to_baseline": 0.01}},
        "b": {"key": {"region": "US", "market": "us_ig"}, "currency": "USD",
              "differential": {"idiosyncratic_z": 0.5, "spread_to_baseline": 0.005}},
    }
    reject_absolute_cross_frame({"left": "a", "right": "b", "basis": "absolute"}, r)  # no raise


# --- end-to-end: the shipped valid book passes every tooth ------------------ #
def test_valid_book_end_to_end():
    import json
    from pathlib import Path
    book = json.loads(
        (Path(__file__).resolve().parents[1] / "examples" / "benchmarking"
         / "index_relative_book.valid.json").read_text()
    )
    receipt = check_book(book)
    assert receipt["cohort_count"] == 2
    assert all(c["reconciles"]["level"] and c["reconciles"]["variance"] for c in receipt["cohorts"])
    assert all(cmp["unit_free"] for cmp in receipt["comparisons"])
