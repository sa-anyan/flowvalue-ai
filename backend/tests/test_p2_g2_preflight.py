"""G2 preflight: synthetic cross-stage propagation and preservation contract.

This fixture checks existing stage invalidation, not numerical recomputation or
the complete G2 exit gate. No new freshness or receipt authority is introduced.
"""
import copy
import unittest

from backend.blocks.execution import MODE, _digest, fresh, input_fingerprint, refresh
from backend.blocks.registry import BLOCKS


def baseline():
    state = {
        "execution_mode": MODE, "source_sha256": "workbook:unchanged",
        "filename": "synthetic.xlsx", "description": "Synthetic plant",
        "plan": {
            "equipment": [
                {"equipment_key": "physical:1", "equipment_tag": "T-104", "size": 10},
                {"equipment_key": "physical:2", "equipment_tag": "T-104", "size": 5},
            ],
            "capex": {"model_id": "fixture"},
            "operating_economics": {
                "sales": [{"id": "sale:1", "price": 1}],
                "financial": {"operating_years": 2},
            },
        },
        "stage_runs": {}, "stage_outputs": {},
        "results": {"stages": {}},
        "revenue_approval": {"fingerprint": "user-approved:1"},
    }
    for block in BLOCKS:
        payload = {"stage": block, "fixture": True}
        state["stage_outputs"][block] = copy.deepcopy(payload)
        state["stage_runs"][block] = {
            "status": "ready",
            "input_hash": input_fingerprint(state, block),
            "output_hash": _digest(payload),
        }
        state["results"]["stages"][block] = {
            "status": "calculated", "result": copy.deepcopy(payload)
        }
    return state


class G2PreflightTests(unittest.TestCase):
    def test_approved_equipment_change_propagates_staleness_without_overwrite(self):
        state = baseline()
        original = copy.deepcopy(state)
        state["plan"]["equipment"][0]["size"] = 20
        self.assertEqual(
            {key for key in BLOCKS if not fresh(state, key)},
            {"equipment", "capex", "opex", "financial"},
        )
        refresh(state)
        for key in ("equipment", "capex", "financial"):
            self.assertEqual(state["stage_runs"][key]["status"], "stale")
            self.assertTrue(state["results"]["stages"][key]["result_is_stale"])
        for key in ("engineering_data", "revenue"):
            self.assertEqual(state["stage_runs"][key]["status"], "ready")
        self.assertEqual(state["stage_outputs"], original["stage_outputs"])
        self.assertEqual(state["revenue_approval"], original["revenue_approval"])
        self.assertEqual(state["source_sha256"], original["source_sha256"])
        self.assertEqual(
            [e["equipment_key"] for e in state["plan"]["equipment"]],
            ["physical:1", "physical:2"],
        )
        self.assertEqual(
            [e["equipment_tag"] for e in state["plan"]["equipment"]],
            ["T-104", "T-104"],
        )

    def test_read_only_refresh_does_not_run_engines(self):
        state = baseline()
        state["plan"]["equipment"][0]["size"] = 20
        before = copy.deepcopy(state["stage_outputs"])
        refresh(state)
        self.assertEqual(state["stage_outputs"], before)
        self.assertEqual(state["plan"]["equipment"][1]["size"], 5)

    def test_revenue_change_does_not_silently_overwrite_equipment(self):
        state = baseline()
        original_equipment = copy.deepcopy(state["plan"]["equipment"])
        state["plan"]["operating_economics"]["sales"][0]["price"] = 2
        self.assertEqual(
            {key for key in BLOCKS if not fresh(state, key)},
            {"revenue", "opex", "financial"},
        )
        refresh(state)
        self.assertEqual(state["plan"]["equipment"], original_equipment)


if __name__ == "__main__":
    unittest.main()
