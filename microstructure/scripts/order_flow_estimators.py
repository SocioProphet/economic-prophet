#!/usr/bin/env python3
"""Deterministic, stdlib-only order-flow estimators for market microstructure.

Order flow is a MARKED POINT PROCESS in event time: events arrive (arrival
intensity), rest and are cancelled (decay / competing hazard), and are filled
(execution / thinning conditional on queue position), each carrying a mark
(signed size). This module is the honest, seeded core the OrderFlowProcess
contract is built on -- analytic where possible, seeded PRNG otherwise, so CI is
reproducible.

Grounding
---------
  * Arrival intensity family -- Poisson (constant lambda, i.i.d. exponential
    interarrivals) -> Hawkes self-exciting lambda(t)=mu+sum phi(t-t_i) with an
    exponential OR power-law kernel phi, whose BRANCHING RATIO n=int phi governs
    stability (n<1 stationary; n>=1 explosive -- the flash-crash edge) -> ACD
    (autoregressive conditional duration: autocorrelated, non-exponential
    durations a Poisson fit misses).
  * Branching ratio is read from the index of dispersion for counts (Fano
    factor). For a stationary Hawkes process Var(N_T)/E(N_T) -> (1-n)^-2, so
    n_hat = 1 - 1/sqrt(IDC); a Poisson stream has IDC=1 => n_hat=0.
  * Kernel discrimination (exp vs power-law self-excitation) is the SAME
    long-memory read the memory-mesh regime characterizer uses: the Hurst
    exponent of the counting process. Exponential self-excitation is
    short-range (H~0.5); power-law self-excitation is long-memory (H>0.5).
  * Marks are heavy-tailed (power-law); the tail index is read with a Hill
    estimator and the loss side is exposed as an F for the RAROC risk kernel.
  * LOB micro-signals: order-flow imbalance (OFI) and a Kyle-lambda price-impact
    slope (impact per unit signed volume), shaped as the liquidity input the
    vol-surface / FTP layer consumes.

Consume-not-fork
----------------
The regime labels (memoryless / short_decaying / long_memory / chaotic), the
``risk_distribution_F`` block shape, and the SHA-256 hash-chain receipt are the
memory-mesh MemoryRegimeCharacterization contract's, reused BY REFERENCE -- not
redefined. The Kyle-lambda / effective-volume / signed-flow-Hurst triple is
shaped for economic-prophet ``market_instruments.liquidity_premium(volume,
regime_hurst, base_bps)``; the marks F is shaped for ``risk_measures.risk(F,
kernel, reference, horizon)`` (LossDistribution samples).

No network, no heavy deps: pure ``math`` + ``random``. Determinism is by
explicit seed so CI teeth are reproducible. numpy is intentionally NOT used
(the home package declares zero runtime dependencies).
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import random
from typing import List, Optional, Sequence, Tuple

# Estate min-n: a characterization on fewer than this many events is only ever
# `provisional` (mirrors the estate min-n>=30 discipline).
MIN_N = 30

# --------------------------------------------------------------------------- #
# Decision thresholds (documented in microstructure/docs/order-flow-process.md)
# --------------------------------------------------------------------------- #
IDC_EXCITE = 1.5      # index of dispersion above this => self-excitation present
N_CRITICAL = 0.90     # branching ratio at/above this (but <1) => near-critical edge (chaotic)
H_LONG = 0.62         # counting-process ensemble Hurst at/above this => long-memory (power-law) kernel
DUR_AUTOCORR_SIGNIF = 0.10   # |lag-1 duration autocorr| above this => ACD memory
FAT_TAIL_KURTOSIS = 1.5      # excess kurtosis above this => heavy-tailed marks
HILL_TAIL_FINITE = 4.0       # Hill tail index below this => a genuinely heavy (power-law) tail


# --------------------------------------------------------------------------- #
# Receipt: proof-artifact-spine SHA-256 hash-chain link (reused BY REFERENCE
# from the memory-mesh MemoryRegimeCharacterization contract).
# --------------------------------------------------------------------------- #
def receipt_content_hash(record: dict) -> str:
    """SHA-256 over the canonical JSON of a record with receipt.contentHash
    blanked.

    Scope note: SHA-256 is the FIPS-180-4 *algorithm*; using it here is NOT a
    claim of FIPS-140 cryptographic-module validation.
    """
    clone = copy.deepcopy(record)
    if isinstance(clone.get("receipt"), dict):
        clone["receipt"]["contentHash"] = ""
    canonical = json.dumps(clone, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Basic statistics
# --------------------------------------------------------------------------- #
def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _var(xs: Sequence[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return sum((x - m) ** 2 for x in xs) / len(xs)


def _std(xs: Sequence[float]) -> float:
    return math.sqrt(_var(xs))


def autocorr(xs: Sequence[float], lag: int) -> float:
    n = len(xs)
    if lag >= n or n == 0:
        return 0.0
    m = _mean(xs)
    denom = sum((x - m) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    num = sum((xs[i] - m) * (xs[i + lag] - m) for i in range(n - lag))
    return num / denom


def _polyfit_slope(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Least-squares slope of ys ~ a + b*xs."""
    n = len(xs)
    if n < 2:
        return 0.0
    mx = _mean(xs)
    my = _mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return 0.0
    sxy = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    return sxy / sxx


