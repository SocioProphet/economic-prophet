"""Verified integration + external validity for the estate financial spine.

This package does NOT re-implement any financial primitive. It *consumes* the
already-merged kernels and asserts real behaviour:

  * the risk-measure kernel ``open_ep_framework.risk_measures`` (economic-prophet
    #43/#44) -- the single ``risk(F, kernel, ...)`` interface over a loss
    distribution F;
  * the Merton / vol-surface market bridge ``open_ep_framework.market_instruments``
    (economic-prophet #44);
  * the ``risk_distribution_F`` descriptor SHAPE emitted by the memory-regime
    characterizer (memory-mesh #50) -- consumed as a contract, not forked. The
    descriptor's own ``raroc_interface`` field literally names
    ``risk(F, reference, kernel, horizon)``; this package proves that seam holds.

Two kinds of teeth live here:

  1. Cross-consumption conformance (``regime_f``): a regime-F descriptor is turned
     into a ``LossDistribution`` and scored through the kernel. Swapping a
     Gaussian-tail regime for a fat-tailed regime AT EQUAL VARIANCE must STRICTLY
     increase the tail measure (ES) -- the proof the F is actually consumed and
     that regime choice changes the price.

  2. Reference-data calibration (external validity): the kernel's numeric ES is
     matched against the closed-form Normal ES, Merton PD is matched against an
     analytic distance-to-default reference, and Sharpe / downside-deviation are
     matched against their analytic identities.

Everything here is deterministic and stdlib-only so estate CI is reproducible.
"""
