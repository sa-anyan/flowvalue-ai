"""Real workbook pipeline and explicit synthetic economics; never a reference-price claim."""

import copy
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from backend.opex.models import Basis
from backend.orchestration.advisor import propose
from backend.orchestration.codec import construct, plain
from backend.orchestration.ingest import parse
from backend.orchestration.pipeline import empty_plan, run, source_streams
from backend.orchestration.service import compare, edit, _execute_connected_reference as execute, new_assessment
from backend.orchestration.store import Store
from backend.tests.test_financial_modelling import fixture as financial_fixture
from backend.tests.test_opex import complete
from backend.tests.test_revenue import fixture as revenue_fixture

WORKBOOK = Path("/Users/user/Downloads/M&E Samples/Nottingham/Mass Balance Team 8.xlsm")
DESCRIPTION = "Wastewater is buffered, pH adjusted, biologically treated and settled. Sulfuric acid, sucrose and NaOH have storage tanks. P-001 is pH adjustment, not a confirmed pump."


def scenario(report):
    """All sizes, quality, sales, costs and policy below are synthetic USER assumptions."""
    plan = empty_plan()
    tank = next(
        e
        for e in report["entities"]
        if e["kind"] == "equipment" and e["identifier"] == "B-001"
    )
    plan["equipment"] = [
        {
            "equipment_key": tank["key"],
            "curve_id": "G303-144",
            "size": 10,
            "size_unit": "1000 US gal",
            "costing_options": {
                "allow_unverified": True,
                "unit_context": {"target_gallon_basis": "US"},
            },
            "rationale": "Synthetic buffer capacity and carbon-steel configuration for integration test only",
        }
    ]
    plan["capex"] = {
        "model_id": "garrett",
        "process_type": "mixed",
        "delivery_basis": "delivered",
        "factor_selection": "minimum",
    }
    basis = Basis("USD", "early 1987")
    revenue = plain(revenue_fixture())
    stream = source_streams(report)[-1]
    revenue.update(
        basis=plain(basis),
        streams=[
            {
                "id": stream["id"],
                "boundary": "outlet",
                "specifications": "Synthetic confirmed test grade; not an actual saleable product claim",
            }
        ],
    )
    product = revenue["products"][0]
    product.update(
        stream_id=stream["id"],
        specification_basis="Synthetic user-confirmed grade for integration test",
    )
    product["years"][0]["selling_price"]["unit"] = "USD/kg"
    # Two annual years required by the independent financial fixture.
    second = copy.deepcopy(revenue["schedule"][0])
    second["year"] = 2
    revenue["schedule"].append(second)
    second = copy.deepcopy(product["years"][0])
    second["year"] = 2
    product["years"].append(second)
    plan["revenue"] = revenue
    opex = complete()
    opex = replace(
        opex,
        basis=basis,
        assumptions=tuple(replace(a, basis=basis) for a in opex.assumptions),
        bases=(),
    )
    plan["opex"] = plain(opex)
    fixture = financial_fixture()
    assumptions = plain(fixture.assumptions)
    assumptions.update(
        start_date="1987-01-01",
        commissioning_date="1987-01-01",
        first_production_date="1987-01-01",
        currency="USD",
        financial_base_year=1987,
    )
    assumptions["working_capital"]["requirements"] = []

    def money(value):
        return {
            "amount": str(value),
            "currency": "USD",
            "price_year": 1987,
            "source": "Explicit synthetic user assumption",
        }

    assumptions["closure_cost"] = money(0)
    policy = plain(fixture.capital[0].depreciation)
    policy["residual_basis"] = money(0)
    plan["financial"] = {
        "project_id": "workbook-synthetic-economics",
        "assumptions": assumptions,
        "capital_spend": plain(fixture.capital[0].spend),
        "depreciation_policies": {
            k: policy for k in ("direct", "indirect", "offsite", "startup")
        },
        "disposal_proceeds": {
            k: money(0) for k in ("direct", "indirect", "offsite", "startup")
        },
        "year_map": {"1": 1, "2": 2},
        "price_year": 1987,
        "startup_treatment": "capitalized",
        "working_capital_funding_year": 0,
        "classifications": {a.id: "sga" for a in opex.assumptions},
    }
    return plan


class OrchestrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not WORKBOOK.exists():
            raise unittest.SkipTest(
                "Private workbook unavailable; run portable tests separately"
            )
        cls.parsed = parse(WORKBOOK.read_bytes(), WORKBOOK.name)
        cls.report = cls.parsed["report"]
        cls.plan = scenario(cls.report)

    def test_actual_workbook_streams_and_partial_exclusions(self):
        self.assertEqual(
            len([e for e in self.report["entities"] if e["kind"] == "equipment"]), 7
        )
        self.assertEqual(len(source_streams(self.report)), 14)
        result = run(self.report, DESCRIPTION, empty_plan())
        self.assertEqual(len(result["exclusions"]), 7)
        self.assertIsNone(
            result["stages"]["equipment"]["result"]["equipment_cost_total"]
        )
        self.assertEqual(result["stages"]["financial"]["status"], "unresolved")

    def test_complete_chain_with_explicit_synthetic_assumptions(self):
        result = run(self.report, DESCRIPTION, self.plan)
        for name, stage in result["stages"].items():
            self.assertNotEqual(stage["status"], "unresolved", (name, stage))
        self.assertIsNotNone(result["stages"]["financial"]["result"]["ledger"])
        self.assertEqual(len(result["exclusions"]), 6)
        self.assertEqual(result["scope"], "partial equipment scope")
        Path("outputs/orchestration-review").mkdir(parents=True, exist_ok=True)
        Path(
            "outputs/orchestration-review/actual-workbook-synthetic-economics.json"
        ).write_text(
            json.dumps(
                {
                    "notice": "Real workbook; ALL economic/design assumptions are synthetic, not validation of plant costs",
                    "description": DESCRIPTION,
                    "report": self.report,
                    "plan": self.plan,
                    "results": result,
                },
                indent=2,
            )
        )

    def test_numeric_text_from_browser_uses_canonical_converter(self):
        plan = copy.deepcopy(self.plan)
        plan["equipment"][0]["size"] = "10"
        numeric = run(self.report, DESCRIPTION, self.plan)
        textual = run(self.report, DESCRIPTION, plan)
        self.assertEqual(numeric["stages"]["capex"], textual["stages"]["capex"])
        self.assertIsNotNone(textual["stages"]["financial"]["result"]["ledger"])

    @patch("backend.revenue.authority.bind", side_effect=lambda state: state)
    def test_rerun_user_lock_persistence_and_comparison(self, _historical_authority):
        # Frozen connected-coordinator test predates Revenue Box binding. Current
        # approval policy is tested independently; no live route uses this reference.
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "models.db")
            state = new_assessment(
                store, WORKBOOK.read_bytes(), WORKBOOK.name, DESCRIPTION
            )
            state.update(
                parsed=self.parsed, plan=copy.deepcopy(self.plan), running=False
            )
            state = store.put(state, state["revision"])
            first = execute(store, state["id"])
            version = store.version(state["id"], "Baseline")
            changed = copy.deepcopy(first["plan"]["equipment"])
            changed[0]["size"] = 20
            edit(
                store,
                first["id"],
                first["revision"],
                "equipment",
                changed,
                "Explicit doubled synthetic capacity",
            )
            with patch(
                "backend.orchestration.service.propose",
                side_effect=AssertionError("No AI on rerun"),
            ):
                second = execute(store, first["id"])
            opened = store.load(version)
            self.assertEqual(opened["plan"]["equipment"][0]["size"], 10)
            self.assertEqual(second["plan"]["equipment"][0]["size"], 20)
            self.assertIn("equipment", second["locked"])
            comparison = compare(opened, second)
            self.assertEqual(comparison["changed_sections"], ["equipment"])
            self.assertNotEqual(
                opened["results"]["stages"]["capex"],
                second["results"]["stages"]["capex"],
            )
            self.assertNotEqual(
                opened["results"]["stages"]["opex"], second["results"]["stages"]["opex"]
            )
            self.assertNotEqual(
                opened["results"]["stages"]["financial"],
                second["results"]["stages"]["financial"],
            )
            with self.assertRaises(ValueError):
                edit(
                    store,
                    second["id"],
                    first["revision"],
                    "equipment",
                    changed,
                    "stale edit",
                )

    def test_unknown_source_and_model_do_not_invent_data(self):
        plan = copy.deepcopy(self.plan)
        plan["equipment"][0]["curve_id"] = "fabricated"
        result = run(self.report, DESCRIPTION, plan)
        self.assertEqual(len(result["exclusions"]), 7)
        plan = copy.deepcopy(self.plan)
        plan["revenue"]["streams"][0]["id"] = "made-up"
        self.assertEqual(
            run(self.report, DESCRIPTION, plan)["stages"]["revenue"]["status"],
            "unresolved",
        )
        plan = copy.deepcopy(self.plan)
        plan["revenue"]["streams"][0]["flow"] = {"value": 999, "unit": "kg/h"}
        self.assertEqual(
            run(self.report, DESCRIPTION, plan)["stages"]["revenue"]["status"],
            "unresolved",
        )

    def test_ai_cache_failure_and_manual_priority(self):
        class Provider:
            model = "test-only-provider"
            calls = 0

            def generate(self, **kwargs):
                self.calls += 1
                return {
                    "sections": [
                        {
                            "section": "equipment",
                            "value_json": "[]",
                            "rationale": "Test only",
                            "units": "mixed",
                            "evidence_ids": [],
                            "uncertainty": "unverified",
                        }
                    ],
                    "source_review": [],
                    "questions": ["Confirm capacity?"],
                }

        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "models.db")
            provider = Provider()
            for _ in range(2):
                propose(self.parsed, DESCRIPTION, empty_plan(), [], store, provider)
            self.assertEqual(provider.calls, 1)
            state = new_assessment(store, b"", WORKBOOK.name, DESCRIPTION)
            state.update(
                parsed=self.parsed,
                plan=copy.deepcopy(self.plan),
                running=False,
                locked=["equipment"],
            )
            store.put(state, state["revision"])
            result = execute(store, state["id"], use_ai=True, provider=provider)
            self.assertEqual(result["plan"]["equipment"], self.plan["equipment"])
            with patch(
                "backend.orchestration.service.propose",
                side_effect=RuntimeError("provider offline"),
            ):
                result = execute(store, state["id"], use_ai=True)
            self.assertFalse(result["running"])
            self.assertEqual(result["ai"]["status"], "review_unavailable")
            self.assertIsNotNone(result["results"])


