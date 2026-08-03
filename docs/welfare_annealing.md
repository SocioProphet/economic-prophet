# Value-Energy-Conservation Welfare-Annealing (WEA-1)

WEA-1 is the estate's constructive **"better framework"**: the normative *inverse* of
*"Silent Weapons for Quiet Wars."* It keeps the same value-as-energy physics — value-energy is
conserved in exchange, growth is a production *source* term, and allocations flow under a
free-energy potential read with a laminar/turbulent lens — and **flips the objective** from
elite-control / extraction to a **global quality-of-life (QoL) welfare index**. The SILENT
epistemic-firewall (Phase 4) contrasts a control-max objective against *this* welfare objective
over the *same conserved energy*.

The module (`src/open_ep_framework/welfare_annealing/`) is deterministic and stdlib-only for
hermetic CI. It is measurement / simulation / audit only — no live or shared-state writes, no
token issuance. Every constituent contract **consumes an existing estate contract by reference**
(consume-not-fork).

## The model

| Piece | Mechanism | Consumed by reference |
|-------|-----------|-----------------------|
| **Value-energy conservation in exchange** | A pure exchange creates no value-energy; it re-attributes the same conserved substance. Gains-from-trade are a *free-energy drop* on the same energy, not new substance. | IC-1 `settlement.check_conservation` (#39) |
| **Objective = global QoL index** | HDI-generalized welfare functional `QoL = Σ_i population_i · gmean(life_length, health, education)`. Geometric mean penalizes imbalance. Missing any of the four dimensions is rejected. | — (`qol.py`) |
| **Annealing dynamics** | Projected gradient flow over allocations on the fixed-energy simplex descending the free-energy potential `F(x) = −W(x)` toward the equal-marginal-welfare attractor. Each step is sum-preserving (conserves energy). | — (`anneal.py`) |
| **Laminar / turbulent lens** | A healthy anneal is a contraction to a stable fixed point (Benettin largest Lyapunov exponent < 0, monotone descent, settles) → **laminar**. A manipulated / over-driven anneal never settles → **turbulent** (same math as SILENT's self-destructive oscillation). | FRL-1 `flow_regime.lorenz` `CHAOS_LAMBDA`, `TAXONOMY_TO_FLOW` (#54) |
| **Carrying-capacity discount + renewable source** | Exchange is a conservative flow; **production** is the only source (Solow / Lockean labor-mixing). Only the *renewable* increment (harvest ≤ regeneration) is sustainable growth; "growth" funded by non-renewable drawdown is **false growth** (the paper-inductance analog). | ALC-1 `asset_ladder.RENEWABILITY_REGIME` (#52) |
| **Discounting** | Fisher real rate `(1+i)=(1+r)(1+π)`; Fisher-ideal index; exchange velocity `MV=PQ`; and the **social discount rate** (Ramsey `r = δ + η·g`) as the master parameter with a Stern-vs-Nordhaus sensitivity sweep. | `inflation.real_rate` (Fisher) |

## Teeth

A record carries one `record_kind` ∈ `{exchange, anneal, growth_path, discount}`; the teeth for
that kind are applied and a receipt-spine-hashed receipt is emitted.

**VERIFIES**
- pure exchange conserves total value-energy (within tolerance);
- the anneal monotonically lowers free-energy / raises the QoL index toward a laminar attractor,
  conserving value-energy at every step;
- a renewable-only growth path is sustainable;
- a low social-discount-rate (Stern) weights future QoL more than a high one (Nordhaus); the
  sensitivity sweep reconciles (present value monotone-decreasing in the rate).

**REJECTS / FLAGS**
- a model creating value in pure exchange (conservation violation);
- a growth path funded by non-renewable drawdown reported as sustainable (false-growth flag);
- a growth claim not Fisher-real-adjusted;
- an anneal that increases free-energy / is turbulent while claiming a healthy laminar descent
  (wrong direction);
- a QoL index missing a required dimension (population / life-length / health / education).

## Run

```bash
# one record -> audit + receipt
PYTHONPATH=src python -m open_ep_framework.welfare_annealing \
  --record examples/welfare_annealing/anneal.laminar_healthy.valid.json

# all teeth over the fixtures (VERIFIES + REJECTS + COHERENCE)
python scripts/validate_welfare_annealing.py

# per-tooth mutation tests
python -m pytest -q tests/test_welfare_annealing_*.py
```

Schema: `schemas/welfare_annealing.schema.json`. Fixtures: `examples/welfare_annealing/`.
CI: `.github/workflows/welfare-annealing.yml`.
