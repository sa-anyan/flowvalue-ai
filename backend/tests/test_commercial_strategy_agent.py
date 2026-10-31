"""Agent proposals cannot replace arithmetic, consent, source or baseline controls."""

import copy
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

from backend.orchestration.codec import plain
from backend.orchestration.store import Store
from backend.revenue.llm.commercial_strategy_analyst import (
    analyse,
    execute_strategy,
    price_from_choice,
    retain_product,
)
from backend.tests.test_operating_economics import DESCRIPTION, fixture
from backend.tests.test_revenue_mece import config_line


def baseline():
    from backend.orchestration.operating_economics import calculate_operating_study

    report, config, capex = fixture()
    result = calculate_operating_study(report, DESCRIPTION, config, capex)
    return {
        "id": "baseline",
        "description": DESCRIPTION,
        "plan": {"operating_economics": config},
        "parsed": {"report": report},
        "results": {
            "stages": {
                "revenue": {"result": plain(result["revenue"])},
                "financial": {"result": {}},
            }
        },
        "assumptions": {},
        "locked": [],
        "running": False,
        "progress": [],
    }


def selection():
    return {
        "candidate_index": 0,
        "reference_quantity": 1,
        "reference_unit": "m3",
        "observation_year": "2025",
        "basis_method": "cpi_purchasing_power_proxy",
        "rationale": "Explicit synthetic purchasing-power scenario",
        "limitations": ["Not a contract"],
    }


def research():
    return {
        "narrative": "Synthetic dated tariff, not an actual market observation",
        "candidates": [
            {
                "price": 2,
                "currency": "USD",
                "quantity_unit": "m3",
                "source_url": "https://example.org/tariff",
                "source_date": "2025",
                "price_period": "2025",
            }
        ],
        "sources": [{"url": "https://example.org/tariff"}],
    }


