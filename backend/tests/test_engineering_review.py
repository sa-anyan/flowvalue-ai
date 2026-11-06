"""Engineering-led interpretation without fixed layout/name matching or AI arithmetic."""

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.ingestion.balance.models import BalanceReport
from backend.orchestration.register import mark_ai
from backend.orchestration.service import (
    _execute_connected_reference as execute,
    new_assessment,
)
from backend.orchestration.sizing import derive_size
from backend.orchestration.store import Store
from backend.orchestration.workbook_review import apply_review


def fixture():
    report = BalanceReport(
        filename="irregular.xlsx", sha256="a" * 64, sheets=[]
    ).model_dump(mode="json")
    return {
        "report": report,
        "source_cells_truncated": False,
        "source_cells": [
            {"sheet": "Process", "cell": "B2", "value": "Feed-A"},
            {"sheet": "Process", "cell": "G14", "value": 2},
            {"sheet": "Process", "cell": "A12", "value": "kg/s"},
            {"sheet": "Process", "cell": "B20", "value": "Neutralisation vessel P001"},
            {
                "sheet": "Process",
                "cell": "B21",
                "value": "Feed-A enters neutralisation vessel P001",
            },
            {"sheet": "Process", "cell": "A30", "value": "Water"},
            {"sheet": "Process", "cell": "G30", "value": 1.5},
        ],
    }


def response():
    def ref(cell):
        return {"sheet": "Process", "cell": cell}

    return {
        "summary": "Feed enters a neutralisation vessel, not a pump.",
        "scope_notes": [],
        "records": [
            {
                "key": "new-feed",
                "kind": "material",
                "identifier": "Feed-A",
                "name": "Aqueous feed",
                "classification": "Liquid material stream",
                "rationale": "Workbook layout interpreted across separated cells",
                "identity_sources": [ref("B2")],
                "observations": [
                    {
                        "property": "mass_flow",
                        "component": None,
                        "source": ref("G14"),
                        "unit": "kg/s",
                        "unit_sources": [ref("A12")],
                        "label_sources": [],
                        "interpretation": "Unit is in a separate region, not an adjacent header",
                        "replaces_evidence_ids": [],
                    },
                    {
                        "property": "component_mass_flow",
                        "component": "Water",
                        "source": ref("G30"),
                        "unit": "kg/s",
                        "unit_sources": [ref("A12")],
                        "label_sources": [ref("A30")],
                        "interpretation": "Water component quantity",
                        "replaces_evidence_ids": [],
                    },
                ],
            },
            {
                "key": "new-neutraliser",
                "kind": "equipment",
                "identifier": "P001",
                "name": "Neutralisation vessel",
                "classification": "Agitated neutralisation reactor",
                "rationale": "Service and process description identify vessel; tag prefix is not a pump classifier",
                "identity_sources": [ref("B20")],
                "observations": [],
            },
        ],
        "connections": [
            {
                "stream_key": "new-feed",
                "equipment_key": "new-neutraliser",
                "role": "destination",
                "sources": [ref("B21")],
                "rationale": "Workbook states the feed enters the vessel",
            }
        ],
        "products": [],
        "questions": ["What residence time is required?"],
    }


