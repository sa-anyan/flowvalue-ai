"""Revenue follows stated payment mechanisms; physical output is not commercial intent."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from backend.orchestration.operating_economics import calculate_operating_study
from backend.orchestration.service import new_assessment
from backend.orchestration.store import Store
from backend.revenue.commercial_intent import (
    capture_manual_methods,
    require_resolved_intent,
    validate_intent,
)
from backend.tests.test_operating_economics import DESCRIPTION, fixture
from backend.tests.test_revenue_mece import config_line


def intent(methods):
    return {
        "status": "explicit",
        "mechanisms": [
            {
                "id": key,
                "category": category,
                "context_quote": quote,
                "interpretation": "User-stated " + category,
            }
            for key, category, quote in methods
        ],
        "questions": [],
    }


class IntentTests(unittest.TestCase):
    def test_service_only_no_product_income(self):
        r, c, cap = fixture()
        c["sales"] = []
        c["commercial_lines"] = [config_line(c["financial"]["operating_years"])]
        c["commercial_lines"][0]["intent_id"] = "treatment"
        description = (
            "We charge wastewater treatment fees only. No water or biomass is sold."
        )
        c["commercial_intent"] = intent(
            [
                (
                    "treatment",
                    "processing_services",
                    "charge wastewater treatment fees only",
                )
            ]
        )
        result = calculate_operating_study(r, description, c, cap)
        self.assertFalse(result["revenue"].products)
        self.assertTrue(result["revenue"].commercial)
        self.assertEqual(
            {x.category for x in result["revenue"].commercial}, {"processing_services"}
        )
        self.assertFalse(result["financial"].issues)

    def test_hybrid_retains_both_user_sources(self):
        r, c, cap = fixture()
        c["sales"][0]["intent_id"] = "sale"
        c["commercial_lines"] = [config_line(c["financial"]["operating_years"])]
        c["commercial_lines"][0]["intent_id"] = "fee"
        desc = DESCRIPTION + " We also receive a processing fee."
        c["commercial_intent"] = intent(
            [
                ("sale", "product_sales", "sells treated water"),
                ("fee", "processing_services", "receive a processing fee"),
            ]
        )
        result = calculate_operating_study(r, desc, c, cap)
        self.assertTrue(result["revenue"].products)
        self.assertTrue(result["revenue"].commercial)
        self.assertFalse(result["financial"].issues)

    def test_product_assumption_cannot_replace_service_method(self):
        _, c, _ = fixture()
        c["sales"][0]["intent_id"] = "fee"
        c["commercial_intent"] = intent(
            [("fee", "processing_services", "paid for treatment")]
        )
        with self.assertRaisesRegex(ValueError, "contradicts"):
            validate_intent(c, "We are paid for treatment. We do not sell the water.")

    def test_invented_output_sales_are_blocked(self):
        _, c, _ = fixture()
        c["sales"][0]["intent_id"] = "invented-biomass"
        c["commercial_intent"] = intent(
            [("fee", "processing_services", "paid for treatment")]
        )
        with self.assertRaisesRegex(ValueError, "no user-stated"):
            validate_intent(c, "We are paid for treatment.")

    def test_all_stated_methods_must_be_represented(self):
        _, c, _ = fixture()
        c["sales"][0]["intent_id"] = "sale"
        c["commercial_intent"] = intent(
            [
                ("sale", "product_sales", "sells treated water"),
                ("fee", "processing_services", "processing fee"),
            ]
        )
        with self.assertRaisesRegex(ValueError, "omitted"):
            validate_intent(c, DESCRIPTION + " Additional processing fee.")

    def test_missing_method_is_question_not_assumed_zero_or_sale(self):
        _, c, _ = fixture()
        c["sales"] = []
        c["commercial_intent"] = {
            "status": "needs_clarification",
            "mechanisms": [],
            "questions": ["How will this project earn revenue?"],
        }
        validate_intent(c, "The plant produces clean water.")
        with self.assertRaisesRegex(ValueError, "How will this project earn revenue"):
            require_resolved_intent(c, "The plant produces clean water.")
        _, wrong, _ = fixture()
        wrong["commercial_intent"] = c["commercial_intent"]
        with self.assertRaises(ValueError):
            validate_intent(wrong, "The plant produces clean water.")

    def test_fake_quote_not_accepted(self):
        _, c, _ = fixture()
        c["sales"][0]["intent_id"] = "sale"
        c["commercial_intent"] = intent(
            [("sale", "product_sales", "we sell clean water")]
        )
        with self.assertRaisesRegex(ValueError, "exact user-context"):
            validate_intent(c, "The process produces clean water. Pricing is unknown.")

    def test_multiple_lines_and_non_product_categories(self):
        for category in [
            "capacity_availability",
            "infrastructure_usage",
            "environmental_attributes",
            "other_contractual_income",
        ]:
            with self.subTest(category=category):
                config = {
                    "sales": [],
                    "commercial_lines": [
                        {
                            "id": "a",
                            "name": "Income",
                            "intent_id": "a",
                            "category": category,
                        }
                    ],
                    "commercial_intent": intent(
                        [("a", category, "We receive " + category + " payments")]
                    ),
                }
                validate_intent(config, "We receive " + category + " payments")

    def test_explicit_manual_changes_can_revise_method(self):
        _, c, _ = fixture()
        c["commercial_intent"] = intent([("old", "processing_services", "old service")])
        updated = capture_manual_methods(
            c, "I changed this working scenario to product sales"
        )
        validate_intent(updated, "Original process description")
        self.assertEqual(updated["intent_source"], "user_override")

    def test_revenue_description_is_saved_as_user_context(self):
        with tempfile.TemporaryDirectory() as folder:
            state = new_assessment(
                Store(Path(folder) / "test.db"),
                b"workbook",
                "test.xlsx",
                "We treat wastewater.",
                "We charge treatment fees and do not sell water.",
            )
            self.assertEqual(
                state["revenue_description"],
                "We charge treatment fees and do not sell water.",
            )
            self.assertEqual(state["process_description"], "We treat wastewater.")
            self.assertIn("USER REVENUE DESCRIPTION", state["description"])

    def test_legacy_saved_baseline_not_silently_reclassified(self):
        _, c, _ = fixture()
        validate_intent(c, DESCRIPTION)

    def test_initial_advisor_contract_requires_intent(self):
        from backend.orchestration.operating_advisor import generate

        class Capture(Exception):
            pass

        provider = Mock()

        def capture(**kwargs):
            schema = kwargs["schema"]
            self.assertIn("commercial_intent", schema["required"])
            self.assertIn(
                "intent_id", schema["properties"]["sales"]["items"]["required"]
            )
            self.assertIn(
                "intent_id",
                schema["properties"]["commercial_lines"]["items"]["required"],
            )
            self.assertIn("processing_services", kwargs["instructions"])
            raise Capture()

        provider.generate.side_effect = capture
        with self.assertRaises(Capture):
            generate(provider, "", {"description": "We are paid for treatment only."})

    def test_entry_upload_passes_commercial_context_into_assessment(self):
        from unittest.mock import patch

        from fastapi.testclient import TestClient

        import backend.api.app as api

        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "api.db")
            with (
                patch.object(api, "store", store),
                patch.object(api, "submit"),
                TestClient(api.app, base_url="http://localhost") as client,
            ):
                response = client.post(
                    "/api/assessments",
                    data={
                        "description": "We produce treated water.",
                        "revenue_description": "We are paid only for processing wastewater.",
                        "use_ai": "false",
                    },
                    files={
                        "file": (
                            "example.xlsx",
                            b"fixture-not-parsed-in-this-transport-test",
                        )
                    },
                )
                self.assertEqual(response.status_code, 202)
                state = store.get(response.json()["id"])
                self.assertEqual(
                    state["revenue_description"],
                    "We are paid only for processing wastewater.",
                )
                self.assertIn(
                    "We are paid only for processing wastewater.", state["description"]
                )

    def test_initial_advisor_corrects_wrong_category_once(self):
        from unittest.mock import Mock

        from backend.orchestration.operating_advisor import generate

        _, config, _ = fixture()
        for key in ("methodology", "assumption_date", "origin", "price_basis"):
            config.pop(key, None)
        config["sales"][0]["intent_id"] = "sale"
        for factor in config["garrett_factors"].values():
            factor["fraction"] = float(factor["fraction"])
        for energy in config["energy"]:
            energy.update(
                volume_m3=None,
                power_density_w_m3=None,
                specific_kwh_per_kg=None,
                pressure_difference_bar=None,
            )
        config["commercial_lines"] = []
        config["avoided_costs"] = []
        config["commercial_intent"] = intent(
            [("sale", "product_sales", "sells treated water")]
        )
        for group in ("sales", "materials"):
            for item in config.get(group, []):
                item["unit_price_currency"] = None
        wrong = copy.deepcopy(config)
        wrong["commercial_intent"]["mechanisms"][0]["category"] = "processing_services"
        provider = Mock()
        provider.generate.side_effect = [wrong, config]
        output = generate(
            provider,
            "",
            {
                "description": DESCRIPTION,
                "calculated_stage_summary": {
                    "capex": {"result": {"currency": "USD", "period": "early 1987"}}
                },
            },
        )
        self.assertEqual(provider.generate.call_count, 2)
        value = json.loads(output["sections"][0]["value_json"])
        self.assertEqual(
            value["commercial_intent"]["mechanisms"][0]["category"], "product_sales"
        )