class PortableTests(unittest.TestCase):
    def test_bad_files(self):
        for content, name in [
            (b"", "empty.xlsx"),
            (b"not excel", "bad.xlsm"),
            (b"bad", "bad.pdf"),
        ]:
            with self.assertRaises(ValueError):
                parse(content, name)

    def test_no_dynamic_types_and_invalid_json_numbers(self):
        from backend.financial_modelling.models import Money

        with self.assertRaises((ValueError, TypeError)):
            construct(
                Money,
                {
                    "amount": "NaN",
                    "currency": "USD",
                    "price_year": 2026,
                    "source": "test",
                },
            )
        with self.assertRaises((ValueError, TypeError)):
            construct(Money, {"type": "eval", "fields": {}})


if __name__ == "__main__":
    unittest.main()


class RecoveryTests(unittest.TestCase):
    def test_source_backed_recovery_and_conflict_preservation(self):
        from backend.orchestration.recovery import recover

        report = {
            "filename": "test.xlsx",
            "entities": [
                {
                    "key": "stream:1",
                    "kind": "material",
                    "table": "table:1",
                    "id_evidence": {"sheet": "MEB", "cell": "B1"},
                    "values": [
                        {
                            "property": "mass_flow",
                            "normalized_value": 10,
                            "normalized_unit": "kg/h",
                        }
                    ],
                }
            ],
            "tables": [
                {
                    "id": "table:1",
                    "sheet": "MEB",
                    "range": "A1:C4",
                    "orientation": "records_in_columns",
                }
            ],
        }
        parsed = {
            "report": report,
            "source_cells": [
                {"sheet": "MEB", "cell": "B2", "value": 20},
                {"sheet": "MEB", "cell": "A2", "value": "Mass flow (kg/h)"},
            ],
        }
        finding = {
            "sheet": "MEB",
            "cell": "B2",
            "recovery": {
                "entity_key": "stream:1",
                "property": "mass_flow",
                "original_unit": "kg/h",
                "header_cell": "A2",
            },
        }
        result, decisions = recover(parsed, [finding])
        self.assertEqual(result, report)
        self.assertEqual(decisions[0]["status"], "pending_review")
        self.assertIn("Conflicts", decisions[0]["reason"])
        finding["cell"] = "C2"
        result, decisions = recover(parsed, [finding])
        self.assertEqual(decisions[0]["status"], "pending_review")

    def test_ai_cannot_self_verify_physical_values_or_product_quality(self):
        from backend.orchestration.register import mark_ai

        value = mark_ai(
            {
                "reviewed": True,
                "specification_status": "confirmed",
                "flow": {"value": "10", "unit": "kg/h", "status": "source_supported"},
            }
        )
        self.assertFalse(value["reviewed"])
        self.assertEqual(value["specification_status"], "provisional")
        self.assertEqual(value["flow"]["status"], "llm_estimate")


