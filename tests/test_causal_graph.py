"""Tests for the causal-graph propagator.

Pins the invariants JSON Schema cannot express plus the propagation
semantics: signed contributions, warrant-required paths, cycle refusal,
per-path attribution, and abstention on any degenerate input.
"""
from __future__ import annotations

import unittest

from open_ep_framework.causal_graph import (
    Edge,
    Hypothesis,
    enforce_invariants,
    propagate,
)


G = "urn:srcos:causal-graph:demo"


def h(node_id: str, **kw) -> Hypothesis:
    return Hypothesis(id=node_id, graph_ref=G, label=node_id, **kw)


def e(eid: str, frm: str, to: str, sign: str = "positive",
      weight: float = 1.0, confidence: float = 1.0,
      warrants: tuple[str, ...] = ("urn:srcos:evidence:w",)) -> Edge:
    return Edge(id=eid, graph_ref=G, from_ref=frm, to_ref=to,
                sign=sign, warrant_refs=warrants, weight=weight, confidence=confidence)


# ── ingest + dict round-trip ───────────────────────────────────────────────

class IngestTest(unittest.TestCase):
    def test_hypothesis_from_dict_matches_the_shipped_contract(self):
        doc = {
            "id": "urn:srcos:causal-hypothesis:tariffs", "type": "CausalHypothesis",
            "specVersion": "0.1.0", "graphRef": G, "label": "Tariffs",
            "hypothesis": "Tariff rates change materially.",
            "topics": [], "claimStatus": "evidenced",
            "warrantRefs": ["urn:srcos:evidence:atom_1"],
            "kkoTypeRef": "kko:Tariff",
        }
        H = Hypothesis.from_dict(doc)
        self.assertEqual(H.id, doc["id"])
        self.assertEqual(H.claim_status, "evidenced")
        self.assertEqual(H.kko_type_ref, "kko:Tariff")
        self.assertEqual(H.warrant_refs, ("urn:srcos:evidence:atom_1",))

    def test_edge_from_dict_defaults_weight_and_confidence(self):
        doc = {"id": "urn:srcos:causal-edge:e", "type": "CausalEdge", "specVersion": "0.1.0",
               "graphRef": G, "fromRef": "urn:srcos:causal-hypothesis:a",
               "toRef": "urn:srcos:causal-hypothesis:b", "sign": "negative",
               "warrantRefs": ["urn:srcos:evidence:atom_1"]}
        E = Edge.from_dict(doc)
        self.assertEqual(E.sign, "negative")
        self.assertEqual(E.weight, 1.0)
        self.assertEqual(E.confidence, 1.0)


# ── invariant enforcement ──────────────────────────────────────────────────

class InvariantTest(unittest.TestCase):
    def test_clean_graph_has_no_errors(self):
        hs = [h("a"), h("b"), h("c")]
        es = [e("e1", "a", "b"), e("e2", "b", "c")]
        self.assertEqual(enforce_invariants(hs, es), [])

    def test_self_loop_is_reported(self):
        hs = [h("a")]
        es = [e("e_self", "a", "a")]
        errs = enforce_invariants(hs, es)
        self.assertTrue(any(k.kind == "self-loop" for k in errs))

    def test_missing_endpoint_is_reported(self):
        hs = [h("a")]
        es = [e("e1", "a", "b")]
        errs = enforce_invariants(hs, es)
        self.assertTrue(any(k.kind == "endpoint-missing" for k in errs))

    def test_weight_out_of_range_is_reported(self):
        hs = [h("a"), h("b")]
        es = [e("e1", "a", "b", weight=1.5)]
        errs = enforce_invariants(hs, es)
        self.assertTrue(any(k.kind == "weight-out-of-range" for k in errs))

    def test_multi_graph_hypothesis_set_is_reported(self):
        hs = [
            Hypothesis(id="x", graph_ref="urn:g1", label="X"),
            Hypothesis(id="y", graph_ref="urn:g2", label="Y"),
        ]
        errs = enforce_invariants(hs, [])
        self.assertTrue(any(k.kind == "multi-graph-hypothesis-set" for k in errs))


# ── propagation semantics ──────────────────────────────────────────────────

