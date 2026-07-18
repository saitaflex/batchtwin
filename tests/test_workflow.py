import unittest

from backend import store

STAGES = store.STAGES


def _stages(signed):
    """Stage rows with the named ones marked signed."""
    return [{"name": n, "status": "signed" if n in signed else "pending"} for n in STAGES]


class WorkflowSummaryTests(unittest.TestCase):
    """The summary must return translation KEYS, never prose: the same batch is
    read by French, English and Arabic speakers, and the server does not get to
    choose which."""

    def test_quality_review_is_triggered_for_failed_qc(self):
        summary = store.build_workflow_summary(
            {"state": "open"}, _stages({"fabrication"}), [], [{"verdict": "FAIL"}])
        self.assertEqual(summary["status"], "quality_review")
        self.assertEqual(summary["headline_key"], "wf_quality_review")
        note = summary["notes"][0]
        self.assertEqual(note["key"], "wf_note_quality_review")
        self.assertEqual(note["args"]["n"], 1)

    def test_release_status_is_derived_when_all_stages_are_signed(self):
        summary = store.build_workflow_summary(
            {"state": "open"}, _stages(set(STAGES)), [], [])
        self.assertEqual(summary["status"], "released")
        self.assertEqual(summary["headline_key"], "wf_released")
        self.assertEqual(summary["progress"], 100)
        self.assertEqual(summary["pending_stages"], [])

    def test_a_rejected_batch_is_reported_as_rejected(self):
        summary = store.build_workflow_summary({"state": "rejected"}, _stages(set()), [], [])
        self.assertEqual(summary["status"], "rejected")
        self.assertEqual(summary["headline_key"], "wf_rejected")

    def test_pending_stages_travel_as_keys_not_sentences(self):
        summary = store.build_workflow_summary(
            {"state": "open"}, _stages({"fabrication"}), [], [])
        nxt = next(n for n in summary["notes"] if n["key"] == "wf_note_next")
        self.assertIn("cond_primaire", nxt["stages"],
                      "raw stage keys travel; the client renders their labels")

    def test_no_prose_leaks_into_the_payload(self):
        summary = store.build_workflow_summary(
            {"state": "open"}, _stages({"fabrication"}), [{"stage": "fabrication"}],
            [{"verdict": "FAIL"}])
        self.assertRegex(summary["headline_key"], r"^wf_[a-z_]+$")
        for note in summary["notes"]:
            self.assertRegex(note["key"], r"^wf_note_[a-z_]+$")


if __name__ == "__main__":
    unittest.main()