def excess_kurtosis(xs: Sequence[float]) -> float:
    """Excess kurtosis (0 for Gaussian). Fat tails => strongly positive."""
    n = len(xs)
    if n == 0:
        return 0.0
    m = _mean(xs)
    s = _std(xs)
    if s == 0:
        return 0.0
    return sum(((x - m) / s) ** 4 for x in xs) / n - 3.0


# --------------------------------------------------------------------------- #
# Seeded arrival-family simulators
# --------------------------------------------------------------------------- #
def sim_poisson(rate: float, T: float, seed: int) -> List[float]:
    """Homogeneous Poisson process: constant intensity `rate`, i.i.d.
    exponential interarrivals -> memoryless / delta kernel / branching n=0."""
    if rate <= 0:
        raise ValueError("Poisson rate must be positive")
    rng = random.Random(seed)
    t = 0.0
    out: List[float] = []
    while True:
        t += -math.log(rng.random()) / rate
        if t >= T:
            break
        out.append(t)
    return out


def sim_hawkes_exp(mu: float, n: float, beta: float, T: float, seed: int) -> List[float]:
    """Univariate Hawkes with EXPONENTIAL kernel phi(t)=alpha*exp(-beta t),
    branching ratio n = alpha/beta = int phi. Ogata thinning, O(#events) via the
    exponential-kernel recursion (the excitation term A decays deterministically
    and jumps by alpha at each accepted event), so long streams are cheap and CI
    is fast.

    Exponential (finite-timescale) self-excitation -> SHORT-decaying memory /
    exponential kernel."""
    if not (0.0 <= n):
        raise ValueError("branching ratio n must be >= 0")
    alpha = n * beta
    rng = random.Random(seed)
    events: List[float] = []
    t = 0.0
    t_last = 0.0
    A = 0.0  # sum of alpha*exp(-beta*(t-t_i)) carried recursively
    while t < T:
        a_cur = A * math.exp(-beta * (t - t_last)) if events else 0.0
        lam_bar = mu + a_cur  # sup on [t, next event): intensity only decays
        if lam_bar <= 0:
            break
        t += -math.log(rng.random()) / lam_bar
        if t >= T:
            break
        a_cur = A * math.exp(-beta * (t - t_last)) if events else 0.0
        lam_t = mu + a_cur
        if rng.random() * lam_bar <= lam_t:
            A = a_cur + alpha
            t_last = t
            events.append(t)
        else:
            A = a_cur
            t_last = t
    return events


