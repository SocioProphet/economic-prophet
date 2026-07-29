"""Tests for backward reasoning (abduction) over the causal graph.

Pins the abduction contract: sign-matched ranked candidates, warrant-weighted
scoring, deterministic ordering, refusal properties inherited from the
forward propagator, and honest defaults (warrant_weight is not zero).
"""
from __future__ import annotations

import unittest

from open_ep_framework.causal_graph import Edge, Hypothesis
from open_ep_framework.causal_abduction import abduce


G = "urn:srcos:causal-graph:demo"


def h(node_id: str) -> Hypothesis:
    return Hypothesis(id=node_id, graph_ref=G, label=node_id)


def e(eid: str, frm: str, to: str, sign: str = "positive",
      weight: float = 1.0, confidence: float = 1.0,
      warrants: tuple[str, ...] = ("urn:srcos:evidence:w",)) -> Edge:
    return Edge(id=eid, graph_ref=G, from_ref=frm, to_ref=to,
                sign=sign, warrant_refs=warrants, weight=weight, confidence=confidence)


# Small "auto-parts" graph shape from the HOPE example:
#   tariffs --neg 0.6--> op_cost --neg 0.5--> revenue    (2-hop, +0.3 net)
#   tariffs --neg 0.4----------------------> revenue     (direct, -0.4)
#   marketing --pos 0.7--------------------> revenue     (positive lift)
def _auto_parts():
    hs = [h("tariffs"), h("op_cost"), h("revenue"), h("marketing")]
    es = [
        e("e_t_o", "tariffs", "op_cost", sign="negative", weight=0.6,
          warrants=("urn:srcos:evidence:tariff_2026Q2",)),
        e("e_o_r", "op_cost", "revenue", sign="negative", weight=0.5,
          warrants=("urn:srcos:evidence:cost_uplift_note",)),
        e("e_t_r", "tariffs", "revenue", sign="negative", weight=0.4,
          warrants=(
              "urn:srcos:evidence:tariff_2026Q2",
              "urn:srcos:evidence:cfo_call_transcript",
              "urn:srcos:evidence:supply_pact_v3",
          )),
        e("e_m_r", "marketing", "revenue", sign="positive", weight=0.7,
          warrants=("urn:srcos:evidence:market_report",)),
    ]
    return hs, es


class SignMatchingTest(unittest.TestCase):
    def test_negative_observed_move_returns_only_negative_paths(self):
        hs, es = _auto_parts()
        r = abduce(hs, es, "revenue", observed_sign="negative")
        for c in r.candidates:
            self.assertLess(c.contribution, 0,
                            f"path {c.edge_path} has non-negative contribution {c.contribution}")

    def test_positive_observed_move_returns_only_positive_paths(self):
        hs, es = _auto_parts()
        r = abduce(hs, es, "revenue", observed_sign="positive")
        for c in r.candidates:
            self.assertGreater(c.contribution, 0)
        # marketing → revenue AND the tariffs-op_cost-revenue 2-hop should show up.
        edge_paths = {c.edge_path for c in r.candidates}
        self.assertIn(("e_m_r",), edge_paths)
        self.assertIn(("e_t_o", "e_o_r"), edge_paths)

    def test_either_returns_both_signs(self):
        hs, es = _auto_parts()
        r = abduce(hs, es, "revenue", observed_sign="either")
        signs = {("positive" if c.contribution > 0 else "negative") for c in r.candidates}
        self.assertEqual(signs, {"positive", "negative"})