class AgentTests(unittest.TestCase):
    def test_python_basis_math(self):
        rate, basis = price_from_choice(
            selection(),
            research(),
            {"price_basis": {"currency": "USD", "price_period": "early1987"}},
        )
        self.assertLess(
            abs(rate - Decimal(2) * Decimal("113.6") / Decimal("321.943")),
            Decimal("1e-26"),
        )
        self.assertEqual(basis["status"], "provisional_agent_assumption_not_contract")

    def test_unretrieved_and_mismatched_basis(self):
        for field, value in [
            ("source_url", "https://example.org/invented"),
            ("currency", "GBP"),
        ]:
            r = research()
            r["candidates"][0][field] = value
            with self.assertRaises(ValueError):
                price_from_choice(
                    selection(),
                    r,
                    {"price_basis": {"currency": "USD", "price_period": "early1987"}},
                )
        c = selection()
        c["basis_method"] = "same_basis"
        with self.assertRaises(ValueError):
            price_from_choice(
                c,
                research(),
                {"price_basis": {"currency": "USD", "price_period": "early1987"}},
            )

    def test_missing_candidate_not_zero(self):
        c = selection()
        c["candidate_index"] = None
        with self.assertRaises(ValueError):
            price_from_choice(
                c,
                research(),
                {"price_basis": {"currency": "USD", "price_period": "early1987"}},
            )

    def test_preserve_previous_product_without_model_numbers(self):
        s = baseline()
        line = retain_product("water-sales", s)
        self.assertEqual(
            line["years"][0]["quantity"],
            s["results"]["stages"]["revenue"]["result"]["products"][0]["quantity_sold"],
        )
        with self.assertRaises(ValueError):
            retain_product("invented", s)

    def test_no_research_without_consent(self):
        s = baseline()
        p = Mock(model="mock")
        new = config_line(
            s["plan"]["operating_economics"]["financial"]["operating_years"]
        )
        p.generate.return_value = {
            "retained_product_ids": ["water-sales"],
            "retain_price_policy": "freeze_previous_annual_prices",
            "new_payments": [new],
            "research_line_ids": ["treatment"],
            "rationale": "Two distinct synthetic payments",
            "questions": [],
        }
        with patch(
            "backend.revenue.llm.commercial_strategy_analyst.research_draft"
        ) as web:
            with self.assertRaises(PermissionError):
                analyse(s, DESCRIPTION, p, research_consent=False)
            web.assert_not_called()

    def test_agent_driver_selects_and_routes_without_touching_cost_inputs(self):
        s = baseline()
        p = Mock(model="mock")
        new = config_line(
            s["plan"]["operating_economics"]["financial"]["operating_years"]
        )
        p.generate.side_effect = [
            {
                "retained_product_ids": ["water-sales"],
                "retain_price_policy": "freeze_previous_annual_prices",
                "new_payments": [new],
                "research_line_ids": ["treatment"],
                "rationale": "Two distinct synthetic payments",
                "questions": [],
            },
            selection(),
        ]
        with (
            patch(
                "backend.revenue.llm.commercial_strategy_analyst.research_draft",
                return_value=research(),
            ),
            patch(
                "backend.revenue.llm.commercial_strategy_analyst.run",
                return_value={"stages": {"financial": {"result": {"ok": True}}}},
            ),
        ):
            plan, _, agent, _ = analyse(s, DESCRIPTION, p, research_consent=True)
        self.assertEqual(len(plan["operating_economics"]["commercial_lines"]), 2)
        self.assertEqual(
            plan["operating_economics"]["materials"],
            s["plan"]["operating_economics"]["materials"],
        )
        self.assertEqual(
            s["plan"]["operating_economics"]["sales"][0]["id"], "water-sales"
        )
        self.assertEqual(agent["name"], "Commercial Strategy Analyst")

    def test_failure_retains_audit_not_stale_results(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "state.db")
            s = baseline()
            draft = store.create(s, b"file")
            provider = Mock(model="mock")
            provider.generate.side_effect = ValueError("Invalid structured proposal")
            state = execute_strategy(store, draft["id"], s, provider=provider)
            self.assertIsNone(state["results"])
            self.assertFalse(state["running"])
            self.assertEqual(state["commercial_strategy"]["status"], "needs_review")

    def test_reference_volume_must_match_source(self):
        c = selection()
        c["reference_unit"] = "US gal"
        with self.assertRaisesRegex(ValueError, "volume unit"):
            price_from_choice(
                c,
                research(),
                {"price_basis": {"currency": "USD", "price_period": "early1987"}},
            )
        c = selection()
        c["reference_quantity"] = 1000
        with self.assertRaisesRegex(ValueError, "billing quantity"):
            price_from_choice(
                c,
                research(),
                {"price_basis": {"currency": "USD", "price_period": "early1987"}},
            )

    def test_api_creates_separate_scenario(self):
        import threading
        from types import SimpleNamespace

        from fastapi.testclient import TestClient

        import backend.api.app as api

        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "state.db")
            s = baseline()
            s["results"]["stages"]["financial"]["result"] = {"ledger": ["synthetic"]}
            original = store.create(s, b"file")
            with (
                patch.object(api, "store", store),
                patch.object(api, "lock", threading.Lock()),
                patch.object(
                    api, "executor", SimpleNamespace(submit=lambda work: work())
                ),
                patch(
                    "backend.revenue.llm.commercial_strategy_analyst.execute_strategy"
                ) as execute,
                TestClient(api.app, base_url="http://localhost") as client,
            ):
                r = client.post(
                    "/api/assessments/" + original["id"] + "/commercial-strategy",
                    json={
                        "revision": 0,
                        "description": "Two distinct revenue sources, no actual contract.",
                        "research_consent": True,
                    },
                )
                self.assertEqual(r.status_code, 202)
                new = store.get(r.json()["id"])
                self.assertNotEqual(new["id"], original["id"])
                self.assertIsNone(new["results"])
                self.assertEqual(new["parent_assessment"], original["id"])
                self.assertEqual(store.get(original["id"]), original)
                self.assertTrue(execute.call_args.kwargs["research_consent"])

    def test_memory_is_project_description_and_time_scoped(self):
        from datetime import UTC, datetime, timedelta

        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "state.db")
            original = store.create(baseline(), b"file")
            description = "Updated commercial process description."
            good = research()
            good.update(
                target_id="fee",
                kind="market",
                retrieved_at=datetime.now(UTC).isoformat(),
            )
            for parent, text, draft in [
                (original["id"], description, good),
                ("other", description, good),
                (original["id"], "Other description", good),
                (
                    original["id"],
                    description,
                    {
                        **good,
                        "retrieved_at": (
                            datetime.now(UTC) - timedelta(days=2)
                        ).isoformat(),
                    },
                ),
            ]:
                prior = copy.deepcopy(original)
                prior.update(
                    parent_assessment=parent,
                    description=text,
                    commercial_strategy={"name": "Commercial Strategy Analyst"},
                    research_drafts=[draft],
                )
                store.create(prior, b"file")
            current = copy.deepcopy(original)
            current["description"] = description
            new = store.create(current, b"file")
            with patch(
                "backend.revenue.llm.commercial_strategy_analyst.analyse",
                return_value=(
                    original["plan"],
                    original["results"],
                    {"rationale": "Synthetic", "questions": []},
                    [],
                ),
            ) as agent:
                execute_strategy(store, new["id"], original, provider=Mock())
                passed = agent.call_args.args[0]["prior_commercial_research"]
                self.assertEqual(passed, [good])

    def test_split_billing_unit_fields(self):
        c = selection()
        c.update(reference_quantity=748, reference_unit="US gal")
        draft = research()
        draft["candidates"][0].update(
            quantity_unit="tariff unit",
            size_unit="One unit is 748 gallons (100 cubic feet)",
        )
        value, _ = price_from_choice(
            c, draft, {"price_basis": {"currency": "USD", "price_period": "early1987"}}
        )
        self.assertGreater(value, 0)
