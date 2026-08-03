# Index-relative benchmarking + relativity-of-price value ordering

Two contracts-with-teeth: the honest **consistency model** and **factor-decomposition
layer** under the omnirisk / EP + outcome-pricing spine. Deterministic, stdlib-only,
measurement / simulation / audit only.

## A. Index-relative benchmarking (IRB-1)

`src/open_ep_framework/benchmarking/index_relative.py`

For each cohort `(asset_class, market, issuer?, rating_agency_bucket?, region?, sector?)`
a baseline index **B** is declared and any measure **X** is decomposed:

```
X_t = beta * B_t + epsilon_t          beta = cov(X, B) / var(B)
                                      epsilon_t = X_t - beta * B_t   (E[eps] = alpha)
var(X) = beta^2 var(B) + var(epsilon)  (systematic + idiosyncratic; exact, OLS-orthogonal)
```

The cross-cohort **differential** is the idiosyncratic residual expressed **unit-free**
(`idiosyncratic_z = mean(eps)/std(eps)`, `spread_to_baseline`, `cross_sectional_rank`),
so it is comparable across currencies / regions / legal-regimes even though absolute
levels are not.

Grounds the estate systematic/idiosyncratic factorization already in the RM-1 risk
kernel (`risk_measures`: the credit shock `PD_short = PD_long*(w1*systematic +
w2*idiosyncratic)` and the CAPM market `beta`), consumed **by reference**.

**Teeth.** A measure not decomposed into baseline + idiosyncratic is REJECTED; a split
that does not reconcile in level (`beta*B + eps == X`) or variance
(`beta^2 var(B) + var(eps) == var(X)`) is REJECTED; a cross-frame comparison on ABSOLUTE
levels (assuming a common price across a currency/region boundary) is REJECTED — it must
ride the dimensionless differential; a cohort with no declared baseline index is REJECTED.

## B. Relativity of price — eventual-consistency value ordering (RVO-1)

`src/open_ep_framework/value_ordering/relativity.py`

Value/price is a **partially-ordered, eventually-consistent** quantity, not a global
scalar. Each market/venue/currency is a **frame** with a local real-time price;
cross-frame reconciliation is a **causal (vector-clock) partial order**, never a global
total order. A CRDT-like merge (a per-frame LWW-register keyed by the total order
`(lamport, receipt_hash)`) is **commutative + associative + idempotent** → it converges
to an eventually-consistent global view from any interleaving.

The causal order is bound to the estate **receipt spine**: each value event is
hash-chained (`receipt = SHA-256(prev_receipt || canonical(event))`), so the receipt
chain **is** the value-event clock. The **holographic-message-stream** (TriTRPC #99) is
the eventually-consistent log this order rides on (by reference).

**Teeth.** A merge that depends on application order is REJECTED (not a CRDT); a claim of
a single GLOBAL price / global simultaneity is REJECTED (the relativity-of-value guard,
mirroring the flow-regime Navier-Stokes no-overclaim tooth); imposing a TOTAL order over
causally-concurrent events is REJECTED; a record asserting IMMEDIATE global consistency
(`consistency_scope == immediate_global`) is REJECTED — value is local + eventual.

## Run

```bash
make benchmarking        # IRB-1 receipt (stdlib gate)
make value-ordering      # RVO-1 receipt (stdlib gate)
make value-relativity    # full fixture teeth for both (needs jsonschema)
python -m pytest -q tests/test_index_relative.py tests/test_value_ordering.py
```

## Upward bindings

See [`docs/bindings/index_relative_value_ordering_bindings.md`](bindings/index_relative_value_ordering_bindings.md)
and the routed governed concepts in
[`docs/concepts/systema_concept_entries.jsonld`](concepts/systema_concept_entries.jsonld).
