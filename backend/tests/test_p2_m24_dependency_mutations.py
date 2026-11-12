"""P2 M2.4: portable controlled-mutation tests for existing stage freshness.

These tests exercise the legacy authority; they do not activate B09 receipts
or trigger calculations. A ready receipt here is synthetic test evidence.
"""

import copy
import unittest

from backend.blocks.execution import MODE, _digest, fresh, input_fingerprint, refresh
from backend.blocks.registry import BLOCKS


def ready_state():
    state = {
        "execution_mode": MODE,
        "source_sha256": "synthetic-source",
        "filename": "fixture.xlsx",
        "description": "Synthetic process",
        "plan": {
            "equipment": [{"equipment_key": "asset:1", "size": 10}],
            "capex": {"factor": 2},
            "operating_economics": {
                "sales": [{"id": "sale:1", "price": 4}],
                "materials": [{"id": "cost:1", "price": 3}],
                "financial": {"operating_years": 2},
            },
        },
        "stage_runs": {},
        "stage_outputs": {},
        "results": {"stages": {}},
    }
    for block in BLOCKS:
        payload = {"synthetic": block}
        state["stage_outputs"][block] = copy.deepcopy(payload)
        state["stage_runs"][block] = {
            "status": "ready",
            "input_hash": input_fingerprint(state, block),
            "output_hash": _digest(payload),
        }
        state["results"]["stages"][block] = {
            "status": "calculated", "result": {"synthetic": block}
        }
    return state


class DependencyMutationTests(unittest.TestCase):
    def test_equipment_edit_invalidates_equipment_capex_and_finance_only(self):
        state = ready_state()
        state["plan"]["equipment"][0]["size"] = 20
        self.assertEqual(
            {block for block in BLOCKS if not fresh(state, block)},
            {"equipment", "capex", "financial"},
        )
        previous = copy.deepcopy(state["stage_outputs"])
        refresh(state)
        self.assertEqual(state["stage_outputs"], previous)
        self.assertEqual(state["stage_runs"]["equipment"]["status"], "stale")
        self.assertEqual(state["stage_runs"]["capex"]["status"], "stale")
        self.assertEqual(state["stage_runs"]["financial"]["status"], "stale")
        self.assertEqual(state["stage_runs"]["revenue"]["status"], "ready")

    def test_revenue_edit_invalidates_revenue_opex_and_finance(self):
        state = ready_state()
        state["plan"]["operating_economics"]["sales"][0]["price"] = 5
        self.assertEqual(
            {block for block in BLOCKS if not fresh(state, block)},
            {"revenue", "opex", "financial"},
        )

    def test_source_edit_invalidates_all_descendants(self):
        state = ready_state()
        state["source_sha256"] = "changed-source"
        self.assertEqual(
            {block for block in BLOCKS if not fresh(state, block)},
            set(BLOCKS),
        )

    def test_unrelated_approval_is_not_overwritten_by_refresh(self):
        state = ready_state()
        state["revenue_approval"] = {
            "fingerprint": "approved:1", "actor": "user", "decision": "approved"
        }
        state["plan"]["equipment"][0]["size"] = 20
        before = copy.deepcopy(state["revenue_approval"])
        refresh(state)
        self.assertEqual(state["revenue_approval"], before)

    def test_missing_optional_cost_base_is_not_silently_zero(self):
        state = ready_state()
        state["stage_outputs"].pop("revenue")
        self.assertFalse(fresh(state, "revenue"))
        self.assertFalse(fresh(state, "opex"))
        self.assertFalse(fresh(state, "financial"))
        self.assertNotEqual(
            state["stage_runs"]["opex"]["input_hash"],
            input_fingerprint(state, "opex"),
        )


if __name__ == "__main__":
    unittest.main()
