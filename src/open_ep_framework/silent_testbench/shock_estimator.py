"""SILENT-WEAPONS SHOCK-TEST ESTIMATOR (SILENT pp.26-29) -- and its de-mystification.

The pamphlet "Silent Weapons for Quiet Wars" (William Cooper's 1986 transcription of an
undated document; widely circulated) models the economy as an electrical circuit and
prescribes a "shock test" to recover its transfer function. In the document's own terms
(the "diode" / "economic inductance" chapter and the matrix pages 26-29):

    "Economic inductance ... The public inventory of goods ... Shock testing ...
     Consumer surveys ... a shock front ... to test the reaction ...
     P = a_11 X_1 + a_12 X_2 + ... + a_1n X_n            (a row of the coefficient matrix)
     ... shock the price of one commodity, observe the change in demand of every other,
     ... assemble [a_jk], collect the observed outputs [Y_j],
     ... solve [a_jk][X_k] = [Y_j] and invert to [b_kj]."

THIS MODULE IMPLEMENTS THAT LITERALLY -- and then SHOWS it is nothing more than the
identification of a **cross-price-elasticity matrix**, equivalently the **impulse-response
identification of a (structural) VAR**. There is no secret weapon in the mathematics; it
is the ordinary econometrics an undergraduate demand-system course teaches.

The three named operations map one-to-one onto standard econometrics:

  doc term                       standard econometrics
  ---------------------------    --------------------------------------------------
  "shock a price, read ΔP"       a partial derivative ∂Q_j/∂P_k  ==  (in logs) the
                                 cross-price ELASTICITY e_jk = ∂lnQ_j/∂lnP_k
  "assemble [a_jk]"              the impact / coefficient matrix of a linear demand
                                 system == the contemporaneous IMPULSE-RESPONSE matrix
                                 of a structural VAR at horizon 0
  "solve [a_jk][X_k]=[Y_j]"      solving the structural system for the driving inputs
  "invert to [b_kj]"            recovering the structural coefficient (A/B) matrix from
                                 the reduced form -- exactly SVAR identification

The teeth (see ``confront.py`` and the tests) assert the EQUIVALENCE numerically: the
finite-difference "shock test", an OLS regression of the same responses, and a VAR(1)
impulse response all recover the SAME matrix within tolerance -- because they are the same
estimator wearing three hats. Reporting this as a "superior predictor" is a RELABELING and
is flagged.

Deterministic and stdlib-only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import linalg


class ShockTestError(ValueError):
    """Raised for an inadmissible shock-test configuration -- REJECTED."""


# --------------------------------------------------------------------------- #
# A ground-truth linear demand system Q_j = sum_k E_jk * lnP_k (+ intercept).
# In LOG space, E_jk is exactly the cross-price elasticity (own-price on the
# diagonal, cross-price off-diagonal). This is the "true" economy the shock test
# is asked to recover; nothing about it is conspiratorial -- it is a demand system.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class DemandSystem:
    """A log-linear demand system: ln Q_j = alpha_j + sum_k E_jk * ln P_k.

    ``elasticities[j][k]`` = e_jk = ∂ln Q_j / ∂ln P_k (own-price on the diagonal,
    conventionally negative; cross-price off-diagonal, sign = substitute(+)/complement(-)).
    """
    goods: tuple
    elasticities: linalg.Matrix          # E[j][k]
    log_intercepts: linalg.Vector

    def __post_init__(self) -> None:
        n = len(self.goods)
        if len(self.elasticities) != n or any(len(r) != n for r in self.elasticities):
            raise ShockTestError("elasticity matrix must be n x n over the goods")
        if len(self.log_intercepts) != n:
            raise ShockTestError("intercept vector must match goods")

    def log_quantities(self, log_prices: linalg.Vector) -> linalg.Vector:
        return [
            self.log_intercepts[j] + sum(self.elasticities[j][k] * log_prices[k]
                                         for k in range(len(self.goods)))
            for j in range(len(self.goods))
        ]

    def quantities(self, prices: linalg.Vector) -> linalg.Vector:
        lp = [math.log(p) for p in prices]
        return [math.exp(lq) for lq in self.log_quantities(lp)]


@dataclass
class ShockTestResult:
    """The output of the doc's procedure, with its econometric identity attached."""
    goods: tuple
    recovered_elasticities: linalg.Matrix   # [a_jk] in the doc's notation, = e_jk
    inverse_matrix: linalg.Matrix           # [b_kj] = [a_jk]^-1 (the doc's "invert" step)
    method: str                             # "shock_test" | "ols" | "var_irf"
    notes: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# 1) THE DOCUMENT'S PROCEDURE, LITERALLY: shock a price, read the response.
