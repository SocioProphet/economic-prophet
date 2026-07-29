# Architecture Overview

The repository is layered in two phases.

## Phase 1: framework as documentation
- white paper
- product specification
- architecture notes
- integrations roadmap
- schemas

## Phase 2: framework as first-class modeling and simulation platform
- reference Python package
- zero-EP pricing solver
- FTP engine
- expected-loss engine
- recovery surface engine
- capital charge engine
- attribution engine
- audit-pack generator

## Runtime equation

```text
EP_hat(o,t,h) = Revenue_hat - ExpectedLoss_hat - Expense_hat - FundingCosts_hat + FundingCredits_hat - Taxes_hat - CapitalCharge_hat
CapitalCharge_hat = Hurdle_hat * Capital_hat
ExpectedLoss_hat  = PD_hat * LGD_hat * EAD_hat
```

## Object graph

Transaction -> Instrument -> Account -> Relationship -> Portfolio -> LineOfBusiness -> LegalEntity

Side objects:
- CollateralSet
- FundingSource
- HedgeSet
- CounterpartySet

## Audit requirements

Every run should emit:
- assumptions
- data provenance
- model version
- parameter version
- scenario set
- solver output
- reconciliation
- attribution
- exceptions / overrides
