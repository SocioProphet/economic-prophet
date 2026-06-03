# Policy Simulation Source Intake

Status: v0.1 schema-first boundary.

Authority repo: `SocioProphet/economic-prophet`

Reference corpus: `SocioProphet/ai-economist`

## Purpose

This note records how Economic Prophet treats an external economic simulation reference corpus as design input. Economic Prophet remains the canonical measurement engine. The first boundary is documentation, schema, fixture, and deterministic validation only.

The reference corpus is useful for simulation grammar: environment lifecycle, scenario composition, actor/planner separation, policy components, objective functions, and replay logs. It is not admitted as a production runtime dependency in v0.1.

## Intake rule

Extract durable patterns. Do not vendor the old runtime stack. Do not import the donor package. Do not add training dependencies. Do not treat a simulation score as release authority.

A profile may inform Economic Prophet only when it can be expressed as auditable measurement data: scenario, actors, planner, components, reward functionals, triparty faces, and an audit receipt.

## Retained patterns

1. Reset/step style simulation lifecycle.
2. Scenario and component decomposition.
3. Participant actor and planner separation.
4. Explicit policy components such as pricing, allocation, tax, subsidy, redistribution, or constraint mechanisms.
5. Named objective functions instead of hidden preferences.
6. Replay and audit traces.
7. Stated intended-use and non-goal boundaries.

## Stripped surfaces

1. Direct runtime dependency on the reference corpus.
2. Old dependency pins and notebook-first packaging.
3. Training framework dependencies in the first tranche.
4. Demo-specific claims or public-policy conclusions.
5. Live policy execution.
6. External settlement, exchange, issuance, or redemption behavior.

## Economic Prophet mapping

A policy simulation profile maps into the Economic Prophet measurement language as follows:

```text
scenario -> economic measurement context
actor -> relationship, counterparty, or sphere participant
planner -> governance or release authority
component -> pricing, allocation, capital, risk, subsidy, or constraint mechanism
reward functional -> explicit objective function
triparty face -> evidential, admitted, released, and residual quantities
audit receipt -> deterministic replay and proof boundary
```

## Triparty boundary

A simulation score is advisory. Release requires a triparty face with visible quantities, admitted quantities, released quantities, residuals, state, and proof reference.

The v0.1 fixture deliberately uses `ReviewRequired` to keep the distinction between simulation evidence and release authority explicit.

## First implementation boundary

The first implementation consists of:

1. `schemas/policy_simulation_profile.schema.json`
2. `examples/policy_simulation_profile.json`
3. `src/open_ep_framework/policy_simulation.py`
4. `tests/test_policy_simulation.py`

No runtime import from the reference corpus is introduced.
