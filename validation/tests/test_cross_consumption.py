"""Tooth #1 -- cross-consumption conformance.

Import the merged risk kernel (economic-prophet #43/#44) and the memory-mesh #50
``risk_distribution_F`` descriptor shape, and prove the kernel ACTUALLY consumes
the regime-F: at EQUAL VARIANCE, a fat-tailed regime yields a STRICTLY larger
tail measure (ES) than a Gaussian regime. A wiring where swapping the regime does
not move the tail measure would mean the F is not really consumed -- REJECTED.
"""
import json
import math
from pathlib import Path

import pytest

from open_ep_framework.risk_measures import risk
from validation.regime_f import (
    build_distribution_from_regime_f,
    is_fat_tailed,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

# Equal variance across every regime under test: a 4%/step vol.
TARGET_VARIANCE = 0.04 ** 2
# Tail confidences with a robust, deterministic gap between thin and fat tails.
ALPHAS = (0.975, 0.99)


def _descriptor(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())["risk_distribution_F"]


def _F(name: str):
    return build_distribution_from_regime_f(
        _descriptor(name), n=20000, target_variance=TARGET_VARIANCE, seed=7
    )


def test_fixtures_are_the_memory_mesh_shape():
    # The fixtures are the verbatim memory-mesh #50 descriptors: the seam is real.
    for name in ("regime_f_gaussian.json", "regime_f_fbm-h07.json", "regime_f_multifractal.json"):
        d = json.loads((FIXTURES / name).read_text())["risk_distribution_F"]
        assert d["raroc_interface"] == "risk(F, reference, kernel, horizon)"
        assert "family" in d and "tail_class" in d


def test_regimes_classify_by_tail_class():
    assert is_fat_tailed(_descriptor("regime_f_gaussian.json")) is False
    assert is_fat_tailed(_descriptor("regime_f_fbm-h07.json")) is False  # fBm is marginally Normal
    assert is_fat_tailed(_descriptor("regime_f_multifractal.json")) is True


def test_equal_variance_across_regimes():
    # The comparison is only honest if the variances really are equal.
    fg = _F("regime_f_gaussian.json")
    ff = _F("regime_f_multifractal.json")
    vg = risk(fg, "stddev").value ** 2
    vf = risk(ff, "stddev").value ** 2
    assert math.isclose(vg, vf, rel_tol=1e-9), (vg, vf)
    assert math.isclose(vg, TARGET_VARIANCE, rel_tol=1e-9)


def test_fat_tailed_ES_strictly_exceeds_gaussian_at_equal_variance():
    # THE tooth: regime choice changes the price. Fat-tailed F > Gaussian F on ES.
    fg = _F("regime_f_gaussian.json")
    ff = _F("regime_f_multifractal.json")
    for alpha in ALPHAS:
        es_gauss = risk(fg, "expected_shortfall", alpha=alpha).value
        es_fat = risk(ff, "expected_shortfall", alpha=alpha).value
        # STRICT: swapping Gaussian -> fat-tailed MUST raise the tail measure.
        assert es_fat > es_gauss, (alpha, es_fat, es_gauss)
        # and by a real margin, not float noise.
        assert es_fat - es_gauss > 1e-4, (alpha, es_fat - es_gauss)


def test_reject_a_wiring_that_ignores_the_F():
    # If the tail measure did NOT respond to the regime swap, the F would not be
    # consumed -- that wiring is REJECTED. We prove the response is non-trivial.
    fg = _F("regime_f_gaussian.json")
    ff = _F("regime_f_multifractal.json")
    es_gauss = risk(fg, "expected_shortfall", alpha=0.99).value
    es_fat = risk(ff, "expected_shortfall", alpha=0.99).value
    relative_move = (es_fat - es_gauss) / es_gauss
    assert relative_move > 0.05, f"regime swap moved ES by only {relative_move:.4%}; F not consumed"


def test_same_F_many_lenses_all_consume_the_regime():
    # ES, a tail-sensitive high-order LPM and excess kurtosis are all lenses on the
    # same F. At EQUAL variance the low moments coincide (that is the whole point of
    # matching variance); only the TAIL-weighted lenses separate the regimes -- and
    # they must, or the fat tail is not being consumed.
    from open_ep_framework.risk_measures import excess_kurtosis, lpm
    fg = _F("regime_f_gaussian.json")
    ff = _F("regime_f_multifractal.json")
    # excess kurtosis: ~0 for Gaussian, strongly positive for the fat-tailed regime.
    assert abs(excess_kurtosis(list(fg.samples))) < 0.1
    assert excess_kurtosis(list(ff.samples)) > 1.0
    # order-4 (extreme-averse) lower partial moment is tail-dominated -> larger for fat.
    assert lpm(list(ff.samples), 0.0, 4) > lpm(list(fg.samples), 0.0, 4)
    # VaR<=ES for each F, and ES coherent flag set -- the single interface holds.
    for F in (fg, ff):
        es = risk(F, "expected_shortfall", alpha=0.99)
        var = risk(F, "var", alpha=0.99)
        assert es.value >= var.value
        assert es.coherent is True
        assert var.coherent is False


def test_pure_fBm_gaussian_marginal_does_not_change_the_marginal_tail():
    # Honest residual: a memoryless-Gaussian regime and a long-memory fBm regime
    # have the SAME Normal marginal, so at equal variance the kernel (which scores
    # the marginal F) prices the same tail. Long memory (Hurst) is NOT yet priced
    # into the one-point tail -- only tail_class is. Tracked as a follow-up.
    fg = _F("regime_f_gaussian.json")
    fbm = _F("regime_f_fbm-h07.json")
    es_gauss = risk(fg, "expected_shortfall", alpha=0.99).value
    es_fbm = risk(fbm, "expected_shortfall", alpha=0.99).value
    assert math.isclose(es_gauss, es_fbm, rel_tol=1e-6), (es_gauss, es_fbm)
