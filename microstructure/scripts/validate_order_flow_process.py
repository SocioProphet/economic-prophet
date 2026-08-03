#!/usr/bin/env python3
"""Validate the OrderFlowProcess + TrendSignal microstructure contracts -- with
teeth in BOTH directions (a control that never fires is suspect).

Order flow is a MARKED POINT PROCESS in event time. The OrderFlowProcess record
binds the arrival-intensity family (Poisson / exponential-Hawkes / power-law
Hawkes / ACD) onto the estate memory-regime taxonomy, exposes the marks as an F
for the RAROC risk kernel and the LOB micro-signals (Kyle-lambda / OFI) as the
liquidity input for the vol-surface / FTP layer. The TrendSignal record reframes
technical analysis (Dow / Edwards-Magee / Elliott, in Fuller's Synergetics cycle
grammar) as LEARNED, receipted signals whose evidence is the order-flow mechanism.

Four tooth families run here:

  VERIFIES  Seeded generators are classified correctly by the honest, stdlib-only
            estimators: Poisson -> memoryless with branching n~0; exponential
            Hawkes(n=0.6) -> short_decaying/self-exciting with n<1; power-law
            Hawkes -> long_memory; ACD -> duration autocorrelation a Poisson fit
            misses; a Poisson-vs-Hawkes discrimination test FIRES on excitation;
            Kyle-lambda is recovered; power-law marks read heavy-tailed.

  REJECTS   Every committed *.invalid.json fixture is refused, each for its
            specific tooth (branching n>=1 without override => UNSTABLE
            flash-crash guard; Poisson claimed while excited; gaussian marks
            while heavy-tailed; fill probability > 1; negative intensity; a
            trend with no order-flow-persistence evidence; support/resistance
            with no LOB-depth evidence; a wave_count with no measured
            self-similarity or a non-fundamental closure; a mismatched Fibonacci
            ratio; a tampered receipt). Dropping any required field is refused.

  COHERENCE Each valid record's risk_distribution_F is shaped for the RAROC
            risk(F, kernel, reference, horizon) interface and its LOB signals for
            market_instruments.liquidity_premium(volume, regime_hurst, base_bps).

  RECEIPT   Every valid record carries a SHA-256 hash-chain link that recomputes
            to its stored contentHash.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_OFP = ROOT / "schemas" / "order-flow-process.schema.json"
SCHEMA_TS = ROOT / "schemas" / "trend-signal.schema.json"
EXAMPLE_DIR = ROOT / "examples" / "order-flow"

sys.path.insert(0, str(ROOT / "scripts"))
import order_flow_estimators as est  # noqa: E402

CLOSURE_COUNT = {"tetra_3": 3, "octa_4": 4, "icosa_5": 5}
SELFSIM_WIDTH_MIN = 0.05
REGIME_KERNEL = {"memoryless": "delta", "short_decaying": "exponential", "long_memory": "power_law"}


def load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


# --------------------------------------------------------------------------- #
# Cross-field invariants the JSON Schema cannot express, per record type.
# Returns a list of (tooth, message) violations.
# --------------------------------------------------------------------------- #
def invariants_ofp(rec: dict):
    out = []
    arr = rec.get("arrival", {})
    n = arr.get("branching_ratio_n")
    regime = rec.get("regime")
    kern = rec.get("autocorr_kernel")

    # T1 UNSTABLE branching (flash-crash guard): n>=1 requires explicit override + stable False.
    if isinstance(n, (int, float)) and n >= 1.0:
        if not (arr.get("unstable_override") is True and arr.get("stable") is False):
            out.append(("INV-unstable-branching",
                        f"branching_ratio_n={n} >= 1 (non-stationary) without explicit unstable_override + stable=false"))

    # T2 Poisson claimed while excited: a poisson family / memoryless regime cannot show excitation.
    idc = arr.get("index_of_dispersion")
    if (arr.get("family") == "poisson" or regime == "memoryless"):
        if arr.get("poisson_vs_hawkes") == "hawkes" or (isinstance(idc, (int, float)) and idc >= est.IDC_EXCITE):
            out.append(("INV-poisson-misfit",
                        f"Poisson/memoryless declared but excitation present (idc={idc}, verdict={arr.get('poisson_vs_hawkes')})"))

    # T3 marks tail misfit: gaussian declared while heavy-tailed feeds the wrong F.
    marks = rec.get("marks", {})
    if marks.get("distribution") == "gaussian" and marks.get("heavy_tailed") is True:
        out.append(("INV-marks-tail-misfit", "marks.distribution 'gaussian' but heavy_tailed=true (would feed the wrong F)"))
    F = rec.get("risk_distribution_F", {})
    if F.get("family") == "gaussian" and F.get("tail_class") in ("fat_tailed", "multifractal"):
        out.append(("INV-marks-tail-misfit", "risk_distribution_F gaussian family with a fat/multifractal tail_class"))

    # T4 regime/kernel coherence.
    if regime in REGIME_KERNEL and kern is not None and kern != REGIME_KERNEL[regime]:
        out.append(("INV-regime-kernel", f"regime {regime} incoherent with autocorr_kernel {kern}"))

    # T5 execution fill probability in [0,1].
    fp = rec.get("execution", {}).get("fill_probability")
    if isinstance(fp, (int, float)) and not (0.0 <= fp <= 1.0):
        out.append(("INV-fill-prob", f"execution.fill_probability={fp} outside [0,1]"))

    # T6 negative intensity / rate.
    for path_, val in (("arrival.base_intensity_mu", arr.get("base_intensity_mu")),
                       ("arrival.branching_ratio_n", n),
                       ("lob_signals.kyle_lambda", rec.get("lob_signals", {}).get("kyle_lambda"))):
        if isinstance(val, (int, float)) and val < 0:
            out.append(("INV-negative-intensity", f"{path_}={val} is negative"))

    out += receipt_violation(rec)
    return out


def invariants_ts(rec: dict):
    out = []
    st = rec.get("signal_type")
    ev = rec.get("evidence", {})
    learned = rec.get("provenance") == "learned"

    if st == "trend" and learned:
        ofp = ev.get("order_flow_persistence", {})
        H = ofp.get("signed_flow_hurst")
        nb = ofp.get("branching_ratio_n")
        has = ofp.get("present") is True and ((isinstance(H, (int, float)) and H > 0.5) or (isinstance(nb, (int, float)) and nb > 0))
        if not has:
            out.append(("INV-trend-no-flow-evidence",
                        "trend asserted with no order-flow-persistence evidence (H>0.5 or branching n>0)"))

    if st == "support_resistance":
        d = ev.get("lob_depth", {})
        depth_ok = d.get("present") is True and ((d.get("bid_depth") or 0) > 0 or (d.get("ask_depth") or 0) > 0)
        if not depth_ok:
            out.append(("INV-sr-no-depth", "support/resistance asserted with no LOB-depth evidence"))

    if st == "volume_confirmation":
        ai = ev.get("arrival_intensity", {})
        if ai.get("present") is not True:
            out.append(("INV-vol-no-intensity", "volume-confirmation asserted with no arrival-intensity evidence"))

    if st == "wave_count":
        ss = ev.get("self_similarity", {})
        w = ss.get("multifractal_spectrum_width")
        csh = ss.get("cross_scale_hurst")
        selfsim_ok = ss.get("present") is True and (
            (isinstance(w, (int, float)) and w >= SELFSIM_WIDTH_MIN) or (isinstance(csh, (int, float)) and csh > 0.5))
        if not selfsim_ok:
            out.append(("INV-wave-no-selfsimilarity",
                        "wave_count asserted with no measured self-similarity (multifractal-spectrum width / cross-scale Hurst)"))
        cc = rec.get("cycle_closure", {})
        closure = cc.get("fundamental_closure")
        count = cc.get("event_count")
        if closure not in CLOSURE_COUNT or count != CLOSURE_COUNT.get(closure):
            out.append(("INV-wave-nonfundamental-closure",
                        f"cycle_closure {closure!r}/event_count {count} is not a fundamental Synergetics closure (tetra_3/octa_4/icosa_5 with matching 3/4/5)"))

    fib = rec.get("fibonacci_claim")
    if isinstance(fib, dict):
        c, m, tol = fib.get("ratio_claimed"), fib.get("ratio_measured"), fib.get("tolerance")
        if all(isinstance(v, (int, float)) for v in (c, m, tol)) and abs(c - m) > tol:
            out.append(("INV-fibonacci-mismatch",
                        f"claimed Fibonacci ratio {c} does not match measured {m} within tolerance {tol}"))

    if rec.get("dow_phase") in ("accumulation", "distribution"):
        inv = ev.get("inventory_cycle", {})
        if inv.get("phase") is None:
            out.append(("INV-dow-no-inventory", f"dow_phase {rec.get('dow_phase')} without inventory-cycle evidence"))

    out += receipt_violation(rec)
    return out


def receipt_violation(rec: dict):
    receipt = rec.get("receipt")
    if isinstance(receipt, dict) and "contentHash" in receipt:
        if est.receipt_content_hash(rec) != receipt.get("contentHash"):
            return [("INV-receipt-hash", "receipt.contentHash does not match recomputed SHA-256 (tampered)")]
    return []


def schema_for(rec: dict):
    rt = rec.get("recordType")
    if rt == "OrderFlowProcess":
        return OFP_VALIDATOR, invariants_ofp
    if rt == "TrendSignal":
        return TS_VALIDATOR, invariants_ts
    return None, None


def schema_errors(rec, validator):
    return sorted(validator.iter_errors(rec), key=lambda e: list(e.path))


def rejection_reasons(rec):
    validator, inv = schema_for(rec)
    if validator is None:
        return [f"unknown recordType: {rec.get('recordType')!r}"]
    reasons = [f"schema:{'.'.join(str(p) for p in e.path) or '<root>'}:{e.message}" for e in schema_errors(rec, validator)]
    reasons += [f"{tooth}:{msg}" for tooth, msg in inv(rec)]
    return reasons


# --------------------------------------------------------------------------- #
# VERIFIES: seeded generators classify correctly (honest estimators)
# --------------------------------------------------------------------------- #
def run_verifies():
    checks = 0

    # Poisson -> memoryless, n~0, not excited (robust sweep).
    for seed in (7, 77):
        ev = est.sim_poisson(5.0, 600.0, seed)
        c = est.classify_arrival(ev)
        if c["regime"] != "memoryless" or c["autocorr_kernel"] != "delta":
            fail(f"VERIFIES poisson seed={seed}: got {c['regime']}/{c['autocorr_kernel']}, want memoryless/delta")
        if c["branching_ratio_n"] > 0.10:
            fail(f"VERIFIES poisson seed={seed}: branching n={c['branching_ratio_n']} not ~0")
        if c["poisson_vs_hawkes"] != "poisson":
            fail(f"VERIFIES poisson seed={seed}: discrimination said {c['poisson_vs_hawkes']}, want poisson")
    checks += 1

    # exponential Hawkes(n=0.6) -> short_decaying/exponential, excited, 0<n<1 (robust sweep).
    for seed in (11, 202, 404):
        ev = est.sim_hawkes_exp(1.0, 0.6, 1.5, 4000.0, seed)
        c = est.classify_arrival(ev)
        if not (0.0 < c["branching_ratio_n"] < 1.0):
            fail(f"VERIFIES hawkes-exp seed={seed}: branching n={c['branching_ratio_n']} not in (0,1)")
        if c["poisson_vs_hawkes"] != "hawkes":
            fail(f"VERIFIES hawkes-exp seed={seed}: Poisson fit NOT rejected (idc={c['index_of_dispersion']})")
        if c["regime"] != "short_decaying" or c["autocorr_kernel"] != "exponential":
            fail(f"VERIFIES hawkes-exp seed={seed}: got {c['regime']}/{c['autocorr_kernel']}, want short_decaying/exponential")
    checks += 1

    # power-law Hawkes -> long_memory/power_law, excited, 0<n<1 (robust sweep).
    for seed in (13, 213, 313):
        ev = est.sim_hawkes_powerlaw(1.0, 0.8, 0.5, 0.3, 900.0, seed)
        c = est.classify_arrival(ev)
        if not (0.0 < c["branching_ratio_n"] < 1.0):
            fail(f"VERIFIES hawkes-powerlaw seed={seed}: branching n={c['branching_ratio_n']} not in (0,1)")
        if c["poisson_vs_hawkes"] != "hawkes":
            fail(f"VERIFIES hawkes-powerlaw seed={seed}: Poisson fit NOT rejected")
        if c["regime"] != "long_memory" or c["autocorr_kernel"] != "power_law":
            fail(f"VERIFIES hawkes-powerlaw seed={seed}: got {c['regime']}/{c['autocorr_kernel']}, want long_memory/power_law")
    checks += 1

    # ACD shows duration autocorrelation a Poisson fit misses.
    acd = est.sim_acd(0.1, 0.3, 0.6, 800, 19)
    pois = est.sim_poisson(5.0, 600.0, 7)
    acd_ac = est.duration_autocorr(acd)
    pois_ac = est.duration_autocorr(pois)
    if not (acd_ac > est.DUR_AUTOCORR_SIGNIF and acd_ac > 4 * abs(pois_ac)):
        fail(f"VERIFIES acd: duration autocorr {acd_ac:.3f} not clearly above Poisson {pois_ac:.3f}")
    checks += 1

    # Poisson-vs-Hawkes discrimination FIRES on excitation but not on Poisson.
    if est.poisson_vs_hawkes(est.sim_hawkes_exp(1.0, 0.6, 1.5, 2000.0, 11))[0] != "hawkes":
        fail("VERIFIES discrimination: excitation NOT detected on a Hawkes stream")
    if est.poisson_vs_hawkes(pois)[0] != "poisson":
        fail("VERIFIES discrimination: false excitation on a Poisson stream")
    checks += 1

    # Kyle-lambda is recovered from seeded (signed_volume, price_change) with a known slope.
    sv, dp = est.sim_price_from_flow(0.25, 400, 29)
    kyle = est.kyle_lambda(sv, dp)
    if not (0.20 <= kyle <= 0.30):
        fail(f"VERIFIES kyle-lambda: recovered {kyle:.3f}, want ~0.25")
    checks += 1

    # power-law marks read heavy-tailed; gaussian marks do not.
    if not est.marks_are_heavy_tailed(est.sim_pareto_marks(500, 1.4, 1.0, 3)):
        fail("VERIFIES marks: power-law marks NOT flagged heavy-tailed")
    import random
    if est.marks_are_heavy_tailed([random.Random(1).gauss(0, 1) for _ in range(500)]):
        fail("VERIFIES marks: gaussian marks wrongly flagged heavy-tailed")
    checks += 1

    print(f"OK VERIFIES: {checks} seeded-generator tooth families classified correctly by the estimators")


# --------------------------------------------------------------------------- #
# COHERENCE: the risk-kernel F and the vol-surface/FTP liquidity signal are
# shaped for their downstream consumers (economic-prophet, by reference).
# --------------------------------------------------------------------------- #
def coherence_checks(rec: dict, name: str):
    F = rec["risk_distribution_F"]
    if "raroc_interface" not in F or "risk(" not in F["raroc_interface"]:
        fail(f"coherence {name}: risk_distribution_F missing a risk(F,...) interface hint")
    if F["family"] == "empirical":
        samples = F.get("params", {}).get("samples")
        if not isinstance(samples, list) or len(samples) < 1:
            fail(f"coherence {name}: empirical F has no LossDistribution samples for the risk kernel")
    lob = rec["lob_signals"]
    if "liquidity_premium" not in lob.get("consumes_interface", ""):
        fail(f"coherence {name}: lob_signals not shaped for market_instruments.liquidity_premium(...)")
    if lob["kyle_lambda"] < 0 or lob["effective_volume"] < 0:
        fail(f"coherence {name}: lob signal has a negative liquidity input")


def main() -> int:
    global OFP_VALIDATOR, TS_VALIDATOR
    ofp_schema = load(SCHEMA_OFP)
    ts_schema = load(SCHEMA_TS)
    Draft202012Validator.check_schema(ofp_schema)
    Draft202012Validator.check_schema(ts_schema)
    OFP_VALIDATOR = Draft202012Validator(ofp_schema)
    TS_VALIDATOR = Draft202012Validator(ts_schema)

    for sid in (ofp_schema.get("$id", ""), ts_schema.get("$id", "")):
        if not sid.startswith("https://schemas.socioprophet.org/economic-prophet/microstructure/"):
            fail(f"$id not rehomed to the microstructure namespace: {sid!r}")

    valid_files = sorted(EXAMPLE_DIR.glob("*.valid.json"))
    invalid_files = sorted(EXAMPLE_DIR.glob("*.invalid.json"))
    if not valid_files:
        fail("no *.valid.json fixtures found")
    if not invalid_files:
        fail("no *.invalid.json fixtures found")

    # --- valid fixtures: schema + invariants + receipt all clean; OFP also coherent ---
    for path in valid_files:
        rec = load(path)
        validator, inv = schema_for(rec)
        if validator is None:
            fail(f"valid fixture {path.name}: unknown recordType {rec.get('recordType')!r}")
        errs = schema_errors(rec, validator)
        if errs:
            lines = [f"valid fixture {path.name} failed SCHEMA:"]
            for e in errs:
                loc = ".".join(str(p) for p in e.path) or "<root>"
                lines.append(f"  - {loc}: {e.message}")
            fail("\n".join(lines))
        viol = inv(rec)
        if viol:
            fail(f"valid fixture {path.name} failed INVARIANTS: " + "; ".join(f"{t}:{m}" for t, m in viol))
        if rec.get("recordType") == "OrderFlowProcess":
            coherence_checks(rec, path.name)
    print(f"OK valid: {len(valid_files)} fixtures pass schema + invariants + receipt (+ OFP coherence)")

    # --- required-field rejection on a canonical valid of each record type ---
    for canonical_name, schema in (("hawkes-powerlaw.long-memory.valid.json", ofp_schema),
                                   ("wave-count.elliott-synergetics.valid.json", ts_schema)):
        canonical = load(EXAMPLE_DIR / canonical_name)
        validator, _ = schema_for(canonical)
        required = schema.get("required", [])
        for field in required:
            broken = copy.deepcopy(canonical)
            broken.pop(field, None)
            if validator.is_valid(broken):
                fail(f"dropping required field '{field}' from {canonical_name} was ACCEPTED but must be rejected")
        print(f"OK required-field rejection ({canonical_name}): {len(required)} required fields each refused when dropped")

    # --- invalid fixtures: each must be rejected, for its specific tooth ---
    EXPECTED = {
        "hawkes.branching-ge-1-no-override": "INV-unstable-branching",
        "poisson.claimed-while-excited": "INV-poisson-misfit",
        "marks.gaussian-while-heavy": "INV-marks-tail-misfit",
        "execution.fill-prob-gt-1": "fill_probability",       # schema maximum OR INV-fill-prob
        "arrival.negative-intensity": "base_intensity_mu",    # schema minimum OR INV-negative-intensity
        "receipt.tampered-hash": "INV-receipt-hash",
        "trend.no-flow-evidence": "INV-trend-no-flow-evidence",
        "support-resistance.no-lob-depth": "INV-sr-no-depth",
        "volume-confirmation.no-intensity": "INV-vol-no-intensity",
        "wave-count.no-self-similarity": "INV-wave-no-selfsimilarity",
        "wave-count.nonfundamental-closure": "INV-wave-nonfundamental-closure",
        "fibonacci.ratio-mismatch": "INV-fibonacci-mismatch",
    }
    for path in invalid_files:
        rec = load(path)
        reasons = rejection_reasons(rec)
        if not reasons:
            fail(f"invalid fixture {path.name} was ACCEPTED but must be rejected")
        stem = path.name.replace(".invalid.json", "")
        needle = EXPECTED.get(stem)
        if needle and not any(needle in r for r in reasons):
            fail(f"invalid fixture {path.name} rejected, but not for the expected tooth '{needle}'. Reasons: {reasons}")
    print(f"OK REJECTS: {len(invalid_files)} invalid fixtures each refused for its specific tooth")

    run_verifies()

    print(f"OK: OrderFlowProcess + TrendSignal contracts validated -- {len(valid_files)} valid, "
          f"{len(invalid_files)} invalid, VERIFIES + REJECTS + COHERENCE + receipt teeth all fired")
    return 0


OFP_VALIDATOR = None
TS_VALIDATOR = None

if __name__ == "__main__":
    raise SystemExit(main())
