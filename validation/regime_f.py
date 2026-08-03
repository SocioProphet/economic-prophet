"""Consume the memory-mesh ``risk_distribution_F`` descriptor with the merged kernel.

The memory-regime characterizer (memory-mesh #50) emits, per characterized
series, a ``risk_distribution_F`` block of the shape::

    {
      "family": "fractional_brownian_motion" | "gaussian" | "multifractal_mmar" | ...,
      "params": {"hurst_H": ..., "sigma": ..., "df": ...},
      "tail_class": "gaussian" | "multifractal" | "heavy" | "student_t",
      "kernel": "power_law" | "delta" | ...,
      "horizon_unit": "step",
      "raroc_interface": "risk(F, reference, kernel, horizon)"
    }

``raroc_interface`` names the economic-prophet risk kernel directly. This module
is the *adapter* that honours that contract: it turns a descriptor into a real
``open_ep_framework.risk_measures.LossDistribution`` and hands it to
``risk(F, ...)``. It is consume-not-fork -- no estimator from memory-mesh is
copied; only the emitted descriptor SHAPE is read.

Determinism: Gaussian marginals are drawn on a stratified inverse-CDF grid
(seed-free, low-discrepancy, so empirical ES converges tightly to the closed
form); fat-tailed marginals use a seeded Student-t. All series are rescaled to an
exact target variance so equal-variance comparisons are exact.
"""
from __future__ import annotations

import math
import random
from typing import Sequence

from open_ep_framework.risk_measures import LossDistribution

# Tail classes the memory-mesh contract can carry. A "gaussian" tail is thin; the
# rest are fat -- a heavier-than-normal loss tail at the SAME variance.
GAUSSIAN_TAIL_CLASSES = {"gaussian", "normal", "thin"}
FAT_TAIL_CLASSES = {"multifractal", "heavy", "fat", "student_t", "student-t", "power_law", "levy"}

# Families whose marginal is Gaussian even though the *process* has memory.
# fGn / fBm are marginally Normal: long memory lives in the autocovariance, not
# in the one-point tail. That distinction is exactly what tooth #1 surfaces.
_GAUSSIAN_MARGINAL_FAMILIES = {"gaussian", "iid_gaussian", "fractional_brownian_motion", "fgn"}

_DEFAULT_STUDENT_T_DF = 3
_DEFAULT_N = 20000


# --------------------------------------------------------------------------- #
# normal helpers (stdlib only)
# --------------------------------------------------------------------------- #
def norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def inv_norm_cdf(p: float) -> float:
    """Inverse standard-normal CDF (Acklam) refined with one Halley step.

    Acklam's rational approximation is good to ~1e-9; a single Halley correction
    against ``math.erf`` pushes it to near machine precision, which the analytic
    ES constant needs.
    """
    if not (0.0 < p < 1.0):
        raise ValueError("inv_norm_cdf requires 0 < p < 1")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1.0 - 0.02425
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        x = (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1.0)
    elif p > phigh:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        x = -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1.0)
    else:
        q = p - 0.5
        r = q * q
        x = (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1.0)
    # one Halley refinement step
    e = norm_cdf(x) - p
    u = e / norm_pdf(x)
    x = x - u / (1.0 + x * u / 2.0)
    return x


def analytic_es_normal(mu: float, sigma: float, alpha: float) -> float:
    """Closed-form Expected Shortfall of a Normal LOSS distribution.

    ``ES_alpha = mu + sigma * phi(Phi^{-1}(alpha)) / (1 - alpha)`` -- the standard
    tail-average of a Gaussian loss with mean ``mu`` and standard deviation
    ``sigma``. This is the external reference the kernel's numeric ES must match.
    """
    z = inv_norm_cdf(alpha)
    return mu + sigma * norm_pdf(z) / (1.0 - alpha)


# --------------------------------------------------------------------------- #
# sample generators (deterministic)
# --------------------------------------------------------------------------- #
def _sample_variance(xs: Sequence[float]) -> float:
    n = len(xs)
    m = sum(xs) / n
    return sum((x - m) ** 2 for x in xs) / (n - 1)