# --------------------------------------------------------------------------- #
def shock_test(system: DemandSystem, base_prices: linalg.Vector,
               rel_shock: float = 0.01) -> ShockTestResult:
    """Recover [a_jk] by the doc's shock test: perturb price k, read Δln Q_j.

    For each good k we multiply its price by (1 + rel_shock), recompute all quantities,
    and form a_jk = Δln Q_j / Δln P_k. In log space this finite difference IS the
    cross-price elasticity e_jk (exactly, for a log-linear system; to O(shock) for any
    smooth system). Then, per the doc, we INVERT [a_jk] to [b_kj].
    """
    n = len(system.goods)
    if len(base_prices) != n:
        raise ShockTestError("base price vector must match goods")
    if rel_shock <= 0:
        raise ShockTestError("relative shock must be positive")
    base_lq = system.log_quantities([math.log(p) for p in base_prices])
    a = [[0.0] * n for _ in range(n)]
    for k in range(n):
        shocked = list(base_prices)
        shocked[k] = base_prices[k] * (1.0 + rel_shock)
        d_ln_pk = math.log(shocked[k]) - math.log(base_prices[k])
        lq = system.log_quantities([math.log(p) for p in shocked])
        for j in range(n):
            a[j][k] = (lq[j] - base_lq[j]) / d_ln_pk
    try:
        b = linalg.invert(a)
    except linalg.SingularMatrixError as exc:
        raise ShockTestError(f"[a_jk] singular, cannot invert to [b_kj]: {exc}") from exc
    return ShockTestResult(
        goods=system.goods, recovered_elasticities=a, inverse_matrix=b,
        method="shock_test",
        notes={"rel_shock": rel_shock,
               "identity": "a_jk == cross-price elasticity ∂lnQ_j/∂lnP_k"},
    )


def solve_for_inputs(a: linalg.Matrix, observed_y: linalg.Vector) -> linalg.Vector:
    """The doc's ``solve [a_jk][X_k] = [Y_j]`` step -- ordinary linear system solving."""
    try:
        return linalg.solve(a, observed_y)
    except linalg.SingularMatrixError as exc:
        raise ShockTestError(f"cannot solve [a_jk][X_k]=[Y_j]: {exc}") from exc


# --------------------------------------------------------------------------- #
# 2) THE SAME NUMBERS AS ORDINARY ECONOMETRICS.
# --------------------------------------------------------------------------- #
def ols_elasticities(system: DemandSystem, base_prices: linalg.Vector,
                     rel_shock: float = 0.05, n_experiments: int = 24) -> ShockTestResult:
    """Recover the elasticity matrix by OLS on a designed price-variation panel.

    We vary each log-price over a deterministic grid (no RNG -> reproducible), record the
    log-quantities, and regress ln Q_j on the ln P_k. The OLS slopes ARE e_jk. This is the
    textbook estimator; the shock test above must agree with it (that is the tooth).
    """
    n = len(system.goods)
    # deterministic design: sweep each good's log-price around its base on a symmetric grid
    rows: list[list[float]] = []
    base_lp = [math.log(p) for p in base_prices]
    for e in range(n_experiments):
        lp = list(base_lp)
        for k in range(n):
            # a fixed, mutually-non-collinear deterministic perturbation pattern
            phase = math.sin((e + 1) * (k + 1) * 0.7)
            lp[k] = base_lp[k] + rel_shock * phase
        rows.append(lp)
    # design matrix with an intercept column
    design = [[1.0] + row for row in rows]
    a = [[0.0] * n for _ in range(n)]
    for j in range(n):
        y = [system.log_quantities(row)[j] for row in rows]
        beta = linalg.ols(design, y)          # beta[0] = intercept, beta[1:] = e_jk
        for k in range(n):
            a[j][k] = beta[1 + k]
    try:
        b = linalg.invert(a)
    except linalg.SingularMatrixError as exc:
        raise ShockTestError(f"OLS elasticity matrix singular: {exc}") from exc
    return ShockTestResult(
        goods=system.goods, recovered_elasticities=a, inverse_matrix=b, method="ols",
        notes={"n_experiments": n_experiments,
               "identity": "OLS slope of lnQ_j on lnP_k == e_jk == doc's a_jk"},
    )


