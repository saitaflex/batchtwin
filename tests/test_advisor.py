"""
The recovery advisor: adaptive without a trained model.

The claim under test is that it genuinely improves as the plant accumulates
history, ranks a fix that held above one that did not, and never invents a
recommendation when there is no precedent.
"""
import tempfile
import time
import unittest
from pathlib import Path

from backend import store, anchor, products, advisor, analytics
from backend.odoo_adapter import MockOdoo

UNDERFILL = [200, 200, 200, 200, 200, 200, 172, 200, 200, 200]


class AdvisorTests(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        store.DB_PATH = tmp / "t.db"
        anchor.ANCHOR_PATH = tmp / "a.log"
        store.use_profile("pharma_gmp")
        store.init_db(reset=True)
        self.odoo = MockOdoo()
        self.of = self.odoo.search_read("mrp.production",
                                        [("order_kind", "=", "fabrication")], ["id"])[0]["id"]
        self.oc = self.odoo.search_read("mrp.production",
                                        [("order_kind", "=", "conditionnement")], ["id"])[0]["id"]
        with store._conn() as c:
            self.spec = products.active(c, "PF201")

    def _lot(self):
        return store.create_batch_for_product(self.odoo, self.spec["id"],
                                              self.of, self.oc, "system")

    def _all(self):
        return [store.get_batch(r["id"]) for r in store.list_batches()]

    def _fail(self, bid):
        store.add_qc_sample(bid, UNDERFILL, "cq.sana")
        return store.list_deviations(bid)[0]

    def _close(self, dev, cause, capa):
        store.close_deviation(dev["id"], "smq.leila", "smq", "Qualite#26",
                              "rework", cause, capa)

    def test_no_precedent_produces_no_recommendation(self):
        """With an empty history it must say so, not guess."""
        bid = self._lot()
        dev = self._fail(bid)
        out = advisor.recommend(dev, store.get_batch(bid), self._all())
        self.assertIsNone(out["recommendation"])
        self.assertEqual(out["confidence"], "none")
        self.assertEqual(out["cases"], [])

    def test_a_closed_deviation_becomes_a_citable_case(self):
        b1 = self._lot()
        self._close(self._fail(b1), "Buse usee", "Remplacement de la buse")
        b2 = self._lot()
        out = advisor.recommend(self._fail(b2), store.get_batch(b2), self._all())
        self.assertIsNotNone(out["recommendation"])
        r = out["recommendation"]
        self.assertEqual(r["capa"], "Remplacement de la buse")
        self.assertEqual(r["closed_by"], "smq.leila")
        self.assertTrue(r["from_lot"], "a recommendation must cite the lot it came from")

    def test_a_fix_that_came_back_ranks_below_one_that_held(self):
        """The outcome signal is what makes this adaptive rather than a lookup."""
        b1 = self._lot()
        self._close(self._fail(b1), "Reglage derive", "Reglage manuel en debut de poste")
        time.sleep(1.1)
        b2 = self._lot()                       # same problem returns -> fix #1 failed
        self._close(self._fail(b2), "Joint use", "Remplacement du joint + requalification")
        time.sleep(1.1)
        b3 = self._lot()
        out = advisor.recommend(self._fail(b3), store.get_batch(b3), self._all())
        self.assertEqual(out["recommendation"]["capa"],
                         "Remplacement du joint + requalification",
                         "the fix that held must be recommended")
        self.assertTrue(out["recommendation"]["held"])
        self.assertFalse(out["cases"][-1]["held"], "the failed fix is kept, ranked lower")

    def test_recurrence_is_counted(self):
        b1 = self._lot()
        self._close(self._fail(b1), "Cause A", "Action A")
        time.sleep(1.1)
        b2 = self._lot()
        self._close(self._fail(b2), "Cause B", "Action B")
        cases = {c["capa"]: c for c in advisor.build_case_base(self._all())}
        self.assertEqual(cases["Action A"]["recurred"], 1)
        self.assertFalse(cases["Action A"]["held"])

    def test_a_case_is_never_its_own_recurrence(self):
        b1 = self._lot()
        self._close(self._fail(b1), "Cause", "Action")
        case = advisor.build_case_base(self._all())[0]
        self.assertEqual(case["recurred"], 0)
        self.assertTrue(case["held"])

    def test_only_closed_deviations_enter_the_case_base(self):
        """An open deviation has no outcome, so it teaches nothing yet."""
        bid = self._lot()
        self._fail(bid)
        self.assertEqual(advisor.build_case_base(self._all()), [])

    def test_a_different_product_does_not_dominate_the_match(self):
        b1 = self._lot()
        self._close(self._fail(b1), "Cause PF201", "Action PF201")
        with store._conn() as c:
            other = products.active(c, "PF310")
        b2 = store.create_batch_for_product(self.odoo, other["id"], self.of, self.oc, "system")
        out = advisor.recommend(self._fail(b2), store.get_batch(b2), self._all())
        # same failure kind and title, different product -> still offered, lower score
        self.assertTrue(out["cases"])
        self.assertLess(out["cases"][0]["similarity"], 1.0)

    def test_drift_advice_fires_before_anything_has_failed(self):
        """The evaluator's case: the chart is drifting, nothing has failed yet."""
        b1 = self._lot()
        self._close(self._fail(b1), "Buse usee", "Remplacement de la buse")
        b2 = self._lot()
        for i in range(10):                    # steady downward drift, still in spec
            store.add_qc_sample(b2, [200.0 - 0.7 * i] * 10, "cq.sana")
        batch = store.get_batch(b2)
        spc = analytics.spc(batch["qc"], batch["target_fill_g"],
                            batch["target_fill_g"] - batch["fill_tol_g"],
                            batch["target_fill_g"] + batch["fill_tol_g"])
        out = advisor.drift_advice(spc, batch, self._all())
        self.assertIsNotNone(out, "a forecast drift must produce advice")
        self.assertTrue(out["preemptive"])
        self.assertEqual(out["trigger"]["reason"], "spc_drift")
        self.assertIsNotNone(out["recommendation"])

    def test_no_drift_means_no_advice(self):
        bid = self._lot()
        store.add_qc_sample(bid, [200.0] * 10, "cq.sana")
        batch = store.get_batch(bid)
        spc = analytics.spc(batch["qc"], 200.0, 192.0, 208.0)
        self.assertIsNone(advisor.drift_advice(spc, batch, self._all()))

    def test_learning_stats_report_effectiveness_honestly(self):
        stats = advisor.learning_stats(self._all())
        self.assertEqual(stats["cases"], 0)
        self.assertIsNone(stats["effectiveness_pct"], "no cases means no percentage")
        self.assertFalse(stats["ready"])

        b1 = self._lot()
        self._close(self._fail(b1), "Cause", "Action")
        time.sleep(1.1)
        b2 = self._lot()
        self._close(self._fail(b2), "Cause 2", "Action 2")
        stats = advisor.learning_stats(self._all())
        self.assertEqual(stats["cases"], 2)
        self.assertEqual(stats["fixes_that_held"], 1)
        self.assertEqual(stats["effectiveness_pct"], 50)
        self.assertTrue(stats["ready"])


if __name__ == "__main__":
    unittest.main()