class PropagateTest(unittest.TestCase):
    def _hope_slice(self):
        # Tariffs --[negative, w=0.6]--> Operation cost --[negative, w=0.5]--> Revenue
        # Tariffs --[negative, w=0.4, direct]--> Revenue
        hs = [h("tariffs"), h("op_cost"), h("revenue")]
        es = [
            e("e_t_o", "tariffs", "op_cost", sign="negative", weight=0.6),
            e("e_o_r", "op_cost", "revenue", sign="negative", weight=0.5),
            e("e_t_r_direct", "tariffs", "revenue", sign="negative", weight=0.4),
        ]
        return hs, es

    def test_single_path_signed_propagation(self):
        hs = [h("a"), h("b")]
        es = [e("e", "a", "b", sign="negative", weight=0.5)]
        r = propagate(hs, es, "a", "b", source_value=1.0)
        self.assertEqual(len(r.paths), 1)
        self.assertAlmostEqual(r.paths[0].contribution, -0.5)
        self.assertEqual(r.paths[0].hypothesis_path, ("a", "b"))

    def test_two_negative_edges_compose_to_positive_via_target(self):
        # Standard HOPE-shape: two negative edges in series yield positive net.
        hs, es = self._hope_slice()
        # Isolate the two-hop path by removing the direct edge:
        r = propagate(hs, [x for x in es if x.id != "e_t_r_direct"], "tariffs", "revenue")
        self.assertEqual(len(r.paths), 1)
        self.assertAlmostEqual(r.paths[0].contribution, 0.3)   # (-1)*0.6*(-1)*0.5 = 0.3

    def test_two_paths_reported_separately_not_averaged(self):
        # Both a two-hop and a direct edge exist — attribution must show both.
        hs, es = self._hope_slice()
        r = propagate(hs, es, "tariffs", "revenue")
        self.assertEqual(len(r.paths), 2)
        contribs = sorted(p.contribution for p in r.paths)
        self.assertAlmostEqual(contribs[0], -0.4)   # direct negative
        self.assertAlmostEqual(contribs[1], 0.3)    # two-hop negative*negative
        self.assertAlmostEqual(r.total_signed_contribution, -0.1)

    def test_confidence_scales_the_contribution(self):
        hs = [h("a"), h("b")]
        es = [e("e", "a", "b", sign="positive", weight=1.0, confidence=0.5)]
        r = propagate(hs, es, "a", "b")
        self.assertAlmostEqual(r.paths[0].contribution, 0.5)
        self.assertAlmostEqual(r.paths[0].combined_confidence, 0.5)

    def test_unwarranted_edge_produces_no_path_and_is_recorded(self):
        hs = [h("a"), h("b")]
        es = [Edge(id="e", graph_ref=G, from_ref="a", to_ref="b",
                   sign="positive", warrant_refs=(), weight=1.0, confidence=1.0)]
        r = propagate(hs, es, "a", "b")
        self.assertEqual(r.paths, [])
        self.assertTrue(any("no warrantRefs" in a for a in r.abstentions))

    def test_multiple_paths_are_reported_not_averaged(self):
        # a -> c direct AND a -> b -> c should both surface.
        hs = [h("a"), h("b"), h("c")]
        es = [e("ab", "a", "b"), e("bc", "b", "c"), e("ac", "a", "c")]
        r = propagate(hs, es, "a", "c")
        edge_paths = sorted(p.edge_path for p in r.paths)
        self.assertEqual(edge_paths, [("ab", "bc"), ("ac",)])

    def test_cycle_is_refused_not_silently_traversed(self):
        # Cycle sits BETWEEN source and target so DFS actually encounters it.
        # a -> b, b -> c (target), and a -> b_again -> a (a genuine cycle
        # the DFS will attempt while trying to reach c).
        hs = [h("a"), h("b"), h("c"), h("d")]
        es = [
            e("ab", "a", "b"),
            e("bc", "b", "c"),
            e("bd", "b", "d"),
            e("db", "d", "b"),   # d->b closes a cycle b -> d -> b during traversal
        ]
        r = propagate(hs, es, "a", "c")
        # The legitimate a->b->c path is reported once.
        self.assertEqual([p.edge_path for p in r.paths], [("ab", "bc")])
        # The b->d->b cycle must show up in abstentions rather than be traversed.
        self.assertTrue(any("cycle detected" in a for a in r.abstentions),
                        f"cycle b->d->b must abstain; got abstentions={r.abstentions}")

    def test_missing_source_or_target_abstains(self):
        hs = [h("a")]
        r1 = propagate(hs, [], "ghost", "a")
        self.assertEqual(r1.paths, [])
        self.assertTrue(any("source" in a for a in r1.abstentions))
        r2 = propagate(hs, [], "a", "ghost")
        self.assertTrue(any("target" in a for a in r2.abstentions))

    def test_disconnected_target_abstains_with_reason(self):
        hs = [h("a"), h("b"), h("c")]
        es = [e("ab", "a", "b")]                   # no path from a to c
        r = propagate(hs, es, "a", "c")
        self.assertEqual(r.paths, [])
        self.assertTrue(any("no warrant-backed path" in a for a in r.abstentions))

    def test_all_reported_paths_are_warrant_backed(self):
        # Mix a warranted and an unwarranted edge on the same source; only the
        # warranted path should show up in `paths`.
        hs = [h("a"), h("b"), h("c")]
        es = [
            e("ab_ok", "a", "b", warrants=("urn:srcos:evidence:w1",)),
            e("bc_ok", "b", "c", warrants=("urn:srcos:evidence:w2",)),
            Edge(id="ac_bare", graph_ref=G, from_ref="a", to_ref="c",
                 sign="positive", warrant_refs=(), weight=1.0, confidence=1.0),
        ]
        r = propagate(hs, es, "a", "c")
        self.assertEqual(len(r.paths), 1)
        self.assertEqual(r.paths[0].edge_path, ("ab_ok", "bc_ok"))
        for p in r.paths:
            self.assertTrue(len(p.all_warrants) > 0)


if __name__ == "__main__":
    unittest.main()