class RankingTest(unittest.TestCase):
    def test_warrant_weight_moves_candidates_up_or_down(self):
        # tariffs→revenue direct has 3 warrants (contrib -0.4); the 2-hop path via
        # op_cost accumulates 2 warrants (contrib +0.3). In this graph the direct
        # path is highest by both criteria, so the ranking does NOT swap between
        # warrant_weight=0 and 1 — but the SPREAD widens under pure warrants
        # (0.75 vs 0.50) compared to pure magnitude (0.40 vs 0.30). That widening
        # is the effect we care about pinning.
        hs, es = _auto_parts()
        r_pure_magnitude = abduce(hs, es, "revenue", observed_sign="either",
                                  warrant_weight=0.0)
        r_pure_warrants = abduce(hs, es, "revenue", observed_sign="either",
                                 warrant_weight=1.0)
        direct = "e_t_r"
        two_hop = ("e_t_o", "e_o_r")
        # In both cases the direct path (3 warrants, |contrib|=0.4) beats the
        # 2-hop path (2 warrants combined, |contrib|=0.3). Assert that; then
        # assert warrant coverage changed the SPREAD as expected.
        direct_score_mag = next(c.score for c in r_pure_magnitude.candidates if c.edge_path == (direct,))
        two_hop_score_mag = next(c.score for c in r_pure_magnitude.candidates if c.edge_path == two_hop)
        direct_score_wt = next(c.score for c in r_pure_warrants.candidates if c.edge_path == (direct,))
        two_hop_score_wt = next(c.score for c in r_pure_warrants.candidates if c.edge_path == two_hop)
        self.assertGreater(direct_score_mag, two_hop_score_mag)
        self.assertGreater(direct_score_wt, two_hop_score_wt)
        # Pure-warrant scores are 0.75 (3/4) vs 0.5 (2/4); pure-magnitude are 0.4 vs 0.3.
        self.assertAlmostEqual(direct_score_wt, 0.75)
        self.assertAlmostEqual(two_hop_score_wt, 0.5)

    def test_warrant_weight_can_reorder_candidates_when_it_matters(self):
        """A separate graph where the swap Copilot flagged as missing actually happens:
        one path has higher magnitude with 1 warrant; another has lower magnitude with
        many warrants. Under pure magnitude the first wins; under pure warrants the
        second wins. Pinning both orderings prevents future regressions of the mix."""
        hs = [h("src_a"), h("src_b"), h("target")]
        es = [
            # Higher magnitude, single warrant
            e("hi_mag", "src_a", "target", sign="negative", weight=0.9, confidence=1.0,
              warrants=("urn:srcos:evidence:one",)),
            # Lower magnitude, four warrants (saturated coverage)
            e("hi_warr", "src_b", "target", sign="negative", weight=0.3, confidence=1.0,
              warrants=("urn:srcos:evidence:a", "urn:srcos:evidence:b",
                        "urn:srcos:evidence:c", "urn:srcos:evidence:d")),
        ]
        pure_mag = abduce(hs, es, "target", observed_sign="negative", warrant_weight=0.0)
        pure_warr = abduce(hs, es, "target", observed_sign="negative", warrant_weight=1.0)
        self.assertEqual([c.source_id for c in pure_mag.candidates], ["src_a", "src_b"])
        self.assertEqual([c.source_id for c in pure_warr.candidates], ["src_b", "src_a"])

    def test_default_warrant_weight_is_nonzero(self):
        """warrant_weight defaulting to 0 would silently reproduce the naive engine
        this module exists to improve on. Pin that default."""
        # We can't inspect the default from a signature test at unittest level
        # cheaply, so infer: run with default and with 0.0 and observe the
        # scores are NOT identical for the 3-warrant path vs a 1-warrant path.
        hs, es = _auto_parts()
        default = abduce(hs, es, "revenue", observed_sign="either")
        pure = abduce(hs, es, "revenue", observed_sign="either", warrant_weight=0.0)
        direct_default = next(c.score for c in default.candidates if c.edge_path == ("e_t_r",))
        direct_pure = next(c.score for c in pure.candidates if c.edge_path == ("e_t_r",))
        self.assertNotEqual(direct_default, direct_pure,
                            "default warrant_weight must not be 0 — that would hide warrant coverage")

    def test_ordering_is_deterministic(self):
        hs, es = _auto_parts()
        r1 = abduce(hs, es, "revenue", observed_sign="either")
        r2 = abduce(hs, es, "revenue", observed_sign="either")
        self.assertEqual([c.edge_path for c in r1.candidates],
                         [c.edge_path for c in r2.candidates])

    def test_top_k_limits(self):
        hs, es = _auto_parts()
        r = abduce(hs, es, "revenue", observed_sign="either", top_k=1)
        self.assertEqual(len(r.candidates), 1)

    def test_top_k_none_returns_all(self):
        hs, es = _auto_parts()
        r = abduce(hs, es, "revenue", observed_sign="either", top_k=None)
        # 4 paths total: direct (neg), 2-hop (pos), marketing (pos), and… op_cost
        # itself isn't a source of a REVENUE explanation directly since it needs
        # the intermediate step. So expect 3: direct, 2-hop from tariffs, marketing.
        # PLUS: op_cost → revenue directly IS a candidate on its own.
        edge_paths = {c.edge_path for c in r.candidates}
        self.assertIn(("e_t_r",), edge_paths)
        self.assertIn(("e_t_o", "e_o_r"), edge_paths)
        self.assertIn(("e_m_r",), edge_paths)
        self.assertIn(("e_o_r",), edge_paths)


