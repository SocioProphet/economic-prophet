# Infinite Duration Forecast Curve v0.1

Status: schema-first advisory forecast curve

Authority repo: `SocioProphet/economic-prophet`

## Purpose

Economic Prophet needs a rate-like forecast object for long-horizon and infinite-duration reasoning. This is not a trading curve, not a yield-curve model, and not a market forecast claim. It is a governed measurement object that lets UVMC scenarios carry finite forecast nodes plus a terminal/infinite-duration node.

## Core idea

An infinite-duration forecast curve is a term structure with two regions:

1. finite forecast nodes, such as year 1, year 3, year 5, and year 10;
2. a terminal node that represents a stabilized perpetuity-style continuation assumption.

```text
finite nodes -> terminal node -> advisory perpetuity continuation
```

The terminal node must carry both a terminal discount rate and a terminal growth rate. The terminal growth rate must be lower than the terminal discount rate. If this invariant fails, the curve is invalid.

## Design boundary

This curve is advisory measurement infrastructure only. It does not price securities, forecast markets, authorize policy automation, release economic value, or claim investment correctness.

## Required invariants

A valid v0.1 curve must satisfy:

1. `curve_type = infinite_duration_forecast_curve`.
2. `mode = advisory`.
3. finite nodes are non-empty.
4. finite node tenors are positive and strictly increasing.
5. finite node rates are non-negative.
6. terminal discount rate is positive.
7. terminal growth rate is non-negative.
8. terminal growth rate is strictly lower than terminal discount rate.
9. advisory non-claims are present.
10. calculation receipt references are present.

## Derived quantities

For the terminal node:

```text
spread = terminal_discount_rate - terminal_growth_rate
perpetuity_multiple = 1 / spread
macaulay_duration_proxy = (1 + terminal_discount_rate) / spread
```

The `macaulay_duration_proxy` is finite when the spread is positive. The cash-flow horizon is infinite, but duration exposure is finite under a stable positive spread.

## Relationship to UVMC

This curve maps into UVMC as:

| UVMC concept | Forecast curve field |
| --- | --- |
| `uvmc:MeasurementContext` | `measurement_context` |
| `uvmc:DiscountCurve` | `finite_nodes` and `terminal_node` |
| `uvmc:CalculationReceipt` | `calculation_receipt` |
| `uvmc:GovernanceControl` | `governance_control` |
| `uvmc:StandardsReference` | `authority_refs` |

## Non-claim

This is a forecast curve object, not a prediction guarantee. It is intended to support scenario discipline and long-horizon comparability inside Economic Prophet.
