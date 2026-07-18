import unittest

from backend import store


class WorkflowSummaryTests(unittest.TestCase):
    def test_quality_review_is_triggered_for_failed_qc(self):
        batch = {"state": "open"}
        stages = [
            {"name": "fabrication", "status": "signed"},
            {"name": "conditionnement", "status": "signed"},
            {"name": "qualite", "status": "pending"},
            {"name": "liberation", "status": "pending"},
        ]
        summary = store.build_workflow_summary(batch, stages, [], [{"verdict": "FAIL"}])
        self.assertEqual(summary["status"], "quality_review")
        self.assertIn("Quality review required", summary["notifications"])

    def test_release_status_is_derived_when_all_stages_are_signed(self):
        batch = {"state": "open"}
        stages = [
            {"name": "fabrication", "status": "signed"},
            {"name": "conditionnement", "status": "signed"},
            {"name": "qualite", "status": "signed"},
            {"name": "liberation", "status": "signed"},
        ]
        summary = store.build_workflow_summary(batch, stages, [], [])
        self.assertEqual(summary["status"], "released")
        self.assertIn("Release complete", summary["notifications"])


if __name__ == "__main__":
    unittest.main()