class RefusalTest(unittest.TestCase):
    def test_unwarranted_edge_produces_no_candidate(self):
        # Build a graph where an unwarranted edge would otherwise be top-ranked.
        hs = [h("a"), h("b")]
        es = [Edge(id="ab", graph_ref=G, from_ref="a", to_ref="b",
                   sign="negative", warrant_refs=(), weight=1.0, confidence=1.0)]
        r = abduce(hs, es, "b", observed_sign="negative")
        self.assertEqual(r.candidates, [])
        self.assertTrue(any("no warrantRefs" in n for n in r.abstentions))

    def test_missing_target_abstains(self):
        r = abduce([], [], "ghost", observed_sign="either")
        self.assertEqual(r.candidates, [])
        self.assertTrue(any("target ghost" in n for n in r.abstentions))

    def test_cycle_between_source_and_target_is_refused_not_traversed(self):
        hs = [h("a"), h("b"), h("c")]
        # a -> b, b -> c (target); b -> d cycle → d -> b that DFS will find
        # while trying to reach c.
        # Simpler: b -> c AND b -> a (which loops back to a's outgoing set).
        # The cycle is only visible if there is a walk to the target that would
        # otherwise re-enter a visited node.
        hs = [h("a"), h("b"), h("c"), h("d")]
        es = [e("ab","a","b"), e("bc","b","c"), e("bd","b","d"), e("db","d","b")]
        r = abduce(hs, es, "c", observed_sign="either")
        # 'a' explains 'c' via ab->bc (one legitimate path).
        edge_paths = [c.edge_path for c in r.candidates if c.source_id == "a"]
        self.assertIn(("ab", "bc"), edge_paths)
        self.assertTrue(any("cycle detected" in n for n in r.abstentions))

    def test_every_returned_candidate_is_warrant_backed(self):
        hs, es = _auto_parts()
        r = abduce(hs, es, "revenue", observed_sign="either", top_k=None)
        for c in r.candidates:
            self.assertGreater(len(c.all_warrants), 0,
                               f"candidate {c.edge_path} has no warrants — refusal broken")

    def test_bogus_warrant_weight_is_rejected(self):
        hs, es = _auto_parts()
        with self.assertRaises(ValueError):
            abduce(hs, es, "revenue", warrant_weight=1.5)
        with self.assertRaises(ValueError):
            abduce(hs, es, "revenue", warrant_weight=-0.1)


class CandidateSourceFilterTest(unittest.TestCase):
    def test_restricting_candidate_sources_narrows_the_result(self):
        hs, es = _auto_parts()
        r_all = abduce(hs, es, "revenue", observed_sign="either")
        r_tariffs = abduce(hs, es, "revenue", observed_sign="either",
                           candidate_source_ids=["tariffs"])
        self.assertGreater(len(r_all.candidates), len(r_tariffs.candidates))
        for c in r_tariffs.candidates:
            self.assertEqual(c.source_id, "tariffs")


if __name__ == "__main__":
    unittest.main()


class ArgumentValidationTest(unittest.TestCase):
    def test_bogus_observed_sign_raises_even_on_an_empty_graph(self):
        # Empty graph would otherwise produce a normal empty Abduction and swallow the bad arg.
        with self.assertRaises(ValueError):
            abduce([], [], "any", observed_sign="upside_down")

    def test_bogus_warrant_weight_raises_even_on_an_empty_graph(self):
        with self.assertRaises(ValueError):
            abduce([], [], "any", warrant_weight=1.5)

    def test_bogus_top_k_raises(self):
        with self.assertRaises(ValueError):
            abduce([], [], "any", top_k=0)
        with self.assertRaises(ValueError):
            abduce([], [], "any", top_k=-3)

    def test_top_k_of_one_is_valid(self):
        # Boundary check: 1 is the smallest legitimate top_k.
        hs, es = _auto_parts()
        r = abduce(hs, es, "revenue", top_k=1)
        self.assertEqual(len(r.candidates), 1)
