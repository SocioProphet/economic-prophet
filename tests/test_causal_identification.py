"""Tests for ECO-1 causal identification, the estimand registry, and the refusal
path (SP-ARCH-000 §4.5 / Ecosystem Simulation Substrate v2 §2).

Pins the load-bearing governance property: an unidentified estimand never returns
a point estimate — the solver is gated on identification (BMG-1 / no-invisible-
authority for inference).
"""
from __future__ import annotations

import unittest

from open_ep_framework.causal_graph import Edge, Hypothesis
from open_ep_framework.causal_identification import (
    NO_UNOBSERVED_CONFOUNDING,
    Estimand,
    EstimandRegistry,
    IdentificationOutcome,
    ModalClass,
    identify,
    run_scenario,
    scenario_from_document,
)

G = "urn:srcos:causal-graph:eco-demo"


def h(node_id: str) -> Hypothesis:
    return Hypothesis(id=node_id, graph_ref=G, label=node_id)


def e(eid: str, frm: str, to: str) -> Edge:
    return Edge(
        id=eid, graph_ref=G, from_ref=frm, to_ref=to,
        sign="positive", warrant_refs=("urn:srcos:evidence:w",),
    )


def est(treatment: str, outcome: str) -> Estimand:
    return Estimand(graph_ref=G, treatment=treatment, outcome=outcome)


class IdentificationTests(unittest.TestCase):
    def test_observed_confounder_is_identified_with_adjustment_set(self) -> None:
        # Z -> T, Z -> Y, T -> Y.  Backdoor T<-Z->Y closed by observed Z.
        hyps = [h("Z"), h("T"), h("Y")]
        edges = [e("zt", "Z", "T"), e("zy", "Z", "Y"), e("ty", "T", "Y")]
        res = identify(hyps, edges, est("T", "Y"))
        self.assertEqual(res.outcome, IdentificationOutcome.IDENTIFIED)
        self.assertEqual(res.adjustment_set, ("Z",))
        self.assertTrue(res.identified)

    def test_latent_confounder_is_not_identified_and_names_the_measurement(self) -> None:
        # U -> T, U -> Y, T -> Y, with U latent (unobserved).
        hyps = [h("U"), h("T"), h("Y")]
        edges = [e("ut", "U", "T"), e("uy", "U", "Y"), e("ty", "T", "Y")]
        res = identify(hyps, edges, est("T", "Y"), latents={"U"})
        self.assertEqual(res.outcome, IdentificationOutcome.NOT_IDENTIFIED)
        self.assertFalse(res.identified)
        self.assertEqual(res.required_measurements, ("U",))
        self.assertTrue(res.blocking_paths)

    def test_refusal_path_returns_no_point_estimate(self) -> None:
        # THE governance property: unidentified => solver does not run => no number.
        hyps = [h("U"), h("T"), h("Y")]
        edges = [e("ut", "U", "T"), e("uy", "U", "Y"), e("ty", "T", "Y")]
        scenario = run_scenario(hyps, edges, est("T", "Y"), latents={"U"})
        self.assertTrue(scenario.refused)
        self.assertIsNone(scenario.point_estimate)
        self.assertEqual(scenario.required_measurements, ("U",))

    def test_identified_under_assumption_runs_but_is_penalised(self) -> None:
        hyps = [h("U"), h("T"), h("Y")]
        edges = [e("ut", "U", "T"), e("uy", "U", "Y"), e("ty", "T", "Y")]
        res = identify(
            hyps, edges, est("T", "Y"),
            latents={"U"}, allow_assumptions={NO_UNOBSERVED_CONFOUNDING},
        )
        self.assertEqual(res.outcome, IdentificationOutcome.IDENTIFIED_UNDER_ASSUMPTION)
        self.assertEqual(res.assumptions, (NO_UNOBSERVED_CONFOUNDING,))
        self.assertGreater(res.epistemic_penalty, 0)

        scenario = run_scenario(
            hyps, edges, est("T", "Y"),
            latents={"U"}, allow_assumptions={NO_UNOBSERVED_CONFOUNDING},
        )
        self.assertFalse(scenario.refused)
        self.assertIsNotNone(scenario.point_estimate)

    def test_no_backdoor_mediator_is_identified_without_adjustment(self) -> None:
        # T -> M -> Y and T -> Y: no backdoor path, identified with empty set.
        hyps = [h("T"), h("M"), h("Y")]
        edges = [e("tm", "T", "M"), e("my", "M", "Y"), e("ty", "T", "Y")]
        res = identify(hyps, edges, est("T", "Y"))
        self.assertEqual(res.outcome, IdentificationOutcome.IDENTIFIED)
        self.assertEqual(res.adjustment_set, ())
        scenario = run_scenario(hyps, edges, est("T", "Y"))
        self.assertFalse(scenario.refused)
        self.assertIsNotNone(scenario.point_estimate)

    def test_collider_on_backdoor_path_is_auto_blocked(self) -> None:
        # A -> T, A -> M <- B, B -> Y, T -> Y.  Backdoor T<-A->M<-B->Y has an
        # unconditioned collider at M, so it is already blocked -> identified with
        # an empty set even though A, B, M are all latent.
        hyps = [h("A"), h("B"), h("M"), h("T"), h("Y")]
        edges = [
            e("at", "A", "T"), e("am", "A", "M"), e("bm", "B", "M"),
            e("by", "B", "Y"), e("ty", "T", "Y"),
        ]
        res = identify(hyps, edges, est("T", "Y"), latents={"A", "B", "M"})
        self.assertEqual(res.outcome, IdentificationOutcome.IDENTIFIED)
        self.assertEqual(res.adjustment_set, ())

    def test_modal_class_is_carried_independently_of_outcome(self) -> None:
        hyps = [h("U"), h("T"), h("Y")]
        edges = [e("ut", "U", "T"), e("uy", "U", "Y"), e("ty", "T", "Y")]
        refused = run_scenario(hyps, edges, est("T", "Y"), latents={"U"})
        self.assertEqual(refused.modal_class, ModalClass.INTERVENTIONAL)


