"""P2 M2.5 historical snapshot read-only compatibility regressions."""
import copy
import unittest

from backend.blocks.execution import MODE, view


class HistoricalReadTests(unittest.TestCase):
    def test_legacy_snapshot_is_history_not_fresh_calculation(self):
        saved = {
            "id": "legacy:1", "description": "Historical plant",
            "source_sha256": "old-workbook-digest",
            "plan": {"equipment": [{"equipment_key": "asset:1", "size": 12}]},
            "results": {"stages": {"equipment": {
                "status": "calculated", "result": {"total": "123"}
            }}},
            "locked": ["equipment"],
            "revenue_approval": {"fingerprint": "approved:original"},
        }
        before = copy.deepcopy(saved)
        opened = view(saved)
        self.assertEqual(saved, before)
        self.assertEqual(opened["execution_mode"], MODE)
        self.assertEqual(opened["source_sha256"], "old-workbook-digest")
        self.assertEqual(opened["plan"]["equipment"], before["plan"]["equipment"])
        self.assertEqual(opened["locked"], ["equipment"])
        self.assertEqual(opened["revenue_approval"], before["revenue_approval"])
        self.assertIn("Historical snapshot", opened["status"])
        self.assertIn("retained as history", opened["execution_notice"])
        self.assertEqual(opened["stage_runs"], {})
        self.assertEqual(opened["stage_outputs"], {})
        self.assertFalse(opened["engineering_data_approved"])

    def test_view_is_idempotent_on_saved_state_and_never_writes_it(self):
        saved = {"id": "old:2", "plan": {}, "results": {"stages": {
            "financial": {"result": {"npv": "9"}}
        }}}
        before = copy.deepcopy(saved)
        first = view(saved)
        second = view(saved)
        self.assertEqual(first["execution_mode"], MODE)
        self.assertEqual(second["execution_mode"], MODE)
        self.assertEqual(saved, before)
        self.assertEqual(first["results"]["stages"], second["results"]["stages"])


if __name__ == "__main__":
    unittest.main()
