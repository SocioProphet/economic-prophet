"""Relativity of price: eventual-consistency value ordering (RVO-1).

Value / price is modeled as a PARTIALLY-ordered, eventually-consistent quantity,
NOT a global scalar. Each market / venue / currency is a FRAME with a local,
real-time price; cross-frame reconciliation is a CAUSAL (vector-clock) partial
order, never a global total order. A CRDT-like merge of per-frame value
observations is commutative + associative + idempotent, so it converges to an
eventually-consistent global view regardless of the order observations arrive.

The causal order is bound to the estate receipt spine: each value event is
hash-chained (SHA-256 over the previous receipt + the event body), so the receipt
chain IS the value-event clock. The holographic-message-stream (TriTRPC #99) is
the eventually-consistent log this order rides on (by reference).

Deterministic and stdlib-only. Measurement, simulation and audit only.
"""
from . import relativity  # noqa: F401

__all__ = ["relativity"]
