"""Outcome-based wisdom-services pricing (OPX-1).

The commercial layer of the estate: it prices a customer engagement as a
risk-adjusted, receipted VALUE-TRANSFER, splits it coherently across the mesh,
and settles on a real-asset-backed token unit. It consumes the economic-prophet
financial spine (EP kernel, risk-measure family, conservation settlement, term
calculus, Fisher-real separation, Jacob's-ladder asset base) BY REFERENCE and
adds no new physics -- it *denominates* a commercial price in the invariants the
spine already enforces.

See ``pricing.py`` for the six-stage decomposition and the teeth.
Deterministic and stdlib-only. Measurement, simulation and audit only: no live
money movement, token issuance, redemption rights, or settlement rails.
"""
from __future__ import annotations

from .pricing import (
    OutcomePricingError,
    price_engagement,
    run_outcome_pricing,
)

__all__ = [
    "OutcomePricingError",
    "price_engagement",
    "run_outcome_pricing",
]