def rescale(xs: Sequence[float], target_mean: float, target_sigma: float) -> list[float]:
    """Affine-rescale ``xs`` to an EXACT target mean and sample std.

    Because every returned series is rescaled to the same target std, two series
    built this way have identical sample variance to float precision -- which is
    what makes the equal-variance tail comparison exact rather than approximate.
    """
    n = len(xs)
    m = sum(xs) / n
    s = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    if s <= 0:
        raise ValueError("cannot rescale a degenerate (zero-variance) series")
    return [target_mean + (x - m) / s * target_sigma for x in xs]


def gaussian_returns(n: int, mu: float = 0.0, sigma: float = 1.0) -> list[float]:
    """Deterministic Gaussian return series on a stratified inverse-CDF grid.

    Seed-free and low-discrepancy: the empirical tail mean converges to the closed
    form far faster than i.i.d. draws, so the ES-vs-analytic tooth is tight.
    """
    return [mu + sigma * inv_norm_cdf((i + 0.5) / n) for i in range(n)]


def student_t_returns(n: int, df: int, seed: int, mu: float = 0.0, sigma: float = 1.0) -> list[float]:
    """Seeded Student-t return series (fat left tail; ``df`` small == fatter).

    Drawn as ``z / sqrt(chi2_df / df)`` from stdlib gaussians. Scale ``sigma`` here
    is the pre-standardisation scale; callers that need an exact variance should
    pass the result through :func:`rescale`.
    """
    rng = random.Random(seed)
    out: list[float] = []
    df = max(3, int(df))  # df<=2 has no finite variance; equal-variance test needs one
    for _ in range(n):
        z = rng.gauss(0.0, 1.0)
        chi2 = sum(rng.gauss(0.0, 1.0) ** 2 for _ in range(df))
        t = z / math.sqrt(chi2 / df) if chi2 > 0 else z
        out.append(mu + sigma * t)
    return out


# --------------------------------------------------------------------------- #
# the adapter: risk_distribution_F descriptor -> LossDistribution
# --------------------------------------------------------------------------- #
def is_fat_tailed(descriptor: dict) -> bool:
    """Whether a ``risk_distribution_F`` descriptor carries a fat loss tail."""
    tail = str(descriptor.get("tail_class", "")).lower()
    if tail in FAT_TAIL_CLASSES:
        return True
    if tail in GAUSSIAN_TAIL_CLASSES:
        return False
    # fall back to family when tail_class is absent/unknown
    fam = str(descriptor.get("family", "")).lower()
    return fam not in _GAUSSIAN_MARGINAL_FAMILIES


def build_distribution_from_regime_f(
    descriptor: dict,
    *,
    n: int = _DEFAULT_N,
    target_variance: float | None = None,
    seed: int = 0,
) -> LossDistribution:
    """Turn a memory-mesh ``risk_distribution_F`` descriptor into a kernel F.

    The descriptor SHAPE (``family`` / ``params`` / ``tail_class``) is the
    memory-mesh #50 contract; this reads it and returns a
    ``LossDistribution`` the merged risk kernel can score. When ``target_variance``
    is given the marginal is rescaled to exactly that variance, so two descriptors
    can be compared at equal variance -- isolating the effect of ``tail_class``.

    Mapping (marginal, one-point):
      * Gaussian-marginal families (gaussian / iid_gaussian / fBm / fGn) -> Normal
        marginal. NOTE: fBm/fGn are marginally Normal; their long memory lives in
        the autocovariance, not the one-point tail.
      * fat ``tail_class`` (multifractal / heavy / student_t) -> Student-t marginal
        with ``params.df`` (default df=3).
    """
    params = descriptor.get("params", {}) or {}
    sigma = float(params.get("sigma", 1.0)) or 1.0

    if is_fat_tailed(descriptor):
        df = int(params.get("df", _DEFAULT_STUDENT_T_DF))
        raw = student_t_returns(n, df=df, seed=seed, mu=0.0, sigma=1.0)
        source = f"regime_f:{descriptor.get('family', 'fat')}:tail={descriptor.get('tail_class')}"
    else:
        raw = gaussian_returns(n, mu=0.0, sigma=1.0)
        source = f"regime_f:{descriptor.get('family', 'gaussian')}:tail={descriptor.get('tail_class')}"

    if target_variance is not None:
        raw = rescale(raw, 0.0, math.sqrt(target_variance))
    else:
        raw = rescale(raw, 0.0, sigma)

    return LossDistribution(tuple(raw), horizon_days=1, source=source, seed=seed)
