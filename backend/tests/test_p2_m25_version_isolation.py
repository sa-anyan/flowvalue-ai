"""P2 M2.5: portable saved-version isolation tests for existing SQLite store.

No B09 receipt writes, live freshness changes or cloud-storage assumptions.
"""
import copy
import tempfile
import unittest
from pathlib import Path

from backend.orchestration.store import Store


class VersionIsolationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(Path(self.folder.name) / "versions.sqlite3")

    def test_named_version_reopens_as_independent_fork(self):
        original = {
            "plan": {"equipment": [{"equipment_key": "asset:1", "size": 10}]},
            "results": {"stages": {"equipment": {"result": {"total": "100"}}}},
            "running": False,
        }
        baseline = self.store.create(copy.deepcopy(original), b"synthetic workbook")
        version_id = self.store.version(baseline["id"], "Baseline")
        changed = copy.deepcopy(baseline)
        changed["plan"]["equipment"][0]["size"] = 20
        self.store.put(changed, baseline["revision"])

        reopened = self.store.load(version_id)
        self.assertNotEqual(reopened["id"], baseline["id"])
        self.assertEqual(reopened["parent_version"], version_id)
        self.assertEqual(reopened["plan"]["equipment"][0]["size"], 10)
        self.assertEqual(reopened["results"]["stages"]["equipment"]["result"]["total"], "100")
        self.assertEqual(self.store.workbook(reopened["id"]), b"synthetic workbook")
        self.assertEqual(self.store.get(baseline["id"])["plan"]["equipment"][0]["size"], 20)

    def test_reopening_one_fork_does_not_mutate_other_forks(self):
        state = self.store.create({"plan": {"x": 1}, "running": False}, b"source")
        version_id = self.store.version(state["id"], "Frozen")
        first = self.store.load(version_id)
        second = self.store.load(version_id)
        changed = copy.deepcopy(first)
        changed["plan"]["x"] = 99
        self.store.put(changed, first["revision"])
        self.assertEqual(self.store.get(second["id"])["plan"]["x"], 1)
        self.assertEqual(self.store.get(state["id"])["plan"]["x"], 1)

    def test_running_assessment_cannot_be_versioned(self):
        state = self.store.create({"plan": {}, "running": True}, b"source")
        with self.assertRaises(ValueError):
            self.store.version(state["id"], "While running")
        self.assertEqual(self.store.versions(state["id"]), [])

    def test_optimistic_revision_conflict_preserves_original(self):
        state = self.store.create({"plan": {"x": 1}, "running": False}, b"source")
        changed = copy.deepcopy(state)
        changed["plan"]["x"] = 2
        self.store.put(changed, state["revision"])
        with self.assertRaises(ValueError):
            self.store.put(state, state["revision"])
        self.assertEqual(self.store.get(state["id"])["plan"]["x"], 2)


if __name__ == "__main__":
    unittest.main()
