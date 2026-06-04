# Policy Simulation UVMC Advisory Mapping v0.1

Status: schema-first advisory evidence mapping

Authority repo: `SocioProphet/economic-prophet`

## Purpose

This note maps policy-simulation profile summaries into the Unified Value Measurement Calculus (UVMC) as advisory measured evidence objects.

A policy simulation profile is not Economic Profit, not policy correctness, not runtime authority, and not release authority. It is an evidence object that can be measured, audited, governed, and routed to downstream consumers under explicit triparty constraints.

## Mapping rule

The policy simulation profile remains the source object. The UVMC measured entity is a projection over that source object.

```text
policy_simulation_profile -> policy_simulation_measured_entity
```

The measured entity exists to make the profile comparable and governable inside the broader Economic Prophet measurement graph.

## Field mapping

| Policy simulation profile | UVMC advisory measured entity |
| --- | --- |
| `profile_id` | `measured_entity_id` and `profile_id` |
| `scenario.scenario_id` | `measurement_context.scenario_ref` |
| `donor_corpus.repository` | `source_ref` |
| `donor_corpus.runtime_dependency` | `governance_control.runtime_dependency` |
| `reward_functionals[*].release_authority` | `governance_control.release_authority` |
| `triparty_faces[*]` | `triparty_measurement` |
| `audit_receipt.run_id` | `calculation_receipt.run_id` |
| `audit_receipt.input_hash` | `calculation_receipt.input_hash` |
| `audit_receipt.output_hash` | `calculation_receipt.output_hash` |

## Advisory status

Every v0.1 measured entity produced from a policy simulation profile must carry:

```text
advisory_status = advisory_evidence_only
```

This means:

- the measured entity may inform review;
- the measured entity may be ranked, compared, or routed;
- the measured entity may be attached to platform evidence;
- the measured entity may not release economic value;
- the measured entity may not authorize policy automation;
- the measured entity may not be treated as a fairness, legality, or correctness proof.

## Required gates

A valid policy simulation measured entity must preserve these invariants:

1. `governance_control.runtime_dependency` is false.
2. `governance_control.release_authority` is `advisory_only`.
3. `advisory_status` is `advisory_evidence_only`.
4. `triparty_measurement.lambda_admit <= triparty_measurement.lambda_evid`.
5. `triparty_measurement.lambda_release <= triparty_measurement.lambda_admit`.
6. `triparty_measurement.residual == lambda_evid - lambda_release` within tolerance.
7. `economic_profit` is not present as a claimed output.
8. `non_claims` explicitly preserve no-runtime, no-policy-automation, no-value-release, and no-policy-correctness boundaries.

## Relationship to UVMC

The measured entity maps into UVMC as follows:

| UVMC concept | Policy simulation advisory object |
| --- | --- |
| `uvmc:MeasurementContext` | `measurement_context` |
| `uvmc:Domain` | `policy_simulation` |
| `uvmc:KnowledgeQuality` | Optional future source/evidence strength record; v0.1 uses no score claim. |
| `uvmc:GovernanceControl` | `governance_control` |
| `uvmc:CalculationReceipt` | `calculation_receipt` |
| `uvmc:TripartyFace` | `triparty_measurement` |
| `uvmc:StandardsReference` | `authority_refs` |

## Non-claim

This mapping is not a valuation model, not a tax model, not an RL model, and not a public policy engine. It is a structured evidence projection that allows Economic Prophet, Sociosphere, systems-learning, and Prophet Platform to reason over the same source-intake artifact without collapsing boundaries.
