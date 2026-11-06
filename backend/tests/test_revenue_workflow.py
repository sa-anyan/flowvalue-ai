"""Entry's revenue-only workflow requires design inputs and never runs other engines."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.orchestration import operating_advisor
from backend.orchestration.ingest import parse
from backend.orchestration.service import execute, new_assessment
from backend.orchestration.store import Store
from backend.revenue.authority import update
from backend.orchestration.current_prices import current_price_view
from backend.tests.revenue_fixtures import workbook, plan_for


class RevenueWorkflowTests(unittest.TestCase):
    def test_balance_and_process_description_are_both_required(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "test.db")
            for content, description in [(b"", "Water treatment"), (b"workbook", ""), (b"workbook", " \n ")]:
                with self.assertRaisesRegex(ValueError, "mass and energy balance"):
                    new_assessment(store, content, "balance.xlsx", description, workflow="revenue")

    def test_approved_revenue_runs_without_capex_opex_or_financials_and_stays_scoped_on_rerun(self):
        content = workbook()
        parsed = parse(content, "synthetic.xlsx")
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "test.db")
            state = new_assessment(store, content, "synthetic.xlsx", "Water treatment", "sells treated water", workflow="revenue")
            state.update(parsed=parsed, plan=plan_for(parsed["report"]), running=False)
            state = store.put(state, state["revision"])
            state = update(store, state["id"], state["revision"], approve=True)
            with patch("backend.orchestration.service.run", side_effect=AssertionError("Full pipeline must not run")), patch("backend.orchestration.operating_economics.calculate_opex", side_effect=AssertionError("No OPEX")), patch("backend.orchestration.operating_economics.calculate_financials", side_effect=AssertionError("No financials")):
                first = execute(store, state["id"])
                second = execute(store, state["id"])
            for result in (first, second):
                self.assertNotIn("error", result)
                self.assertEqual(set(result["results"]["stages"]), {"revenue"})
                self.assertEqual(result["status"], "revenue_calculated")
                self.assertTrue(result["results"]["stages"]["revenue"]["result"]["annual"])
            with patch("backend.orchestration.current_prices.run", side_effect=AssertionError("Viewing revenue must not run the full pipeline")):
                view = current_price_view(second)
                self.assertEqual(set(view["results"]["stages"]), {"revenue"})
            updated = update(store, second["id"], second["revision"], text="sells treated water at a revised price")
            self.assertEqual(set(updated["results"]["stages"]), {"revenue"})

    def test_unapproved_revenue_remains_a_draft(self):
        content = workbook()
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "test.db")
            state = new_assessment(store, content, "synthetic.xlsx", "Water treatment", workflow="revenue")
            result = execute(store, state["id"], content=content)
            self.assertEqual(result["status"], "revenue_pending_user_input")
            self.assertEqual(set(result["results"]["stages"]), {"revenue"})
            self.assertTrue(result["revenue_questions"])

    def test_revenue_ai_contract_omits_costs_and_financial_assumptions(self):
        class CaptureProvider:
            def generate(self, *, instructions, context, schema):
                self.schema = copy.deepcopy(schema)
                raise RuntimeError("schema captured without a provider call")
        provider = CaptureProvider()
        with self.assertRaisesRegex(RuntimeError, "schema captured"):
            operating_advisor.generate(provider, "", {"report": {"entities": []}}, revenue_only=True)
        fields = provider.schema["properties"]
        self.assertNotIn("materials", fields)
        self.assertNotIn("energy", fields)
        self.assertNotIn("garrett_factors", fields)
        self.assertEqual(set(fields["financial"]["properties"]), {"operating_years", "production_ramp", "rationale"})
        self.assertEqual(fields["sales"]["items"]["properties"]["price_mode"]["enum"], ["assumed_price"])
        with self.assertRaisesRegex(RuntimeError, "schema captured"):
            operating_advisor.generate(provider, "", {"report": {"entities": []}, "revenue_edit": True,
                "plan": {"operating_economics": {"price_basis": {"currency": "USD", "price_period": "unspecified reference year"}}}}, revenue_only=True)
        basis = provider.schema["properties"]["price_basis"]["properties"]
        self.assertEqual(basis["currency"]["enum"], ["USD"])
        self.assertEqual(basis["price_period"]["enum"], ["unspecified reference year"])

    def test_ai_planning_requests_revenue_only_and_retains_review_gate(self):
        content = workbook()
        parsed = parse(content, "synthetic.xlsx")
        config = plan_for(parsed["report"])["operating_economics"]
        response = {"sections": [{"section": "operating_economics", "value_json": json.dumps(config)}], "questions": []}
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "test.db")
            state = new_assessment(store, content, "synthetic.xlsx", "Water treatment", "sells treated water", workflow="revenue")
            state.update(parsed=parsed, running=False)
            state = store.put(state, state["revision"])
            with patch("backend.orchestration.revenue_workflow.review", return_value=(parsed["report"], {"questions": []}, [], {"status": "reviewed"})), patch("backend.orchestration.revenue_workflow.propose", return_value=(response, {"model": "fake"})) as proposal, patch("backend.orchestration.service.run", side_effect=AssertionError("No full pipeline")):
                result = execute(store, state["id"], use_ai=True, provider=object())
            self.assertNotIn("error", result)
            self.assertEqual(proposal.call_args.kwargs["requested_sections"], ("revenue",))
            self.assertTrue(proposal.call_args.kwargs["force_refresh"])
            self.assertTrue(proposal.call_args.args[0]["revenue_edit"])
            self.assertEqual(proposal.call_args.args[0]["revenue_box"], "sells treated water")
            self.assertEqual(result["status"], "revenue_pending_user_input")
            self.assertEqual(set(result["results"]["stages"]), {"revenue"})

    def test_upload_api_rejects_blank_process_before_starting_work(self):
        from fastapi.testclient import TestClient
        from backend.api import app as api
        content = workbook()
        with tempfile.TemporaryDirectory() as folder, patch.object(api, "store", Store(Path(folder) / "test.db")), patch.object(api, "submit") as submit:
            client = TestClient(api.app)
            response = client.post("/api/assessments", files={"file": ("synthetic.xlsx", content)}, data={"workflow": "revenue", "description": "   "})
            self.assertEqual(response.status_code, 422)
            submit.assert_not_called()
            response = client.post("/api/assessments", data={"workflow": "revenue", "description": "Water treatment"})
            self.assertEqual(response.status_code, 422)
            response = client.post("/api/assessments", files={"file": ("synthetic.xlsx", content)}, data={"workflow": "revenue", "description": "Water treatment"})
            self.assertEqual(response.status_code, 202)
            saved = api.store.get(response.json()["id"])
            self.assertEqual(saved["workflow"], "revenue")
