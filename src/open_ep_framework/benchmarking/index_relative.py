"""Baseline-vs-idiosyncratic benchmarking decomposition (IRB-1).

For each cohort ``(asset_class, market, issuer?, rating_agency_bucket?, region?,
sector?)`` a baseline index ``B`` is declared, and any measure series ``X`` is
decomposed into a systematic and an idiosyncratic part:

    X_t = beta * B_t + epsilon_t      (single-factor, OLS beta through the data)
    beta = cov(X, B) / var(B)
    epsilon_t = X_t - beta * B_t      (carries the idiosyncratic mean alpha = E[eps])

Because ``beta`` is the OLS slope, the residual is orthogonal to the baseline
(``cov(B, epsilon) == 0``), so the risk splits EXACTLY:

    var(X) = beta^2 * var(B) + var(epsilon)      (systematic + idiosyncratic)

The cross-cohort DIFFERENTIAL is the idiosyncratic residual expressed UNIT-FREE
so it is comparable across currencies / regions / legal regimes even though the
absolute levels are not:

  * ``idiosyncratic_z``     = mean(eps) / std(eps)      (dimensionless t-like)
  * ``spread_to_baseline``  = mean(eps)                 (residual return spread)
  * ``cross_sectional_rank``= ordinal rank of z among a peer set

Teeth (both directions)
-----------------------
REQUIRES  a cohort declares a baseline index; a measure attributes systematic vs
          idiosyncratic (``beta*B + eps``); the split reconciles in LEVEL
          (``beta*B_t + eps_t == X_t``) and in VARIANCE
          (``beta^2 var(B) + var(eps) == var(X)``) within tolerance; a cross-frame
          comparison rides a dimensionless basis.
REJECTS   a cohort with NO declared baseline index; a measure NOT decomposed into
          baseline + idiosyncratic (no systematic/idiosyncratic attribution); a
          split that does not reconcile in level or in variance; a CROSS-FRAME
          comparison done on ABSOLUTE levels (assuming a common price across a
          currency / region / legal-regime boundary) instead of the dimensionless
          differential.

Consume-by-reference: the RM-1 systematic/idiosyncratic factorization and CAPM
beta (``risk_measures``). Deterministic and stdlib-only.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

_SCHEMA = "schemas/index_relative_cohort.schema.json"

# The cohort key axes. asset_class + market are REQUIRED (a cohort is at least an
# asset class in a market); issuer / rating_agency_bucket / region / sector refine
# it. region + the market's currency are what make absolute levels incomparable.
REQUIRED_COHORT_AXES = ("asset_class", "market")
OPTIONAL_COHORT_AXES = ("issuer", "rating_agency_bucket", "region", "sector")

# Dimensionless comparison bases admitted across frames. An absolute level is NOT
# admissible across a currency / region / legal-regime boundary.
DIMENSIONLESS_BASES = {"idiosyncratic_z", "spread_to_baseline", "cross_sectional_rank"}
ABSOLUTE_BASES = {"absolute", "absolute_level", "raw_level", "price_level"}

# Reconciliation tolerances (exact up to floating point for OLS by construction).
LEVEL_TOL = 1e-9
VAR_TOL = 1e-9


class IndexRelativeError(ValueError):
    """Raised when a cohort / measure / comparison violates IRB-1 (REJECTED)."""


# --------------------------------------------------------------------------- #
# small deterministic stats (population moments, stdlib only)
# --------------------------------------------------------------------------- #
def _mean(xs) -> float:
    xs = list(xs)
    if not xs:
        raise IndexRelativeError("cannot take the mean of an empty series")
    return sum(xs) / len(xs)


def _variance(xs) -> float:
    xs = list(xs)
    m = _mean(xs)
    return sum((x - m) ** 2 for x in xs) / len(xs)


def _covariance(xs, ys) -> float:
    xs, ys = list(xs), list(ys)
    if len(xs) != len(ys):
        raise IndexRelativeError("covariance needs equal-length series")
    mx, my = _mean(xs), _mean(ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / len(xs)


def _std(xs) -> float:
    return math.sqrt(_variance(xs))


# --------------------------------------------------------------------------- #
# the decomposition
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Decomposition:
    """A single-factor baseline decomposition of a measure series X on baseline B."""

    beta: float
    alpha: float                 # E[epsilon] -- the idiosyncratic mean (spread-to-baseline)
    epsilon: tuple               # idiosyncratic residual series
    systematic: tuple            # beta * B_t series
    var_baseline: float
    var_epsilon: float
    var_total: float             # var(X)
    n: int

    @property
    def systematic_share(self) -> float:
        """Fraction of total variance explained by the baseline (R^2-like)."""
        if self.var_total <= 0:
            return 0.0
        return (self.beta ** 2 * self.var_baseline) / self.var_total

    @property
    def idiosyncratic_share(self) -> float:
        if self.var_total <= 0:
            return 0.0
        return self.var_epsilon / self.var_total


def decompose(x_series, b_series) -> Decomposition:
    """Decompose X = beta*B + epsilon with the OLS single-factor beta.

    ``epsilon`` carries the idiosyncratic mean (alpha), so ``beta*B_t + eps_t``
    reproduces ``X_t`` exactly and the residual is orthogonal to B.
    """
    x = [float(v) for v in x_series]
    b = [float(v) for v in b_series]
    if len(x) != len(b):
        raise IndexRelativeError("measure and baseline series must be equal length")
    if len(x) < 2:
        raise IndexRelativeError("decomposition needs at least 2 observations")

    var_b = _variance(b)
    if var_b <= 0:
        raise IndexRelativeError(
            "baseline index has zero variance; beta is not identified "
            "(a flat baseline cannot carry systematic risk)"
        )
    beta = _covariance(x, b) / var_b
    systematic = tuple(beta * bt for bt in b)
    epsilon = tuple(xt - st for xt, st in zip(x, systematic))
    alpha = _mean(epsilon)
    return Decomposition(
        beta=beta,
        alpha=alpha,
        epsilon=epsilon,
        systematic=systematic,
        var_baseline=var_b,
        var_epsilon=_variance(epsilon),
        var_total=_variance(x),
        n=len(x),
    )


# --------------------------------------------------------------------------- #
# reconciliation teeth
# --------------------------------------------------------------------------- #
def check_reconciliation(decomp: Decomposition, x_series) -> None:
    """REJECT a split that does not reconcile in LEVEL and in VARIANCE.

    Level:    beta*B_t + eps_t == X_t   for all t   (exact by construction).
    Variance: beta^2 var(B) + var(eps) == var(X)     (OLS orthogonality).
    A non-reconciling split means the attribution is not a real decomposition.
    """
    x = [float(v) for v in x_series]
    if len(x) != decomp.n:
        raise IndexRelativeError("reconciliation series length mismatch")

    for t, (st, et, xt) in enumerate(zip(decomp.systematic, decomp.epsilon, x)):
        if abs(st + et - xt) > LEVEL_TOL:
            raise IndexRelativeError(
                f"level reconciliation failed at t={t}: beta*B + eps = {st + et!r} "
                f"!= X = {xt!r} (the split is not X = beta*B + epsilon)"
            )

    lhs = decomp.beta ** 2 * decomp.var_baseline + decomp.var_epsilon
    if abs(lhs - decomp.var_total) > VAR_TOL:
        raise IndexRelativeError(
            f"variance reconciliation failed: beta^2 var(B) + var(eps) = {lhs!r} "
            f"!= var(X) = {decomp.var_total!r}; the residual is not orthogonal to "
            f"the baseline (this is not a systematic/idiosyncratic split)"
        )


# --------------------------------------------------------------------------- #
# the unit-free idiosyncratic differential
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Differential:
    """The cross-frame-comparable, DIMENSIONLESS idiosyncratic differential."""

    idiosyncratic_z: float        # mean(eps)/std(eps): a dimensionless t-like statistic
    spread_to_baseline: float     # mean(eps): the residual return spread
    epsilon_std: float


def idiosyncratic_differential(decomp: Decomposition) -> Differential:
    """The unit-free residual: comparable across currencies / regions / regimes."""
    std = math.sqrt(decomp.var_epsilon)
    z = 0.0 if std == 0 else decomp.alpha / std
    return Differential(
        idiosyncratic_z=z,
        spread_to_baseline=decomp.alpha,
        epsilon_std=std,
    )


def cross_sectional_ranks(zs) -> list:
    """Ordinal (unit-free) rank of each idiosyncratic_z within the peer set.

    Rank 1 == smallest differential. Ties share the average rank. Ranks are the
    most robust cross-frame comparison: they assume no common scale at all.
    """
    zs = [float(z) for z in zs]
    order = sorted(range(len(zs)), key=lambda i: zs[i])
    ranks = [0.0] * len(zs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and zs[order[j + 1]] == zs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0  # 1-based average rank over the tie group
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


# --------------------------------------------------------------------------- #
# cohort teeth
# --------------------------------------------------------------------------- #
def require_baseline(cohort: dict, where: str = "cohort") -> None:
    """REJECT a cohort with no declared baseline index."""
    bi = cohort.get("baseline_index")
    if not bi or not isinstance(bi, dict):
        raise IndexRelativeError(
            f"{where}: no declared baseline_index; a cohort measure cannot be "
            f"attributed to systematic vs idiosyncratic without a baseline"
        )
    if not bi.get("series"):
        raise IndexRelativeError(f"{where}: baseline_index has no series")
    for axis in REQUIRED_COHORT_AXES:
        if not cohort.get("key", {}).get(axis):
            raise IndexRelativeError(f"{where}: cohort key missing required axis {axis!r}")


def require_decomposed(measure: dict, where: str) -> None:
    """REJECT a measure that is not attributed to a baseline + idiosyncratic split.

    A measure that arrives as a bare level/series with ``decomposed`` false, or
    with no measure series to decompose, has made no systematic/idiosyncratic
    attribution and is inadmissible.
    """
    if measure.get("decomposed") is False:
        raise IndexRelativeError(
            f"{where}: measure declares decomposed=false; a measure not split into "
            f"baseline + idiosyncratic is REJECTED (attribute systematic vs idiosyncratic)"
        )
    if not measure.get("series"):
        raise IndexRelativeError(f"{where}: measure has no series to decompose")


def cohort_key(cohort: dict) -> dict:
    key = dict(cohort.get("key", {}))
    return {k: key.get(k) for k in REQUIRED_COHORT_AXES + OPTIONAL_COHORT_AXES if key.get(k) is not None}


def run_cohort(cohort: dict) -> dict:
    """Validate + decompose ONE cohort. Returns a deterministic receipt fragment."""
    cid = cohort.get("cohort_id", "cohort")
    require_baseline(cohort, cid)
    measure = cohort["measure"]
    require_decomposed(measure, cid)

    b = cohort["baseline_index"]["series"]
    x = measure["series"]
    decomp = decompose(x, b)
    check_reconciliation(decomp, x)
    diff = idiosyncratic_differential(decomp)

    return {
        "cohort_id": cid,
        "key": cohort_key(cohort),
        "baseline_index_id": cohort["baseline_index"].get("index_id"),
        "currency": cohort.get("frame", {}).get("currency"),
        "n": decomp.n,
        "beta": round(decomp.beta, 10),
        "alpha": round(decomp.alpha, 10),
        "systematic_share": round(decomp.systematic_share, 10),
        "idiosyncratic_share": round(decomp.idiosyncratic_share, 10),
        "reconciles": {
            "level": True,
            "variance": True,
            "identity": "beta*B + epsilon == X ; beta^2 var(B) + var(eps) == var(X)",
        },
        "differential": {
            "idiosyncratic_z": round(diff.idiosyncratic_z, 10),
            "spread_to_baseline": round(diff.spread_to_baseline, 10),
        },
    }


# --------------------------------------------------------------------------- #
# cross-frame teeth: the dimensionless differential, never an absolute level
# --------------------------------------------------------------------------- #
def _frame_of(cohort_receipt: dict) -> tuple:
    key = cohort_receipt.get("key", {})
    return (cohort_receipt.get("currency"), key.get("region"), key.get("market"))


def reject_absolute_cross_frame(comparison: dict, cohort_receipts: dict) -> None:
    """REJECT a cross-frame comparison done on ABSOLUTE levels.

    Comparing two cohorts that live in different frames (differing currency /
    region / market) is only admissible on a DIMENSIONLESS basis. A comparison
    that asserts a common absolute price / level across a frame boundary has
    assumed a global price where none exists and is inadmissible.
    """
    basis = comparison.get("basis")
    left = comparison.get("left")
    right = comparison.get("right")
    if left not in cohort_receipts or right not in cohort_receipts:
        raise IndexRelativeError(
            f"comparison references unknown cohort(s) {left!r}/{right!r}"
        )
    same_frame = _frame_of(cohort_receipts[left]) == _frame_of(cohort_receipts[right])
    if basis in ABSOLUTE_BASES and not same_frame:
        raise IndexRelativeError(
            f"cross-frame comparison {left!r} vs {right!r} on an ABSOLUTE basis "
            f"{basis!r}: absolute levels are not comparable across a currency/region/"
            f"market boundary; use a dimensionless differential {sorted(DIMENSIONLESS_BASES)}"
        )
    if basis not in DIMENSIONLESS_BASES and basis not in ABSOLUTE_BASES:
        raise IndexRelativeError(f"comparison has unknown basis {basis!r}")


def compare_cross_frame(comparison: dict, cohort_receipts: dict) -> dict:
    """Evaluate an admitted cross-frame comparison on its dimensionless basis."""
    reject_absolute_cross_frame(comparison, cohort_receipts)
    basis = comparison["basis"]
    left, right = comparison["left"], comparison["right"]
    lr, rr = cohort_receipts[left], cohort_receipts[right]

    if basis == "cross_sectional_rank":
        zs = [r["differential"]["idiosyncratic_z"] for r in cohort_receipts.values()]
        ids = list(cohort_receipts.keys())
        ranks = dict(zip(ids, cross_sectional_ranks(zs)))
        lval, rval = ranks[left], ranks[right]
    else:
        lval = lr["differential"][basis]
        rval = rr["differential"][basis]

    return {
        "left": left,
        "right": right,
        "basis": basis,
        "left_value": round(lval, 10),
        "right_value": round(rval, 10),
        "differential": round(lval - rval, 10),
        "cross_frame": _frame_of(lr) != _frame_of(rr),
        "unit_free": True,
    }


# --------------------------------------------------------------------------- #
# whole-book check + receipt
# --------------------------------------------------------------------------- #
def check_book(book: dict) -> dict:
    """Validate every cohort and every cross-frame comparison. Returns a receipt."""
    cohorts = book.get("cohorts")
    if not cohorts:
        raise IndexRelativeError("book has no cohorts")

    receipts = {}
    for c in cohorts:
        r = run_cohort(c)
        if r["cohort_id"] in receipts:
            raise IndexRelativeError(f"duplicate cohort_id {r['cohort_id']!r}")
        receipts[r["cohort_id"]] = r

    comparisons = []
    for cmp in book.get("comparisons", []):
        comparisons.append(compare_cross_frame(cmp, receipts))

    return {
        "contract": "IRB-1",
        "book_id": book.get("book_id"),
        "cohort_count": len(receipts),
        "cohorts": list(receipts.values()),
        "comparisons": comparisons,
    }


def load(path: str) -> dict:
    return json.loads(Path(path).read_text())


def run_check(book_path: str, schema_path: str = _SCHEMA) -> dict:
    """Schema-validate (stdlib) then apply every tooth. Returns the receipt."""
    from ..validation import validate_json_file

    validate_json_file(book_path, schema_path)
    return check_book(load(book_path))


# --------------------------------------------------------------------------- #
# CLI: emit a deterministic receipt for CI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Check the index-relative benchmarking contract (IRB-1)."
    )
    parser.add_argument("--book", default="examples/benchmarking/index_relative_book.valid.json")
    parser.add_argument("--schema", default=_SCHEMA)
    parser.add_argument("--receipt", default=None, help="Optional path to write the receipt JSON.")
    args = parser.parse_args(argv)

    receipt = run_check(args.book, args.schema)
    text = json.dumps(receipt, indent=2, sort_keys=True)
    if args.receipt:
        Path(args.receipt).write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
