#!/usr/bin/env python3
"""Validate the flow-regime contracts (FRT-1 trinomial + FRL-1 turbulence lens) --
with teeth in BOTH directions (a control that never fires is suspect).

Tooth families:

  VERIFIES   Valid fixtures are schema-valid AND self-consistent when recomputed by the
             deterministic module: the memoryless trinomial CONVERGES to Black-Scholes;
             the mean-reverting trinomial DIFFERS from Black-Scholes (mean reversion is
             priced); the classic Lorenz set classifies TURBULENT (positive Lyapunov, no
             stable fixed point) and a sub-critical set classifies LAMINAR (stable fixed
             point, negative Lyapunov); the Lyapunov sign AGREES with the memory-mesh
             taxonomy label.

  REJECTS    Every committed *.invalid.json is refused for its specific tooth: a branch
             probability outside [0,1]; a "regime-aware" price identical to Black-Scholes
             across regimes (the regime was never consumed); a Navier-Stokes
             existence/smoothness over-claim; a wrong scope pin; a Lyapunov-sign vs
             taxonomy mismatch.

  COHERENCE  Each valid trinomial fixture's node probabilities lie in [0,1] and sum to 1;
             each valid lens fixture's scope is pinned to analogue_characterization_only.

Consume-by-reference: Black-76 from market_instruments (MKT-1); the OU fit, the
process->regime->option crosswalk taxonomy and the Lyapunov/regime taxonomy from the
memory-mesh characterizer. Deterministic, stdlib + jsonschema only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from open_ep_framework.flow_regime.trinomial import (  # noqa: E402
    EuropeanOption, RegimeAwareTrinomial, RegimeSpec, TrinomialError,
    black_scholes_reference,
)
from open_ep_framework.flow_regime.lorenz import (  # noqa: E402
    FlowRegimeError, classify_flow, lyapunov_sign_agrees,
    reject_navier_stokes_overclaim,
)

SCHEMA_TRINOMIAL = ROOT / "schemas" / "trinomial_option.schema.json"
SCHEMA_LENS = ROOT / "schemas" / "flow_regime_lens.schema.json"
EXAMPLES = ROOT / "examples" / "flow_regime"

BS_LIMIT_TOL = 8e-3       # |trinomial - BS| in the memoryless limit
OU_DIFF_MIN = 0.25        # |trinomial - BS| must exceed this in an OU regime
SELF_CONSISTENCY_TOL = 1e-3

_passes = 0


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ok(msg: str) -> None:
    global _passes
    _passes += 1
    print(f"  PASS  {msg}")


def fail(msg: str) -> None:
    print(f"  FAIL  {msg}")
    sys.exit(1)


def _opt(rec: dict) -> EuropeanOption:
    o = rec["option"]
    return EuropeanOption(
        spot=o["spot"], strike=o["strike"], vol=o["vol"], maturity=o["maturity"],
        rate=o.get("rate", 0.0), call=o.get("call", True),
    )


def _regime(rec: dict) -> RegimeSpec:
    r = rec["regime"]
    return RegimeSpec(
        kind=r["kind"], theta=r.get("theta", 0.0), mu=r.get("mu", 0.0),
        momentum_drift=r.get("momentum_drift", 0.0), source_regime=r.get("source_regime", ""),
    )


# --------------------------------------------------------------------------- #
# trinomial teeth
# --------------------------------------------------------------------------- #
def verify_trinomial_valid(path: Path, schema) -> None:
    rec = load(path)
    errs = sorted(schema.iter_errors(rec), key=lambda e: e.path)
    if errs:
        fail(f"{path.name}: schema-invalid: {errs[0].message}")
    opt, reg = _opt(rec), _regime(rec)
    steps = rec.get("steps", 200)
    tri = RegimeAwareTrinomial(opt, reg, steps=steps)
    price = tri.price()
    bs = black_scholes_reference(opt)

    # self-consistency: reported == recomputed
    if "prices" in rec:
        if abs(rec["prices"]["trinomial_price"] - price) > SELF_CONSISTENCY_TOL:
            fail(f"{path.name}: reported price {rec['prices']['trinomial_price']} != "
                 f"recomputed {price:.6f}")

    # node probabilities coherence tooth (each in [0,1], sum to 1)
    for pu, pm, pd in tri.node_probabilities():
        if not (0.0 <= pu <= 1.0 and 0.0 <= pm <= 1.0 and 0.0 <= pd <= 1.0):
            fail(f"{path.name}: a node probability escaped [0,1]")
        if abs(pu + pm + pd - 1.0) > 1e-6:
            fail(f"{path.name}: node probabilities do not sum to 1")

    if reg.kind == "memoryless":
        if abs(price - bs) > BS_LIMIT_TOL:
            fail(f"{path.name}: BS-limit tooth: |{price:.6f}-{bs:.6f}| > {BS_LIMIT_TOL}")
        ok(f"{path.name}: memoryless -> Black-Scholes within {BS_LIMIT_TOL} "
           f"(|diff|={abs(price - bs):.2e})")
    elif reg.kind in ("mean_reverting", "chaotic"):
        if abs(price - bs) <= OU_DIFF_MIN:
            fail(f"{path.name}: OU-differs tooth did not fire (|diff|={abs(price - bs):.4f})")
        ok(f"{path.name}: {reg.kind} DIFFERS from Black-Scholes "
           f"(|diff|={abs(price - bs):.4f}); half_life={reg.half_life:.4f}")
    else:
        ok(f"{path.name}: {reg.kind} priced ({price:.4f})")


def reject_trinomial_invalid(path: Path, schema) -> None:
    rec = load(path)
    name = path.name
    # 1) schema rejection (e.g. a probability outside [0,1])
    errs = list(schema.iter_errors(rec))
    if errs:
        ok(f"{name}: REJECTED by schema ({errs[0].message[:60]})")
        return
    # 2) branch-probability tooth: any declared triple out of [0,1] or non-normalized
    if "branch_probabilities" in rec:
        for trip in rec["branch_probabilities"]:
            if any(p < 0 or p > 1 for p in trip) or abs(sum(trip) - 1.0) > 1e-6:
                ok(f"{name}: REJECTED -- branch probability out of [0,1] / not normalized")
                return
    # 3) regime-really-consumed tooth: a mean_reverting/chaotic record whose price
    #    equals Black-Scholes proves the regime was never consumed.
    if "prices" in rec and rec["regime"]["kind"] in ("mean_reverting", "chaotic"):
        p = rec["prices"]
        if abs(p.get("trinomial_price", 0.0) - p.get("black_scholes_reference", 0.0)) <= OU_DIFF_MIN:
            ok(f"{name}: REJECTED -- regime-aware price identical to Black-Scholes "
               f"(regime not consumed)")
            return
    fail(f"{name}: expected REJECTION but no tooth fired")


# --------------------------------------------------------------------------- #
# lens teeth
# --------------------------------------------------------------------------- #
def verify_lens_valid(path: Path, schema) -> None:
    rec = load(path)
    errs = sorted(schema.iter_errors(rec), key=lambda e: str(e.path))
    if errs:
        fail(f"{path.name}: schema-invalid: {errs[0].message}")
    if rec["scope"] != "analogue_characterization_only":
        fail(f"{path.name}: scope not pinned to analogue_characterization_only")
    # no-overclaim guard must pass on a legitimate record
    reject_navier_stokes_overclaim(rec.get("interpretation"))

    p = rec["params"]
    cls = classify_flow((p["sigma"], p["rho"], p["beta"]))
    if cls.regime != rec["regime"]:
        fail(f"{path.name}: recomputed regime {cls.regime} != declared {rec['regime']}")
    # Lyapunov sign must agree with the memory-mesh taxonomy label
    if not lyapunov_sign_agrees(cls, rec["memory_regime"]):
        fail(f"{path.name}: Lyapunov sign disagrees with taxonomy {rec['memory_regime']}")
    ok(f"{path.name}: {cls.regime} (lambda={cls.lambda_max}, stable_fp={cls.stable_fixed_point}) "
       f"agrees with memory-regime '{rec['memory_regime']}'")


def reject_lens_invalid(path: Path, schema) -> None:
    rec = load(path)
    name = path.name
    errs = list(schema.iter_errors(rec))
    if errs:
        ok(f"{name}: REJECTED by schema ({errs[0].message[:60]})")
        return
    # no-overclaim guard
    try:
        reject_navier_stokes_overclaim(rec.get("interpretation"))
    except FlowRegimeError:
        ok(f"{name}: REJECTED -- Navier-Stokes existence/smoothness over-claim")
        return
    # sign-agreement tooth
    p = rec["params"]
    cls = classify_flow((p["sigma"], p["rho"], p["beta"]))
    if "memory_regime" in rec and not lyapunov_sign_agrees(cls, rec["memory_regime"]):
        ok(f"{name}: REJECTED -- Lyapunov sign vs taxonomy mismatch "
           f"({cls.regime} vs '{rec['memory_regime']}')")
        return
    fail(f"{name}: expected REJECTION but no tooth fired")


def main() -> int:
    tri_schema = Draft202012Validator(load(SCHEMA_TRINOMIAL))
    lens_schema = Draft202012Validator(load(SCHEMA_LENS))

    print("FRT-1 trinomial contract:")
    for path in sorted(EXAMPLES.glob("trinomial.*.valid.json")):
        verify_trinomial_valid(path, tri_schema)
    for path in sorted(EXAMPLES.glob("trinomial.*.invalid.json")):
        reject_trinomial_invalid(path, tri_schema)

    print("FRL-1 flow-regime lens contract:")
    for path in sorted(EXAMPLES.glob("lens.*.valid.json")):
        verify_lens_valid(path, lens_schema)
    for path in sorted(EXAMPLES.glob("lens.*.invalid.json")):
        reject_lens_invalid(path, lens_schema)

    print(f"\nOK: {_passes} flow-regime teeth passed (VERIFIES + REJECTS + COHERENCE).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