def sim_hawkes_powerlaw(mu: float, n: float, c: float, gamma: float,
                        T: float, seed: int) -> List[float]:
    """Univariate Hawkes with POWER-LAW kernel
    phi(t) = k*(t+c)^-(1+gamma), int_0^inf phi = k*c^-gamma/gamma = n
    => k = n*gamma*c^gamma. Ogata thinning.

    Heavy-tailed (long-memory) self-excitation -> LONG-memory / power-law
    kernel."""
    if not (0.0 <= n):
        raise ValueError("branching ratio n must be >= 0")
    if c <= 0 or gamma <= 0:
        raise ValueError("power-law kernel needs c>0, gamma>0")
    k = n * gamma * (c ** gamma)

    def phi(dt: float) -> float:
        return k * (dt + c) ** (-(1.0 + gamma))

    rng = random.Random(seed)
    events: List[float] = []
    t = 0.0
    while t < T:
        lam_bar = mu + sum(phi(t - ti) for ti in events)
        if lam_bar <= 0:
            break
        t += -math.log(rng.random()) / lam_bar
        if t >= T:
            break
        lam_t = mu + sum(phi(t - ti) for ti in events)
        if rng.random() * lam_bar <= lam_t:
            events.append(t)
    return events


def sim_acd(omega: float, a: float, b: float, n_events: int, seed: int) -> List[float]:
    """Autoregressive Conditional Duration (ACD(1,1)):
    psi_i = omega + a*x_{i-1} + b*psi_{i-1}, x_i = psi_i * eps_i, eps~Exp(1).

    Durations are autocorrelated and NON-exponential (over-dispersed) -- a
    Poisson (i.i.d. exponential duration) fit MISSES this. Returns event times
    (cumulative durations)."""
    if a < 0 or b < 0 or a + b >= 1.0:
        raise ValueError("ACD needs a>=0, b>=0, a+b<1 for stationarity")
    rng = random.Random(seed)
    psi = omega / (1.0 - a - b)  # unconditional mean duration
    x_prev = psi
    times: List[float] = []
    t = 0.0
    for _ in range(n_events):
        psi = omega + a * x_prev + b * psi
        eps = -math.log(rng.random())  # Exp(1)
        x = psi * eps
        x_prev = x
        t += x
        times.append(t)
    return times


# --------------------------------------------------------------------------- #
# Interarrival durations
# --------------------------------------------------------------------------- #
def durations(events: Sequence[float]) -> List[float]:
    return [events[i] - events[i - 1] for i in range(1, len(events))]


def duration_autocorr(events: Sequence[float], lag: int = 1) -> float:
    """Lag-`lag` autocorrelation of interarrival DURATIONS. ~0 for Poisson,
    strongly positive for ACD memory."""
    d = durations(events)
    if len(d) < lag + 2:
        return 0.0
    return autocorr(d, lag)


# --------------------------------------------------------------------------- #
# Branching ratio via the index of dispersion for counts (Fano factor)
# --------------------------------------------------------------------------- #
def counts_in_windows(events: Sequence[float], window: float,
                      T: Optional[float] = None) -> List[int]:
    if not events:
        return []
    if T is None:
        T = events[-1]
    k = int(T / window)
    if k < 1:
        return [len(events)]
    counts = [0] * k
    for e in events:
        idx = int(e / window)
        if 0 <= idx < k:
            counts[idx] += 1
    return counts


def index_of_dispersion(events: Sequence[float],
                        target_per_window: float = 25.0) -> float:
    """Var(N)/E(N) over count windows sized so the mean count ~ target. IDC=1
    for Poisson; IDC>1 for a self-exciting (clustered) stream."""
    if len(events) < 4:
        return 1.0
    T = events[-1]
    rate = len(events) / T if T > 0 else 1.0
    window = target_per_window / rate if rate > 0 else T / 10.0
    counts = counts_in_windows(events, window, T)
    if len(counts) < 3:
        # too few windows: fall back to a finer split
        counts = counts_in_windows(events, T / 10.0, T)
    if len(counts) < 3:
        return 1.0
    m = _mean(counts)
    if m <= 0:
        return 1.0
    return _var(counts) / m


def branching_ratio_hat(events: Sequence[float]) -> float:
    """n_hat = 1 - 1/sqrt(IDC), clamped to [0, 1). For a stationary Hawkes
    Var(N_T)/E(N_T) -> (1-n)^-2, so this inverts the asymptotic Fano factor. A
    Poisson stream (IDC=1) yields n_hat=0."""
    idc = index_of_dispersion(events)
    idc = max(idc, 1.0)
    n_hat = 1.0 - 1.0 / math.sqrt(idc)
    return min(max(n_hat, 0.0), 0.999)


