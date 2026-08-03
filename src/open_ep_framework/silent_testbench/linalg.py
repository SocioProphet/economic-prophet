"""Deterministic, stdlib-only linear algebra for the silent_testbench.

Just enough dense linear algebra to (a) solve ``[a_jk][X_k] = [Y_j]`` and invert the
recovered coefficient matrix -- the two operations the "Silent Weapons" shock-test
estimator (SILENT pp.26-29) prescribes -- and (b) run the ordinary-least-squares
regression that the shock test turns out to BE. No numpy: partial-pivot Gaussian
elimination and normal-equations OLS, both exact-arithmetic-friendly and reproducible.
"""
from __future__ import annotations

Matrix = list  # list[list[float]]
Vector = list  # list[float]


class SingularMatrixError(ValueError):
    """Raised when a system is singular / rank-deficient -- REJECTED, not silently fudged."""


def _copy(matrix: Matrix) -> Matrix:
    return [list(row) for row in matrix]


def _dims(matrix: Matrix) -> tuple[int, int]:
    rows = len(matrix)
    cols = len(matrix[0]) if rows else 0
    for row in matrix:
        if len(row) != cols:
            raise ValueError("ragged matrix")
    return rows, cols


def matvec(matrix: Matrix, vector: Vector) -> Vector:
    return [sum(a * x for a, x in zip(row, vector)) for row in matrix]


def matmul(a: Matrix, b: Matrix) -> Matrix:
    ra, ca = _dims(a)
    rb, cb = _dims(b)
    if ca != rb:
        raise ValueError(f"incompatible shapes {ra}x{ca} @ {rb}x{cb}")
    return [[sum(a[i][k] * b[k][j] for k in range(ca)) for j in range(cb)] for i in range(ra)]


def transpose(matrix: Matrix) -> Matrix:
    rows, cols = _dims(matrix)
    return [[matrix[i][j] for i in range(rows)] for j in range(cols)]


def solve(matrix: Matrix, rhs: Vector, tol: float = 1e-12) -> Vector:
    """Solve ``A x = b`` by partial-pivot Gaussian elimination."""
    n, cols = _dims(matrix)
    if n != cols:
        raise ValueError("solve requires a square matrix")
    if len(rhs) != n:
        raise ValueError("rhs length mismatch")
    aug = [list(matrix[i]) + [rhs[i]] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < tol:
            raise SingularMatrixError("singular matrix in solve")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        piv = aug[col][col]
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col] / piv
            if factor == 0.0:
                continue
            for c in range(col, n + 1):
                aug[r][c] -= factor * aug[col][c]
    return [aug[i][n] / aug[i][i] for i in range(n)]


def invert(matrix: Matrix, tol: float = 1e-12) -> Matrix:
    """Invert a square matrix (Gauss-Jordan). The doc's ``[a_jk] -> [b_kj]`` step."""
    n, cols = _dims(matrix)
    if n != cols:
        raise ValueError("invert requires a square matrix")
    aug = [list(matrix[i]) + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < tol:
            raise SingularMatrixError("singular matrix in invert")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        piv = aug[col][col]
        for c in range(2 * n):
            aug[col][c] /= piv
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            if factor == 0.0:
                continue
            for c in range(2 * n):
                aug[r][c] -= factor * aug[col][c]
    return [row[n:] for row in aug]


def ols(design: Matrix, target: Vector, tol: float = 1e-12) -> Vector:
    """Ordinary least squares beta = (X'X)^-1 X'y via the normal equations.

    This is the estimator an economist reaches for; the whole point of the testbench is
    to show the "Silent Weapons" shock test recovers the SAME coefficients.
    """
    xt = transpose(design)
    xtx = matmul(xt, design)
    xty = matvec(xt, target)
    return solve(xtx, xty, tol=tol)


def max_abs_diff(a, b) -> float:
    """Max absolute elementwise difference of two equally-shaped matrices/vectors."""
    if a and isinstance(a[0], (list, tuple)):
        return max(abs(x - y) for ra, rb in zip(a, b) for x, y in zip(ra, rb))
    return max(abs(x - y) for x, y in zip(a, b))
