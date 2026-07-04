# Unified Value Measurement Calculus — Class and Entity Crosswalk v0.1

## Purpose

This document aligns the Unified Value Measurement Calculus to the Economic Profit framework, the `economic-prophet` canonical object model, NAICS/ISIC-style industry overlays, IBM-style KPI trees, knowledge quality, and the World Economy Digital Twin corridor model.

The goal is to make each class and entity measurable. Every object that participates in value measurement must say:

1. what class it belongs to,
2. which EP term it affects,
3. which KPI driver family it maps to,
4. which industry/domain overlay weights it uses,
5. which knowledge quality variables apply,
6. which provenance class applies,
7. which digital twin corridor owns or reviews the action.

## Core equations

### Economic Profit

```text
EP_t = NOPAT_adj_t - HurdleRate_adj_t * Capital_adj_{t-1}
```

### Value as additive EP stream

```text
Value = NPV(EP) = sum_t EP_t / (1 + HurdleRate_adj_t)^t
```

### Knowledge-adjusted EP

```text
K_EP_t = NOPAT_adj_t - (HurdleRate_adj_t - f(K)) * Capital_adj_{t-1}
```

where:

```text
K = C * Q * S * P
```

with:

- `C`: coverage,
- `Q`: coherence / quality,
- `S`: stability,
- `P`: provenance.

### EP variance decomposition

```text
Delta_EP = Delta_Price + Delta_Volume + Delta_Cost + Delta_Productivity + Delta_Capital
```

### KPI tensor mapping

```text
Delta_EP = sum_{i,d,o,k} T_{i,d,o,k} * Delta_KPI_{i,d,o,k}
```

where:

- `i` = industry or sector overlay,
- `d` = value-driver family,
- `o` = object/entity level,
- `k` = KPI leaf.

## Object-level alignment

| Class / Entity | Existing economic-prophet analog | EP Term(s) | KPI Driver Family | Knowledge Variables | Digital Twin Corridor | Provenance Requirements |
|---|---|---|---|---|---|---|
| LegalEntity | `legal_entity` | NOPAT, Capital, hurdle | enterprise value, governance, risk | source coverage, entity lineage | Supervisory Federation | measured or governed entity registry |
| LineOfBusiness | `line_of_business` | NOPAT, capital allocation | revenue, cost, productivity, capital | KPI coverage and stability | Supervisory Federation / Treasury | measured financials plus governed allocation |
| Relationship | `relationship` | revenue, EL, FC/FCR, capital | client value, cross-sell, utilization, risk | relationship context completeness | Treasury / Margin / Settlement | measured account graph plus estimated risk |
| Account | `account` | revenue, cost, utilization, FC | volume, utilization, servicing cost | account lineage quality | Settlement Queue | measured ledger and account context |
| Instrument | `instrument` | revenue, EL, FC, capital charge | price, credit risk, liquidity cost | instrument terms coverage | Treasury / Margin | measured contract plus estimated risk |
| TransactionEvent | `transaction_event` | volume, revenue, cost, event proof | event volume and operational throughput | event proof strength | Settlement Queue | measured event evidence |
| CollateralSet | `collateral_set` | LGD, EC, capital offset | collateral quality, haircut, encumbrance | valuation provenance | Collateral Operations | measured custody plus estimated valuation |
| FundingSource | `funding_source` | FC, FCR, FTP premia | liquidity, term, optionality | curve source quality | Treasury / Liquidity | measured or estimated curve source |
| HedgeSet | `hedge_set` | market-risk EC, FC/FCR | hedge effectiveness, basis risk | hedge coverage stability | Treasury / Margin | measured trade and model evidence |
| CivicAsset | new | EC offset, EP_Civ | buffer capacity, resilience, public-good maintenance | civic verification and capacity evidence | Collateral / Fail-Repair | measured or audited capacity registry |
| ReputationProfile | new | EL, EC_req, access, reward weighting | reliability, trust, stewardship, governance | event provenance and graph stability | Settlement / Federation | measured events plus estimated graph trust |
| HellerBalance | new | exchange velocity, liquidity, settlement | circulation, demurrage, reciprocity | ledger completeness | Treasury / Settlement | measured balance ledger |
| ReplayRow | new | historical replay, evidence grading | replay quality, proxy hardening | source grade and uncertainty | Federation | imputed / estimated with explicit grade |
| StandardsProfile | new | adjustments, controls, reporting | IFRS/GAAP/Basel/NIST/OECD alignment | standards mapping completeness | Federation / Governance | governed standards registry |

## Industry overlay requirements

Every measured entity should carry an optional industry overlay.

```json
{
  "industry_overlay": {
    "naics": "522110",
    "isic": "K6419",
    "sector_label": "Depository Credit Intermediation",
    "driver_weight_matrix_id": "banking.v1"
  }
}
```

The overlay selects a weighting matrix:

```text
W_industry(driver, domain)
```