# --------------------------------------------------------------------------- #
# Poisson-vs-Hawkes discrimination test (fires on excitation)
# --------------------------------------------------------------------------- #
def poisson_vs_hawkes(events: Sequence[float]) -> Tuple[str, float]:
    """Discriminate a Poisson null from self-excitation via the index of
    dispersion. Returns (verdict, idc): verdict 'hawkes' when IDC>=IDC_EXCITE
    (a Poisson fit is REJECTED -- clustering/excitation present), else
    'poisson'."""
    idc = index_of_dispersion(events)
    return ("hawkes" if idc >= IDC_EXCITE else "poisson"), idc


# --------------------------------------------------------------------------- #
# Hurst of the counting process (kernel discrimination: exp vs power-law)
# --------------------------------------------------------------------------- #
def hurst_rs(series: Sequence[float]) -> float:
    """Hurst exponent via rescaled-range (R/S) analysis on a noise series.
    H~0.5 short-range; H>0.5 long-memory (power-law dependence)."""
    incs = list(series)
    N = len(incs)
    if N < 16:
        return 0.5
    sizes: List[int] = []
    s = 8
    while s <= N // 2:
        sizes.append(s)
        s = int(s * 1.5)
    if not sizes:
        sizes = [max(8, N // 2)]
    log_s: List[float] = []
    log_rs: List[float] = []
    for w in sizes:
        nblocks = N // w
        if nblocks < 1:
            continue
        rs_vals: List[float] = []
        for bidx in range(nblocks):
            block = incs[bidx * w:(bidx + 1) * w]
            m = _mean(block)
            dev = 0.0
            cum: List[float] = []
            for v in block:
                dev += v - m
                cum.append(dev)
            R = max(cum) - min(cum)
            S = _std(block)
            if S > 0 and R > 0:
                rs_vals.append(R / S)
        if rs_vals:
            log_s.append(math.log(w))
            log_rs.append(math.log(_mean(rs_vals)))
    if len(log_s) < 2:
        return 0.5
    return _polyfit_slope(log_s, log_rs)


def hurst_dfa(series: Sequence[float]) -> float:
    """Hurst exponent via detrended fluctuation analysis (DFA). More stable than
    R/S on short count series; alpha ~ H for a noise series."""
    incs = list(series)
    N = len(incs)
    if N < 16:
        return 0.5
    m = _mean(incs)
    prof: List[float] = []
    acc = 0.0
    for v in incs:
        acc += v - m
        prof.append(acc)
    sizes: List[int] = []
    s = 8
    while s <= N // 4:
        sizes.append(s)
        s = int(s * 1.5)
    if not sizes:
        return 0.5
    log_s: List[float] = []
    log_f: List[float] = []
    for w in sizes:
        nblocks = N // w
        f2: List[float] = []
        for b in range(nblocks):
            seg = prof[b * w:(b + 1) * w]
            idx = list(range(w))
            slope = _polyfit_slope(idx, seg)
            intercept = _mean(seg) - slope * _mean(idx)
            f2.append(sum((seg[i] - (intercept + slope * i)) ** 2 for i in range(w)) / w)
        if f2:
            fluct = math.sqrt(_mean(f2))
            if fluct > 0:
                log_s.append(math.log(w))
                log_f.append(math.log(fluct))
    if len(log_s) < 2:
        return 0.5
    return _polyfit_slope(log_s, log_f)


def _adaptive_bin_counts(n_events: int) -> List[int]:
    """Bin counts chosen so each bin holds ~[12..35] events and there are >=48
    bins -- scale-free across the very different stream lengths (a long
    exponential stream vs a shorter power-law one)."""
    out: List[int] = []
    for target in (12.0, 18.0, 25.0, 35.0):
        b = int(n_events / target)
        if b >= 48:
            out.append(b)
    if not out:
        out = [max(16, n_events // 12)]
    return out


def counting_hurst(events: Sequence[float]) -> float:
    """Ensemble Hurst of the binned counting process -- the exp-vs-power-law
    kernel discriminator. Averages R/S and DFA over several adaptive bin scales
    to suppress the single-scale estimator variance. Exponential self-excitation
    is short-range (ensemble H well below H_LONG even for long streams); a
    heavy power-law kernel is long-memory (H >= H_LONG)."""
    if len(events) < 96:
        return 0.5
    T = events[-1]
    vals: List[float] = []
    for bins in _adaptive_bin_counts(len(events)):
        counts = [float(c) for c in counts_in_windows(events, T / bins, T)]
        if len(counts) >= 48:
            vals.append(0.5 * (hurst_rs(counts) + hurst_dfa(counts)))
    return _mean(vals) if vals else 0.5


# --------------------------------------------------------------------------- #
# Self-similarity across scale (Elliott/Synergetics wave-count evidence).
# The full multifractal spectrum is the memory-mesh regime characterizer's;
# reused BY REFERENCE. This is a light cross-scale read for fixture evidence.
# --------------------------------------------------------------------------- #
def generalized_hurst_width(series: Sequence[float], qs=(1.0, 2.0, 3.0)) -> float:
    """Width of the generalized Hurst exponents H(q) via structure functions
    S_q(tau)=<|x(t+tau)-x(t)|^q> ~ tau^(q*H(q)). A MONO-fractal (self-affine)
    trace has H(q) constant (width ~0); a MULTIFRACTAL trace spreads H(q) across
    q (width > 0) -- the measurable signature of self-similar recursion across
    scale that an Elliott wave-count must carry."""
    x = list(series)
    n = len(x)
    if n < 64:
        return 0.0
    taus = [t for t in (2, 4, 8, 16, 32) if t < n // 4]
    if len(taus) < 3:
        return 0.0
    hq: List[float] = []
    for q in qs:
        log_tau: List[float] = []
        log_s: List[float] = []
        for tau in taus:
            incs = [abs(x[i + tau] - x[i]) ** q for i in range(n - tau)]
            s = _mean(incs)
            if s > 0:
                log_tau.append(math.log(tau))
                log_s.append(math.log(s))
        if len(log_tau) >= 3:
            hq.append(_polyfit_slope(log_tau, log_s) / q)
    if len(hq) < 2:
        return 0.0
    return max(hq) - min(hq)


# --------------------------------------------------------------------------- #
# Marks: heavy-tailed sizes + Hill tail index
# --------------------------------------------------------------------------- #
def sim_pareto_marks(n_marks: int, tail_index: float, xmin: float,
                     seed: int) -> List[float]:
    """Power-law (Pareto) marks: P(X>x) = (xmin/x)^tail_index, x>=xmin. Small
    tail_index => heavier tail."""
    if tail_index <= 0 or xmin <= 0:
        raise ValueError("Pareto needs tail_index>0, xmin>0")
    rng = random.Random(seed)
    return [xmin * (rng.random() ** (-1.0 / tail_index)) for _ in range(n_marks)]


def hill_tail_index(sizes: Sequence[float], k_frac: float = 0.1) -> float:
    """Hill estimator of the (Pareto) tail index alpha from the top k order
    statistics. A small alpha (<HILL_TAIL_FINITE) is a genuinely heavy tail;
    a Gaussian yields a large/ill-defined value."""
    xs = sorted((x for x in sizes if x > 0), reverse=True)
    n = len(xs)
    if n < 10:
        return float("inf")
    k = max(2, int(k_frac * n))
    k = min(k, n - 1)
    logs = [math.log(xs[i]) for i in range(k)]
    thresh = math.log(xs[k])
    denom = _mean(logs) - thresh
    if denom <= 0:
        return float("inf")
    return 1.0 / denom


def marks_are_heavy_tailed(sizes: Sequence[float]) -> bool:
    """A mark set is heavy-tailed if its excess kurtosis is large OR the Hill
    tail index is finite/small (genuine power-law tail)."""
    if excess_kurtosis(sizes) >= FAT_TAIL_KURTOSIS:
        return True
    return hill_tail_index(sizes) < HILL_TAIL_FINITE


# --------------------------------------------------------------------------- #
# LOB micro-signals: OFI and Kyle-lambda
# --------------------------------------------------------------------------- #
def order_flow_imbalance(signed_sizes: Sequence[float]) -> float:
    """OFI = sum of signed order sizes (buy +, sell -)."""
    return sum(signed_sizes)


def kyle_lambda(signed_volume: Sequence[float], price_change: Sequence[float]) -> float:
    """Kyle's lambda: price impact per unit signed volume, the OLS slope of
    price change on signed volume. >=0 for a normal (adverse-selection) book.

    Shaped as the liquidity input for economic-prophet
    market_instruments.liquidity_premium(...)."""
    if len(signed_volume) != len(price_change) or len(signed_volume) < 2:
        raise ValueError("need >=2 aligned (signed_volume, price_change) pairs")
    return _polyfit_slope(signed_volume, price_change)


def sim_price_from_flow(kyle: float, n_steps: int, seed: int,
                        noise: float = 0.05, vol_scale: float = 1.0
                        ) -> Tuple[List[float], List[float]]:
    """Seeded (signed_volume, price_change) pairs with a KNOWN Kyle-lambda:
    dp = kyle * signed_volume + noise*eps. Used to VERIFY lambda recovery."""
    rng = random.Random(seed)
    sv: List[float] = []
    dp: List[float] = []
    for _ in range(n_steps):
        v = rng.gauss(0.0, vol_scale)
        sv.append(v)
        dp.append(kyle * v + rng.gauss(0.0, noise))
    return sv, dp


# --------------------------------------------------------------------------- #
# Execution: fill probability conditional on queue position
# --------------------------------------------------------------------------- #
def fill_probability(queue_ahead: float, depletion_rate: float) -> float:
    """P(fill) for a resting limit order with `queue_ahead` size in front,
    thinned by a market-order depletion rate: exp(-queue_ahead/depletion_rate),
    in [0,1]. A resting order at the front (queue_ahead=0) fills with prob 1."""
    if queue_ahead < 0:
        raise ValueError("queue_ahead must be >= 0")
    if depletion_rate <= 0:
        raise ValueError("depletion_rate must be > 0")
    return math.exp(-queue_ahead / depletion_rate)


def competing_hazard_fill_prob(fill_hazard: float, cancel_hazard: float) -> float:
    """P(order is filled before cancelled) under competing exponential hazards:
    fill_hazard/(fill_hazard+cancel_hazard), in [0,1]. Cancellation is the
    competing risk (limit-order lifetime = Exp(fill+cancel))."""
    if fill_hazard < 0 or cancel_hazard < 0:
        raise ValueError("hazards must be >= 0")
    tot = fill_hazard + cancel_hazard
    if tot == 0:
        return 0.0
    return fill_hazard / tot


# --------------------------------------------------------------------------- #
# Arrival-family classifier -> memory regime (the KEY integration)
# --------------------------------------------------------------------------- #
def classify_arrival(events: Sequence[float]) -> dict:
    """Map an event stream onto the estate memory-regime taxonomy in EVENT time.

    poisson            -> memoryless    (delta kernel,   n~0)
    exponential-Hawkes -> short_decaying (exponential kernel)
    power-law-Hawkes   -> long_memory   (power_law kernel)
    near-critical n->1 -> chaotic       (the unstable/flash-crash edge)
    """
    n_hat = branching_ratio_hat(events)
    verdict, idc = poisson_vs_hawkes(events)
    Hc = counting_hurst(events)
    excited = verdict == "hawkes"

    if not excited:
        regime, kernel, family = "memoryless", "delta", "poisson"
    elif n_hat >= N_CRITICAL:
        # near-critical branching: the unstable / flash-crash edge
        regime, kernel, family = "chaotic", "power_law", "hawkes_near_critical"
    elif Hc >= H_LONG:
        # long-memory (power-law) self-excitation survives as long-range dependence
        regime, kernel, family = "long_memory", "power_law", "hawkes_powerlaw"
    else:
        # self-excitation present but short-range: exponential kernel
        regime, kernel, family = "short_decaying", "exponential", "hawkes_exponential"

    stable = n_hat < 1.0
    return {
        "n_events": len(events),
        "branching_ratio_n": round(n_hat, 4),
        "index_of_dispersion": round(idc, 4),
        "counting_hurst": round(Hc, 4),
        "poisson_vs_hawkes": verdict,
        "arrival_family": family,
        "regime": regime,
        "autocorr_kernel": kernel,
        "stable": stable,
    }
