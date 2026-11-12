"""P2 M2.1: portable canonical stream-contract regression tests."""
import copy
import unittest
from backend.orchestration.pipeline import source_streams

def material(key, values):
    return {"key": key, "kind": "material", "identifier": "S-001", "values": values}

def flow(value, unit="kg/h", status="resolved", cell="D4", ref="obs:1"):
    return {"id": ref, "property": "mass_flow", "normalized_value": value,
            "normalized_unit": unit, "status": status, "workbook": "fixture.xlsx",
            "sheet": "MEB", "cell": cell}

class StreamContractTests(unittest.TestCase):
    def test_identity_source_and_explicit_zero_preserved(self):
        report = {"extracted_on": "2026-01-01",
                  "entities": [material("material:1", [flow(0)])]}
        original = copy.deepcopy(report)
        result = source_streams(report)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "material:1")
        self.assertEqual(result[0]["flow"]["value"], "0")
        self.assertEqual(result[0]["flow"]["unit"], "kg/h")
        self.assertEqual(result[0]["flow"]["source"], "fixture.xlsx!MEB!D4")
        self.assertEqual(result[0]["source_references"], ["obs:1"])
        self.assertEqual(report, original)

    def test_missing_is_not_zero(self):
        self.assertEqual(source_streams({"entities": [
            material("material:1", [flow(None)])]}), [])

    def test_conflicting_values_not_silently_selected(self):
        self.assertEqual(source_streams({"entities": [
            material("material:1", [flow(10), flow(20, cell="D5", ref="obs:2")])]}), [])

    def test_unsupported_units_and_unresolved_values_excluded(self):
        result = source_streams({"entities": [
            material("material:1", [flow(10, unit="lb/h")]),
            material("material:2", [flow(10, status="unresolved")]),
            material("material:3", [flow(10)]),
        ]})
        self.assertEqual([x["id"] for x in result], ["material:3"])

if __name__ == "__main__":
    unittest.main()
