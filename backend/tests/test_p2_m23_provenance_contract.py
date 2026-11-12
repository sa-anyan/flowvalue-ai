"""P2 M2.3 portable provenance-contract regressions.

These tests cover existing register behavior only. They do not assert that
inherited metadata constitutes independent engineering evidence or approval.
"""

import copy
import unittest

from backend.orchestration.register import mark_ai, register


class ProvenanceContractTests(unittest.TestCase):
    def test_nested_value_keeps_own_source_unit_and_status(self):
        plan = {"equipment": [{"duty": {
            "value": 125, "unit": "kW", "source": "MEB!D14",
            "rationale": "Observed workbook cell", "status": "source_supported",
        }}]}
        metadata = {"equipment": {
            "origin": "workbook", "units": "kg/h",
            "rationale": "Section-level context only",
            "evidence_ids": ["cell:D14"], "status": "unresolved",
        }}
        rows = register(plan, metadata)
        value = next(row for row in rows if row["path"] == "equipment.0.duty.value")
        self.assertEqual(value["value"], 125)
        self.assertEqual(value["unit"], "kW")
        self.assertEqual(value["source"], "MEB!D14")
        self.assertEqual(value["status"], "source_supported")
        self.assertEqual(value["evidence_ids"], ["cell:D14"])

    def test_missing_and_explicit_zero_are_distinct(self):
        rows = register({"revenue": {"price": None, "fraction": 0}}, {})
        by_path = {row["path"]: row for row in rows}
        self.assertIn("revenue.price", by_path)
        self.assertIsNone(by_path["revenue.price"]["value"])
        self.assertEqual(by_path["revenue.fraction"]["value"], 0)
        self.assertEqual(by_path["revenue.price"]["status"], "unresolved")

    def test_registration_does_not_modify_inputs(self):
        plan = {"streams": [{"flow": {"value": None, "unit": "kg/h"}}]}
        metadata = {"streams": {"evidence_ids": ["source:1"]}}
        original_plan, original_metadata = copy.deepcopy(plan), copy.deepcopy(metadata)
        register(plan, metadata)
        self.assertEqual(plan, original_plan)
        self.assertEqual(metadata, original_metadata)

    def test_ai_cannot_self_approve_source_or_review(self):
        proposal = {"flow": {
            "value": 12, "unit": "kg/h", "status": "source_supported",
            "source": "unsupported reference", "reviewed": True,
        }}
        original = copy.deepcopy(proposal)
        result = mark_ai(proposal, evidence_ids=["cell:A1"])
        self.assertEqual(result["flow"]["status"], "llm_estimate")
        self.assertFalse(result["flow"]["reviewed"])
        self.assertEqual(result["flow"]["source"], "unsupported reference")
        self.assertEqual(proposal, original)

    def test_source_supported_ai_value_requires_matching_evidence(self):
        proposal = {"flow": {
            "value": 12, "unit": "kg/h", "status": "source_supported",
            "source": "workbook!sheet!cell:A1", "reviewed": True,
        }}
        result = mark_ai(proposal, evidence_ids=["cell:A1"])
        self.assertEqual(result["flow"]["status"], "source_supported")
        self.assertFalse(result["flow"]["reviewed"])


if __name__ == "__main__":
    unittest.main()
