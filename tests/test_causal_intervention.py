"""Teeth for interventional + counterfactual reasoning (rungs 2 and 3).

The science this must get right, both ways:
  * `do(X)` severs arrows INTO X (graph surgery), not arrows out of it.
  * a confounder Z (X←Z→Y) opens a back-door path; {Z} identifies the effect, ∅ does
    not, and a descendant of X never does.
  * a collider is the opposite: a collider back-door path is BLOCKED by default and
    OPENED by conditioning on the collider (or its descendant).
  * the counterfactual is abduction → action → prediction and reports the contrast.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from open_ep_framework.causal_graph import Edge, Hypothesis  # noqa: E402
from open_ep_framework.causal_intervention import (  # noqa: E402
    backdoor_paths,
    counterfactual,
    intervene,
    interventional_effect,
    satisfies_backdoor,
)

G = "graph:test"


def h(i: str) -> Hypothesis:
    return Hypothesis(id=i, graph_ref=G, label=i)


def e(i: str, a: str, b: str, sign: str = "positive", w: float = 1.0, c: float = 1.0) -> Edge:
    return Edge(id=i, graph_ref=G, from_ref=a, to_ref=b, sign=sign, warrant_refs=(f"warrant:{i}",), weight=w, confidence=c)


# --- confounder graph: Z -> X, Z -> Y, X -> Y ------------------------------- #
def _confounded():
    hyps = [h("X"), h("Y"), h("Z")]
    edges = [e("zx", "Z", "X"), e("zy", "Z", "Y"), e("xy", "X", "Y", w=0.5)]
    return hyps, edges


def test_do_severs_only_incoming_edges():
    _, edges = _confounded()
    mut = intervene(edges, {"X": 1.0})
    kept = {x.id for x in mut.edges}
    assert "zx" not in kept, "do(X) must cut Z→X"
    assert "xy" in kept and "zy" in kept, "do(X) must NOT cut X's outgoing or unrelated edges"
    assert any("zx" in s for s in mut.severed)


def test_backdoor_path_found_for_confounder():
    hyps, edges = _confounded()
    paths = backdoor_paths(hyps, edges, "X", "Y")
    assert len(paths) == 1
    assert paths[0].nodes == ("X", "Z", "Y")  # X ← Z → Y


def test_backdoor_criterion_identifiable_with_Z_not_without():
    hyps, edges = _confounded()
    assert satisfies_backdoor(hyps, edges, "X", "Y", {"Z"}).identifiable is True
    empty = satisfies_backdoor(hyps, edges, "X", "Y", set())
    assert empty.identifiable is False
    assert empty.open_paths and empty.open_paths[0].nodes == ("X", "Z", "Y")


def test_backdoor_criterion_rejects_descendant_of_treatment():
    # add a descendant D of X; conditioning on it must be rejected outright.
    hyps, edges = _confounded()
    hyps = hyps + [h("D")]
    edges = edges + [e("xd", "X", "D")]
    v = satisfies_backdoor(hyps, edges, "X", "Y", {"D"})
    assert v.identifiable is False
    assert "descendant" in v.reason


def test_interventional_effect_is_direct_path_and_reports_backdoor():
    hyps, edges = _confounded()
    eff = interventional_effect(hyps, edges, "X", "Y", value=1.0)
    # Only the direct X→Y path survives surgery; its signed contribution is +0.5.
    assert abs(eff.total - 0.5) < 1e-9
    assert [p.hypothesis_path for p in eff.propagation.paths] == [("X", "Y")]
    # And the confounding path the surgery removed is reported for audit.
    assert eff.backdoor and eff.backdoor[0].nodes == ("X", "Z", "Y")


# --- collider graph: A -> X, A -> C, B -> C, B -> Y  ------------------------ #
# Back-door path X ← A → C ← B → Y has a COLLIDER at C.
def _collider():
    hyps = [h("X"), h("Y"), h("A"), h("B"), h("C")]
    edges = [e("ax", "A", "X"), e("ac", "A", "C"), e("bc", "B", "C"), e("by", "B", "Y")]
    return hyps, edges


def test_collider_path_blocked_by_default_opened_by_conditioning():
    hyps, edges = _collider()
    paths = backdoor_paths(hyps, edges, "X", "Y")
    assert any(p.nodes == ("X", "A", "C", "B", "Y") for p in paths), paths
    # ∅ blocks the collider path -> identifiable.
    assert satisfies_backdoor(hyps, edges, "X", "Y", set()).identifiable is True
    # conditioning on the collider C OPENS the path -> no longer identifiable.
    opened = satisfies_backdoor(hyps, edges, "X", "Y", {"C"})
    assert opened.identifiable is False
    assert opened.open_paths


def test_counterfactual_three_step_contrast():
    hyps, edges = _confounded()
    # Factually Y was observed at 0.9; had we set X=1 (do), the model predicts +0.5.
    cf = counterfactual(hyps, edges, "X", "Y", value=1.0, factual_observed_value=0.9,
                        factual_observed_sign="either")
    assert abs(cf.prediction.total - 0.5) < 1e-9
    assert cf.contrast is not None and abs(cf.contrast - (0.5 - 0.9)) < 1e-9
    # step 1 (abduction) ran and produced at least one explanation of the factual Y.
    assert cf.factual is not None and cf.factual.candidates


def test_fail_closed_on_undeclared_nodes():
    hyps, edges = _confounded()
    eff = interventional_effect(hyps, edges, "NOPE", "Y")
    assert eff.total == 0.0
    assert any("NOPE" in a for a in eff.propagation.abstentions)


def test_unwarranted_edge_cannot_contribute_under_do():
    # An edge with no warrants is inadmissible even in the mutilated graph.
    hyps = [h("X"), h("Y")]
    bad = Edge(id="xy", graph_ref=G, from_ref="X", to_ref="Y", sign="positive", warrant_refs=(), weight=1.0)
    eff = interventional_effect(hyps, [bad], "X", "Y")
    assert eff.total == 0.0
    assert any("unwarranted" in a or "warrantRefs" in a for a in eff.propagation.abstentions)