class EngineeringReviewTests(unittest.TestCase):
    def test_new_records_units_components_and_connections_outside_python_tables(self):
        parsed = fixture()
        original = copy.deepcopy(parsed)
        effective, decisions = apply_review(parsed, response())
        self.assertEqual(parsed, original)
        self.assertEqual(len(effective["entities"]), 2)
        feed = next(e for e in effective["entities"] if e["kind"] == "material")
        flow = next(v for v in feed["values"] if v["property"] == "mass_flow")
        self.assertEqual(flow["normalized_value"], 7200)
        self.assertEqual(flow["normalized_unit"], "kg/h")
        self.assertEqual(flow["cell"], "G14")
        self.assertEqual(
            next(v for v in feed["values"] if v["component"] == "Water")[
                "normalized_value"
            ],
            5400,
        )
        equipment = next(e for e in effective["entities"] if e["kind"] == "equipment")
        self.assertIn(feed["key"], equipment["stream_keys"])
        self.assertEqual(effective["connections"][0]["status"], "inferred")
        self.assertTrue(
            any(d["status"] == "source_checked_interpretation" for d in decisions)
        )

    def test_bad_source_does_not_discard_other_records(self):
        proposal = response()
        proposal["records"][0]["observations"][0]["source"]["cell"] = "Z999"
        report, decisions = apply_review(fixture(), proposal)
        self.assertEqual(len(report["entities"]), 2)
        self.assertTrue(any(d["status"] == "not_applied" for d in decisions))
        self.assertTrue(
            any(
                v.get("component") == "Water"
                for e in report["entities"]
                for v in e["values"]
            )
        )

    def test_source_correction_keeps_original_and_recalculates(self):
        parsed = fixture()
        effective, _ = apply_review(parsed, response())
        for key in ("review_summary", "scope_notes", "product_candidates"):
            effective.pop(key, None)
        parsed["report"] = effective
        feed = next(e for e in effective["entities"] if e["kind"] == "material")
        existing = next(v for v in feed["values"] if v["property"] == "mass_flow")
        existing["normalized_value"] = 999
        correction = response()
        correction["records"] = correction["records"][:1]
        correction["records"][0]["key"] = feed["key"]
        correction["records"][0]["observations"] = correction["records"][0][
            "observations"
        ][:1]
        correction["records"][0]["observations"][0]["replaces_evidence_ids"] = [
            existing["id"]
        ]
        correction["connections"] = []
        # A different interpretation source identity gives a fresh evidence id.
        correction["records"][0]["observations"][0]["unit"] = "kg/h"
        corrected, _ = apply_review(parsed, correction)
        values = next(e for e in corrected["entities"] if e["key"] == feed["key"])[
            "values"
        ]
        self.assertTrue(
            any(
                v["normalized_value"] == 999 and v["status"] == "unresolved"
                for v in values
            )
        )
        self.assertTrue(
            any(
                v["normalized_value"] == 2 and v["status"] == "inferred" for v in values
            )
        )
        self.assertEqual(existing["normalized_value"], 999)

    def test_interpretations_not_erased_and_source_claims_checked(self):
        value = mark_ai(
            {
                "boundary": "outlet",
                "specification_status": "confirmed",
                "reviewed": True,
                "flow": {
                    "value": "2",
                    "unit": "kg/s",
                    "source": "cell:1",
                    "status": "source_supported",
                },
            },
            evidence_ids={"cell:1"},
        )
        self.assertEqual(value["boundary"], "outlet")
        self.assertEqual(value["flow"]["status"], "source_supported")
        self.assertEqual(value["specification_status"], "provisional")
        self.assertFalse(value["reviewed"])

    def test_python_residence_sizing(self):
        report, _ = apply_review(fixture(), response())
        feed = next(e for e in report["entities"] if e["kind"] == "material")
        feed["values"].append(
            {
                "id": "vol",
                "property": "volume_flow",
                "component": None,
                "normalized_value": 4,
                "normalized_unit": "m3/h",
                "status": "inferred",
            }
        )
        size, unit, evidence = derive_size(
            {
                "sizing": {
                    "method": "volume_residence",
                    "stream_key": feed["key"],
                    "residence_time_h": "2",
                    "working_fraction": ".8",
                }
            },
            report,
        )
        self.assertEqual((size, unit), (10, "m3"))
        self.assertEqual(evidence["source_evidence"], "vol")
        with self.assertRaises(ValueError):
            derive_size(
                {"sizing": {"method": "code", "stream_key": feed["key"]}}, report
            )

    def test_full_lifecycle_uses_review_before_model_selection(self):
        class Provider:
            model = "controlled-test"

            def generate(self, **kwargs):
                if "python_records" in kwargs["context"]:
                    return response()
                self.report = kwargs["context"]["report"]
                if "equipment" in kwargs["schema"].get("properties", {}):
                    from backend.capex import get_factor_ranges

                    return {
                        "equipment": [],
                        "capex": {
                            "process_type": "mixed",
                            "delivery_basis": "delivered",
                            "rationale": "Controlled engineering scenario",
                            "selected_factors": {
                                f["id"]: float(f["minimum"])
                                for f in get_factor_ranges("garrett", "mixed")
                                if f["additive"]
                            },
                            "offsite_scope_confirmation": None,
                        },
                        "questions": [],
                    }
                return {"sections": [], "source_review": [], "questions": []}

        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "state.sqlite3")
            provider = Provider()
            state = new_assessment(
                store, b"", "irregular.xlsx", "Neutralise an aqueous feed"
            )
            state["parsed"] = fixture()
            store.put(state, state["revision"])
            result = execute(store, state["id"], use_ai=True, provider=provider)
            self.assertEqual(result["ai"]["status"], "connected")
            self.assertEqual(len(provider.report["entities"]), 2)
            self.assertEqual(len(result["effective_report"]["entities"]), 2)
            self.assertEqual(len(result["results"]["exclusions"]), 1)
            with patch(
                "backend.orchestration.service.review",
                side_effect=AssertionError("No paid review on Python rerun"),
            ):
                repeated = execute(store, state["id"])
            self.assertEqual(result["effective_report"], repeated["effective_report"])

    def test_engineering_revenue_scenario_keeps_default_review_policy(self):
        from dataclasses import replace

        from backend.revenue import calculate_revenue
        from backend.tests.test_revenue import fixture as revenue_fixture

        project = revenue_fixture()
        product = project.products[0]
        project = replace(
            project,
            products=(
                replace(
                    product,
                    reviewed=False,
                    specification_status="provisional",
                    allocation_fraction=replace(
                        product.allocation_fraction, status="llm_estimate"
                    ),
                    saleable_fraction=replace(
                        product.saleable_fraction, status="llm_estimate"
                    ),
                ),
            ),
        )
        self.assertEqual(calculate_revenue(project).status, "needs_review")
        scenario = calculate_revenue(project, engineering_scenario=True)
        self.assertEqual(scenario.status, "calculated_preliminary")
        self.assertTrue(
            any("Conditional AI engineering scenario" in w for w in scenario.warnings)
        )
        self.assertFalse(project.products[0].reviewed)