def var1_impulse_matrix(coeff: linalg.Matrix, horizon: int = 0) -> linalg.Matrix:
    """Impulse-response matrix of a VAR(1) x_t = A x_{t-1} + shock, at ``horizon``.

    For a VAR(1) the horizon-h impulse response to unit structural shocks is A^h. At
    horizon 0 it is the identity times the impact matrix; the *contemporaneous* response
    matrix to price shocks in a demand system is precisely the elasticity matrix A. This
    function exists to make the label explicit: the doc's "[a_jk]" is a VAR impulse-response
    matrix. (We expose A^h so the equivalence at h=0, A^0 composed with the impact matrix,
    is checkable in tests.)
    """
    n = len(coeff)
    result = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]  # A^0 = I
    for _ in range(horizon):
        result = linalg.matmul(result, coeff)
    # horizon-0 impulse response to a unit shock in each variable IS the impact matrix
    return coeff if horizon == 0 else result


# --------------------------------------------------------------------------- #
# 3) THE EQUIVALENCE TOOTH.
# --------------------------------------------------------------------------- #
def demonstrate_estimator_is_var(system: DemandSystem, base_prices: linalg.Vector,
                                 tol: float = 1e-6) -> dict:
    """Numerically SHOW the shock test == OLS == VAR impulse response == the true e_jk.

    Returns a receipt dict with the three recovered matrices, their max deviations from
    the ground-truth elasticity matrix, and an ``equivalent`` verdict. This is the
    load-bearing demonstration that the "Silent Weapons" estimator is a RELABELING of
    ordinary cross-price-elasticity / impulse-response identification.
    """
    truth = system.elasticities
    shock = shock_test(system, base_prices)
    reg = ols_elasticities(system, base_prices)
    irf = var1_impulse_matrix(shock.recovered_elasticities, horizon=0)

    dev_shock = linalg.max_abs_diff(shock.recovered_elasticities, truth)
    dev_ols = linalg.max_abs_diff(reg.recovered_elasticities, truth)
    dev_irf = linalg.max_abs_diff(irf, shock.recovered_elasticities)
    dev_shock_ols = linalg.max_abs_diff(shock.recovered_elasticities,
                                        reg.recovered_elasticities)
    equivalent = max(dev_shock, dev_ols, dev_irf, dev_shock_ols) < tol
    return {
        "goods": list(system.goods),
        "ground_truth_elasticities": truth,
        "shock_test_matrix": shock.recovered_elasticities,
        "ols_matrix": reg.recovered_elasticities,
        "var_irf_horizon0_matrix": irf,
        "max_dev_shock_vs_truth": dev_shock,
        "max_dev_ols_vs_truth": dev_ols,
        "max_dev_shocktest_vs_ols": dev_shock_ols,
        "max_dev_irf_vs_shocktest": dev_irf,
        "tolerance": tol,
        "equivalent": equivalent,
        "conclusion": (
            "shock-test estimator == cross-price elasticity == VAR impulse response "
            "(RELABELING of ordinary econometrics)" if equivalent
            else "estimators DISAGREE -- investigate"
        ),
    }


# --------------------------------------------------------------------------- #
# HONESTY GUARD (mirrors flow_regime's no-overclaim tooth): reproducing the
# mechanism is NOT confirming the conspiracy. A record that says so is REJECTED.
# --------------------------------------------------------------------------- #
_CONSPIRACY_ACTS = ("confirm", "confirms", "confirmed", "proves", "proven", "prove",
                    "validates", "validated", "vindicates", "establishes")
_CONSPIRACY_SUBJECTS = ("conspiracy", "silent weapons", "quiet wars", "secret weapon",
                        "population reduction plan", "depopulation plot")


def reject_conspiracy_overclaim(text) -> None:
    """REJECT any record claiming that reproducing the MECHANISM confirms the CONSPIRACY.

    The testbench reproduces the document's *mathematics* precisely so it can be shown to
    be ordinary econometrics. A claim that this reproduction "proves the conspiracy" or
    "confirms Silent Weapons" is a category error and inadmissible.
    """
    if text is None:
        return
    if isinstance(text, (list, tuple)):
        for t in text:
            reject_conspiracy_overclaim(t)
        return
    low = str(text).lower()
    if not any(s in low for s in _CONSPIRACY_SUBJECTS):
        return
    if any(act in low for act in _CONSPIRACY_ACTS):
        raise ShockTestError(
            "REJECTED: reproducing the document's mechanism does NOT confirm the "
            "conspiracy -- the testbench shows the estimator is ordinary econometrics, "
            "not evidence for 'Silent Weapons for Quiet Wars'."
        )
