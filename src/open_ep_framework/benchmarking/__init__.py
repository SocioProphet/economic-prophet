"""Index-relative benchmarking: the baseline-vs-idiosyncratic decomposition (IRB-1).

A contract-with-teeth for cross-cohort measurement. Absolute levels are NOT
comparable across currencies / regions / legal regimes; only the DIMENSIONLESS
idiosyncratic differential is. Every measure ``X`` on a cohort must be attributed
to a declared baseline index ``B`` as ``X = beta*B + epsilon`` (systematic +
idiosyncratic), the split must reconcile in level AND in variance, and any
cross-frame comparison must ride the unit-free differential -- never an absolute
level.

Grounded in the estate risk kernel (RM-1 ``risk_measures``): the same
systematic/idiosyncratic factorization that the credit shock
``PD_short = PD_long * (w1*systematic + w2*idiosyncratic)`` and the CAPM market
beta already use. The RM-1 ``LossDistribution.beta`` field is the market beta of a
return F; IRB-1 is the general single-factor decomposition of any cohort measure
against its declared baseline.

Deterministic and stdlib-only. Measurement, simulation and audit only.
"""
from . import index_relative  # noqa: F401

__all__ = ["index_relative"]