class RouteTests(unittest.TestCase):
    """The exposed route (scenario_from_document / the `oepf causal-scenario` mode)."""

    def _doc(self, latents=None):
        return {
            "graphRef": G,
            "hypotheses": [
                {"id": "Z", "graphRef": G, "label": "Z"},
                {"id": "T", "graphRef": G, "label": "T"},
                {"id": "Y", "graphRef": G, "label": "Y"},
            ],
            "edges": [
                {"id": "zt", "graphRef": G, "fromRef": "Z", "toRef": "T",
                 "sign": "positive", "warrantRefs": ["w"]},
                {"id": "zy", "graphRef": G, "fromRef": "Z", "toRef": "Y",
                 "sign": "positive", "warrantRefs": ["w"]},
                {"id": "ty", "graphRef": G, "fromRef": "T", "toRef": "Y",
                 "sign": "negative", "warrantRefs": ["w"]},
            ],
            "estimand": {"treatment": "T", "outcome": "Y"},
            "latents": latents or [],
            "allowAssumptions": [],
        }

    def test_identified_document_returns_estimate_and_adjustment(self) -> None:
        out = scenario_from_document(self._doc())
        self.assertFalse(out["refused"])
        self.assertIsNotNone(out["pointEstimate"])
        self.assertEqual(out["identification"]["adjustmentSet"], ["Z"])
        self.assertEqual(out["modalClass"], "interventional")

    def test_latent_document_is_refused_with_no_estimate(self) -> None:
        out = scenario_from_document(self._doc(latents=["Z"]))
        self.assertTrue(out["refused"])
        self.assertIsNone(out["pointEstimate"])
        self.assertEqual(out["requiredMeasurements"], ["Z"])


class EstimandRegistryTests(unittest.TestCase):
    def test_deterministic_id_and_roundtrip(self) -> None:
        reg = EstimandRegistry()
        a = est("T", "Y")
        eid = reg.register(a)
        self.assertEqual(eid, a.id)
        self.assertEqual(reg.get(eid), a)
        # Idempotent: same estimand re-registers to the same id, len stays 1.
        self.assertEqual(reg.register(est("T", "Y")), eid)
        self.assertEqual(len(reg), 1)

    def test_distinct_estimands_get_distinct_ids(self) -> None:
        self.assertNotEqual(est("T", "Y").id, est("T", "Z").id)


if __name__ == "__main__":
    unittest.main()