class ApiTests(unittest.TestCase):
    def test_local_api_invalid_upload_and_origin_guards(self):
        from fastapi.testclient import TestClient

        from backend.api.app import app

        with TestClient(app) as client:
            self.assertEqual(client.get("/api/health").status_code, 200)
            self.assertEqual(
                client.post(
                    "/api/assessments", files={"file": ("bad.pdf", b"bad")}
                ).status_code,
                422,
            )
            self.assertEqual(
                client.post(
                    "/api/assessments",
                    files={"file": ("bad.xlsx", b"bad")},
                    headers={"origin": "https://untrusted.example"},
                ).status_code,
                403,
            )
            self.assertEqual(
                client.post(
                    "/api/assessments",
                    content=b"x",
                    headers={"content-length": str(22 * 1024**2)},
                ).status_code,
                413,
            )
            self.assertEqual(client.get("/api/assessments/missing").status_code, 404)


class SuccessfulRecoveryTests(unittest.TestCase):
    def test_missing_value_recovers_only_from_aligned_explicit_source(self):
        from backend.ingestion.balance.models import BalanceReport
        from backend.orchestration.recovery import recover

        report = BalanceReport.model_validate(
            {
                "filename": "test.xlsx",
                "sha256": "a" * 64,
                "sheets": [],
                "tables": [
                    {
                        "id": "t",
                        "sheet": "MEB",
                        "range": "A1:B3",
                        "orientation": "records_in_columns",
                        "kind": "material",
                    }
                ],
                "entities": [
                    {
                        "key": "s",
                        "identifier": "S1",
                        "kind": "material",
                        "table": "t",
                        "id_evidence": {
                            "id": "id1",
                            "workbook": "test.xlsx",
                            "sheet": "MEB",
                            "cell": "B1",
                            "property": "identifier",
                            "label": "Stream",
                            "original_value": "S1",
                        },
                    }
                ],
            }
        ).model_dump(mode="json")
        parsed = {
            "report": report,
            "source_cells": [
                {"sheet": "MEB", "cell": "A2", "value": "Mass flow (kg/h)"},
                {"sheet": "MEB", "cell": "B2", "value": 12},
            ],
        }
        finding = {
            "sheet": "MEB",
            "cell": "B2",
            "recovery": {
                "entity_key": "s",
                "property": "mass_flow",
                "original_unit": "kg/h",
                "header_cell": "A2",
            },
        }
        updated, decisions = recover(parsed, [finding])
        self.assertEqual(decisions[0]["status"], "source_checked_inferred")
        self.assertEqual(updated["entities"][0]["values"][0]["normalized_value"], 12)
        self.assertEqual(report["entities"][0]["values"], [])
        self.assertEqual(updated["entities"][0]["values"][0]["status"], "inferred")

class UploadVisibilityTests(unittest.TestCase):
    def test_fresh_upload_publishes_capital_before_operating_advice(self):
        report = {"entities": []}
        parsed = {"report": report}
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "study.sqlite3")
            state = new_assessment(store, b"source workbook", "balance.xlsx", "We sell water")

            def calculations(actual_report, description, plan, **kwargs):
                complete = bool(plan.get("operating_economics"))
                return {"stages": {
                    "capex": {"status": "provisional", "result": {"total_capex": "1000"}},
                    "financial": {"status": "calculated_preliminary" if complete else "unresolved", "result": {"ledger": []} if complete else None},
                }}

            def advice(*args, requested_sections, **kwargs):
                if requested_sections == ("revenue", "opex"):
                    published = store.get(state["id"])
                    self.assertTrue(published["running"])
                    self.assertEqual(published["results"]["stages"]["capex"]["result"]["total_capex"], "1000")
                    sections = [{"section": "operating_economics", "value_json": '{"operating": {"days_per_year": 314}}'}]
                else:
                    sections = []
                return {"sections": sections, "source_review": [], "questions": []}, {}

            with (
                patch("backend.orchestration.service.parse", return_value=parsed),
                patch("backend.orchestration.service.review", return_value=(report, {"questions": []}, [], {})),
                patch("backend.orchestration.service.propose", side_effect=advice) as advisor,
                patch("backend.orchestration.service.run", side_effect=calculations),
            ):
                finished = execute(store, state["id"], content=b"source workbook", use_ai=True, provider=object())
            self.assertEqual(advisor.call_count, 2)
            self.assertFalse(finished["running"])
            self.assertEqual(finished["status"], "calculated_with_disclosures")

    def test_missing_financial_result_is_incomplete_not_success(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "study.sqlite3")
            state = new_assessment(store, b"source", "balance.xlsx", "We sell water")
            state["parsed"] = {"report": {"entities": []}}
            store.put(state, state["revision"])
            with patch("backend.orchestration.service.run", return_value={"stages": {"financial": {"result": None}}}):
                finished = execute(store, state["id"])
            self.assertTrue(finished["status"].startswith("incomplete_assessment"))