where weights sum to one inside each declared measurement lens.

## Driver families

| Driver Family | Typical KPI Leaves | EP Effect |
|---|---|---|
| Price | spread, fee rate, unit price, discount rate | revenue and margin |
| Volume | units, balances, transactions, active users | revenue and cost scale |
| Cost | unit cost, servicing cost, fixed overhead | V_minus / expenses |
| Productivity | cycle time, automation rate, error rate, capacity utilization | cost and throughput |
| Capital | invested capital, EC_req, collateral usage, working capital | capital charge / reservation |
| Risk | PD, LGD, EAD, ES, operational incidents | EL and EC |
| Liquidity | FTP premia, queue depth, settlement delay, funding stability | FC/FCR |
| Knowledge | coverage, coherence, stability, provenance | K adjustment and confidence |
| Civic | buffer capacity, repair capacity, resilience days | EC offset and EP_Civ |
| Human | health, capability, participation, underemployment | V_plus and system resilience |

## Standards alignment surface

| Standard Family | Framework Use | Entity Attachment |
|---|---|---|
| IFRS / GAAP | accounting adjustments, invested capital, NOPAT normalization | LegalEntity, LineOfBusiness |
| Basel / ICAAP | capital, expected loss, economic capital, stress buffers | Instrument, Relationship, Portfolio |
| NIST / security controls | provenance, evidence custody, identity, cyber risk | Event, Evidence, ReputationProfile |
| OECD / SNA / NAICS / ISIC | industry overlays, macro comparability, value-added context | StandardsProfile, ReplayRow |
| Internal ontology | canonical object graph and typed lineage | all objects |

## Metrics and tensors

### Metric

```text
g(u,v) = sum_{i=1}^{22} w_i u_i v_i + w_K u_23 v_23 + sum_{j=24}^{26} w_j u_j v_j
```

### Distance

```text
d(u,v) = arccos(g(u,v) / sqrt(g(u,u)) * sqrt(g(v,v)))
```

Implementation note: the denominator must be parsed as `sqrt(g(u,u)) * sqrt(g(v,v))`; code should avoid ambiguous precedence.

### Risk-capital tensor

```text
CapitalCharge = sum_{i,r,t} alpha_{i,r,t} R_{i,r,t}
```

### Knowledge adjustment tensor

```text
HurdleRate_adj = HurdleRate + <K_ab, theta_ab>
```

In the non-usury Human Economic Profit formulation, this may be translated into capital reservation and confidence adjustment rather than a literal interest-rate increase.

## Class-level measurement contract

Every class must expose these fields or derivable equivalents:

```json
{
  "object_id": "string",
  "object_class": "string",
  "period": "string",
  "industry_overlay": {},
  "value_driver_family": "string",
  "kpi_leaf": "string",
  "ep_term": "string",
  "knowledge_quality": {
    "coverage": 0.0,
    "coherence": 0.0,
    "stability": 0.0,
    "provenance": 0.0
  },
  "provenance_class": "measured|estimated|governed|imputed",
  "digital_twin_corridor": "string",
  "evidence_ref": "string"
}
```

## Banking example mapping

| Object | KPI | Driver | EP Term | Corridor |
|---|---|---|---|---|
| Instrument loan | contractual spread | price | revenue | Treasury |
| Instrument loan | PD/LGD/EAD | risk | EL / EC | Margin |
| Funding source | FTP curve | liquidity | FC / FCR | Treasury |
| Collateral set | haircut / eligibility | capital/risk | LGD / EC offset | Collateral |
| Relationship | cross-sell credit | revenue/productivity | NOPAT | Federation / Treasury |

## Healthcare example mapping

| Object | KPI | Driver | EP Term | Corridor |
|---|---|---|---|---|
| Clinic civic asset | verified service capacity | civic | EC offset | Collateral / Fail-Repair |
| Care event | patient care hours | human/productivity | V_plus | Settlement |
| Medical supply buffer | coverage days | civic/liquidity | EC offset / FC | Treasury / Collateral |
| Reputation profile | care reliability | risk/human | EL and access | Settlement |

## Telecom example mapping

| Object | KPI | Driver | EP Term | Corridor |
|---|---|---|---|---|
| Network asset | uptime | productivity/civic | V_plus / EC offset | Fail-Repair |
| Subscriber account | ARPU | price/volume | revenue | Settlement |
| Spectrum/capex | invested capital | capital | capital charge | Margin |
| Outage event | downtime minutes | cost/risk | V_minus / EL | Fail-Repair |

## Implementation backlog

1. Add `unified-value-entity.schema.json`.
2. Add `knowledge-quality.schema.json`.
3. Add `industry-overlay.schema.json`.
4. Add fixtures for banking, healthcare, and telecom.
5. Add tensor mapping examples in Python.
6. Add invariant tests: weights sum to one, K in `[0,1]`, EP decomposition reconciles, provenance is non-null.