class EngineeringFeedbackTests(unittest.TestCase):
    def test_one_correction_uses_python_errors_and_does_not_stack_factors(self):
        import json

        from backend.orchestration.feedback import equipment_feedback

        parsed = fixture()
        report, _ = apply_review(parsed, response())
        key = next(e["key"] for e in report["entities"] if e["kind"] == "equipment")

        def proposal(corrected=False):
            options = {
                "allow_unverified": True,
                "unit_context": {
                    "input_gallon_basis": "US",
                    "target_gallon_basis": "US",
                },
                "factors": (
                    ["258.installation.open_tank"]
                    if corrected
                    else ["258.module.standard", "258.installation.open_tank"]
                ),
                "factor_basis_confirmation": "Explicit synthetic scope test",
            }
            rows = [
                {
                    "equipment_key": key,
                    "curve_id": "G258-008",
                    "size": 100,
                    "size_unit": "gal",
                    "costing_options": options,
                }
            ]
            return {
                "sections": [
                    {
                        "section": "equipment",
                        "value_json": json.dumps(rows),
                        "rationale": "Synthetic factor-selection test",
                        "units": "US gal",
                        "evidence_ids": [],
                        "uncertainty": "Test only",
                    },
                    {
                        "section": "capex",
                        "value_json": json.dumps(
                            {
                                "process_type": "mixed",
                                "factor_selection": "minimum",
                                "delivery_basis": "delivered",
                            }
                        ),
                        "rationale": "Synthetic CAPEX input",
                        "units": "historical USD",
                        "evidence_ids": [],
                        "uncertainty": "Test only",
                    },
                ],
                "questions": [],
                "source_review": [],
            }

        empty = {"sections": [], "questions": [], "source_review": []}
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "test.db")
            state = new_assessment(store, b"", "irregular.xlsx", "Neutralisation test")
            state["parsed"] = parsed
            store.put(state, state["revision"])
            review_result = (report, response(), [], {"model": "test", "cached": False})
            with (
                patch(
                    "backend.orchestration.service.review", return_value=review_result
                ),
                patch(
                    "backend.orchestration.service.propose",
                    side_effect=[(proposal(), {}), (proposal(True), {}), (empty, {})],
                ) as advisor,
            ):
                final = execute(store, state["id"], use_ai=True, provider=object())
            self.assertEqual(advisor.call_count, 3)
            self.assertIn(
                "engineering_errors", advisor.call_args_list[1].kwargs["stage_results"]
            )
            line = final["results"]["stages"]["equipment"]["result"]["equipment"][0]
            self.assertIsNotNone(line["equipment_cost"])
            self.assertIsNone(equipment_feedback(final["results"]))
            self.assertIn("equipment_correction", final["ai"]["advisors"])


def test_timeout_retries_only_source_region_once(tmp_path):
    from backend.orchestration.workbook_review import review

    class Uncached:
        def cached(self, context, compute):
            return compute(), False

    class Flaky:
        model = "test"
        calls = 0

        def generate(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise TimeoutError("Synthetic timeout")
            return response()

    provider = Flaky()
    result, _, _, meta = review(fixture(), "", Uncached(), provider)
    assert provider.calls == 2
    assert result["entities"]
    assert meta["batches"][0]["status"] == "reviewed"
