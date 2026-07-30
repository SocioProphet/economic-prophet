# Case Study — IBM Q2 2026: adjudicating a contested down-case

**Companion demo to** `examples/vdt_gyg_qsr.json` (Guzman y Gomez — an *up-case*).
**Artifact:** `examples/vdt_ibm_enterprise_tech.json`.
**As-of:** 2026-07-22 (official Q2 results). **Event:** −25% single-day equity drop on 2026-07-14, IBM's worst on record.

This case exists to show the Economic Prophet doing the *hard* thing a pundit's infographic cannot: **decompose a contested value destruction, carry rival causal hypotheses instead of asserting one, name the single disclosure that would settle it, and quantify how much of the market's reaction the fundamentals actually justify.**

---

## 1. The event (warranted to primary sources)

| Figure | Value | Source |
|---|---|---|
| Equity move (2026-07-14) | $290.23 → $217.07, **−25.2%** (worst day since ≥1968) | CNBC 07-14 |
| Q2 revenue | **$17.162bn, +1% YoY** (vs $17.86bn consensus) | IBM release 07-22 |
| Software | $7.761bn, **+5%** (Red Hat +11%, Data +19%, Automation +4%, **Transaction Processing −8%**) | IBM release |
| Consulting | $5.327bn, **+0.2% (flat)** | IBM release |
| Infrastructure | $3.835bn, **−7.4%** (**IBM Z mainframe −42%**) | IBM release / BigGo |
| Non-GAAP EPS | **$2.93** (GAAP $2.27) vs $3.02 consensus | IBM release |
| FY2026 guidance | trimmed to **4–5% cc revenue growth**; FCF +~$1bn YoY | IBM release |
| Securities investigation | **plaintiff-side law-firm solicitations** (BFA Law; Frank R. Cruz) — *not* SEC/DOJ; no finding of wrongdoing | BusinessWire 07-15 |

Krishna's account is explicitly a **sequencing** story: *"numerous large deals failed to close on the timelines we expected, driving the majority of our shortfall."*

---

## 2. The two rival hypotheses (the Prophet refuses to pick prematurely)

Encoded in `rival_hypotheses`. They implicate **different drivers**, with **different accumulation**, so they carry **different value consequences** and have **different observable falsifiers**.

| | **H_sequencing** (management) | **H_integrity** (the investigation's premise) |
|---|---|---|
| Cause | Late-June capex rotation to AI servers/memory; mainframe pull-forward. Deals real, just later. | Reported pipeline never as firm as booked; forecasting discipline failed. |
| EP calculus | `Δ_Volume` timing shock; `K=C·Q·S·P` intact; step levers **recover** | Collapse in **stability + provenance** → `f(K)` raises the hurdle → **persistent re-rating** + prior EP overstated (restatement risk) |
| Driver locus | `RevenueGrowth × SupplyDelivery` | `TrustComplianceResilience × (CustomerInterface + GovernanceKnowledge)` |
| Predicted observable | **RPO grows** while revenue dips | **RPO flat/down** despite the deferral claim |

**The tell that already strains H_sequencing:** consulting was *flat*, and consulting has no hardware substitute competing for its budget line — a DRAM/AI-crowd-out cause structurally cannot reach it.

**Discriminating warrant — and it is OPEN.** RPO / consulting book-to-bill is **not disclosed** in the 07-22 release (management gives only a qualitative "high-quality backlog"). The hard number lands in the Q2 10-Q. Until then the honest state is a **50/50 prior, not a verdict** — the disclosure gap sits exactly on the line that separates the hypotheses.

---

## 3. Model vs market — the reconciliation (the punchline)

Encoded in `reconciliation`.

| | EV impact | USD |
|---|---|---|
| **Market reaction** | −22% of EV (−25% equity) | **−$68.8bn** |
| **Model — operating surprise** (capitalized) | −10% to −17% of EV | **−$31bn to −$54bn** |
| Model — growth *profile* (levels) | *net positive* | **+$36bn PV** — franchise not shrinking |
| **Trust-discount residual** | −5 to −12pp | **−$15bn to −$38bn** |

**Read:** the operating surprise — a ~3.7% quarterly revenue miss, mainframe −42%, guidance trimmed to 4–5% — justifies at most ~−17% of enterprise value. The market took −22%. The unexplained **~$15–38bn (~5–12pp)** is a **multiple re-rating**, not a cash-flow markdown: the market pricing the forecasting-credibility / pipeline-integrity tail. It maps precisely to `TrustComplianceResilience`, which this VDT weights at **0.20** (vs ~0.09 for GYG), half of it in the pipeline-integrity + forecasting cells.

That residual is the quantified form of *"the market priced a 25% drop because it wasn't sure."* It **collapses toward zero if the 10-Q RPO confirms H_sequencing, and hardens if it confirms H_integrity.**

*Method (stated, not hidden):* segment value-shares Software 0.52 / Consulting 0.26 / Infrastructure 0.22; growth-to-value multiplier 2.0×–3.5×; consensus growth expectations (Software ~8–10%, Consulting ~+3%, Infra ~flat). The range is the honesty; the point estimate is not claimed.

---

## 4. Why it pairs with GYG

- **GYG** = the Prophet **valuing an up-case**: a clean forward value-driver tree, +2.7% EV uplift under stated operating levers.
- **IBM** = the Prophet **adjudicating a contested down-case**: two rival causes, a quantified trust-discount residual, and an explicit *open* warrant it declines to pre-judge.

The infographic asserted one causal story and got the provenance of its own inputs wrong (intraday "open" passed as settle; consensus mis-stated). The Prophet carries both stories, capitalizes the fundamentals, isolates the trust premium, and points at the one number that resolves it. **That contrast is the demo.**

---

## 5. Open follow-up

When IBM files the Q2 10-Q, pull the **RPO total + consulting book-to-bill**, apply `rival_hypotheses.discriminating_warrant.falsification_rule`, and flip `status` from `OPEN` to the surviving hypothesis — then the `trust_discount_residual` resolves to a fundamental or a governance loss.

*Authoring-model knowledge cutoff: January 2026. All July-2026 figures are warranted to the cited sources in `evidence_refs`, not model recall.*
