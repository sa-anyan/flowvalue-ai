"""Independently calculated multi-mechanism commercial schedules and financial handoff."""

import copy
import unittest
from dataclasses import replace
from decimal import Decimal as D
from decimal import localcontext
from unittest.mock import Mock

from backend.capex import calculate_capex
from backend.financial_modelling.connectors.revenue.interface import sales_from_result
from backend.orchestration.operating_economics import calculate_operating_study
from backend.revenue import calculate_revenue, freeze_project, restore_project
from backend.revenue.llm.commercial_interpreter import interpret
from backend.revenue.models import CommercialLine, PaymentYear
from backend.revenue.registry import list_categories
from backend.tests.test_capex import inputs
from backend.tests.test_operating_economics import DESCRIPTION
from backend.tests.test_operating_economics import fixture as operating_fixture
from backend.tests.test_revenue import a, fixture


def line(category="processing_services", identity="fee", years=(1,)):
    return CommercialLine(
        identity,
        "Synthetic fee",
        category,
        identity,
        "m3",
        "per_unit",
        "user_assumption",
        "Explicit synthetic commercial assumption, not a contract",
        (),
        tuple(
            PaymentYear(
                y,
                a(100, "m3"),
                a(2, "GBP/m3"),
                a(0, "GBP/year"),
                a(0, "m3"),
                a(0, "GBP/year"),
                a(1),
                a(0, "fraction/year"),
            )
            for y in years
        ),
        eligibility_basis="Synthetic eligibility assumption; independent verification required",
    )


def project(*lines, savings=()):
    return replace(
        fixture(), products=(), commercial_lines=tuple(lines), avoided_costs=savings
    )


def config_line(life=1, category="processing_services"):
    return {
        "id": "treatment",
        "name": "Treatment fee",
        "category": category,
        "payment_id": "treatment",
        "quantity_unit": "m3",
        "rate_period": "per_unit",
        "arrangement": "user_assumption",
        "context_quote": "",
        "rationale": "Synthetic user assumption",
        "uncertainty": "Unverified",
        "source_references": [],
        "stream_key": "water",
        "property": "volume_flow",
        "component": None,
        "fixed_variable_distinct": False,
        "eligibility_basis": "",
        "years": [
            {
                "year": y,
                "quantity": None,
                "rate": 2,
                "fixed_payment": 0,
                "minimum_quantity": 0,
                "minimum_payment": 0,
                "availability": 1,
                "escalation": 0,
                "periods": 1,
            }
            for y in range(1, life + 1)
        ],
    }


class RevenueMechanismsTests(unittest.TestCase):
    def test_each_category(self):
        for category in list_categories():
            with self.subTest(category=category):
                result = calculate_revenue(project(line(category)))
                self.assertFalse(result.issues)
                self.assertEqual(result.annual[0].sales_revenue, D(200))
                self.assertEqual(result.commercial[0].category, category)

    def test_six_categories_plus_existing_products(self):
        lines = tuple(line(c, c) for c in list_categories())
        p = replace(fixture(), commercial_lines=lines)
        result = calculate_revenue(p)
        self.assertFalse(result.issues)
        self.assertEqual(result.annual[0].sales_revenue, D(3201200))
        finance = sales_from_result(result, 1, price_year=2026)
        self.assertEqual(
            sum(p.revenue.amount for p in finance), result.annual[0].sales_revenue
        )
        self.assertEqual(len(finance), 7)

    def test_multiple_lines_same_category(self):
        self.assertEqual(
            calculate_revenue(project(line(identity="a"), line(identity="b")))
            .annual[0]
            .sales_revenue,
            D(400),
        )

    def test_multiple_products_preserve_allocations(self):
        p = fixture()
        first = replace(p.products[0], allocation_fraction=a(".5"))
        second = replace(first, id="P-2")
        result = calculate_revenue(
            replace(p, products=(first, second), commercial_lines=(line(),))
        )
        self.assertFalse(result.issues)
        self.assertEqual(result.annual[0].sales_revenue, D(3200200))

    def test_duplicate_payment_cross_categories_rejected(self):
        result = calculate_revenue(project(line(), line("infrastructure_usage")))
        self.assertIn("Duplicate", str(result.issues))
        self.assertFalse(result.annual)

    def test_duplicate_with_legacy_product_rejected(self):
        p = replace(fixture(), commercial_lines=(line(identity="P-1"),))
        self.assertTrue(calculate_revenue(p).issues)

    def test_unknown_price_is_unresolved_not_zero(self):
        l = line()
        l = replace(l, years=(replace(l.years[0], rate=a(None, "GBP/m3")),))
        result = calculate_revenue(project(l))
        self.assertTrue(result.issues)
        self.assertFalse(result.annual)

    def test_no_identified_income_unresolved(self):
        self.assertTrue(calculate_revenue(replace(fixture(), products=())).issues)

    def test_fixed_plus_variable_and_minimum_floor(self):
        l = line()
        y = replace(
            l.years[0],
            fixed_payment=a(50, "GBP/year"),
            minimum_payment=a(300, "GBP/year"),
        )
        self.assertTrue(calculate_revenue(project(replace(l, years=(y,)))).issues)
        result = calculate_revenue(
            project(replace(l, fixed_variable_distinct=True, years=(y,)))
        )
        self.assertEqual(result.annual[0].sales_revenue, D(300))  # max(300,50+100*2)

    def test_annual_and_monthly_capacity_with_availability(self):
        l = line("capacity_availability")
        y = replace(
            l.years[0], rate=a(2, "GBP/m3/month"), availability=a(".9"), periods=12
        )
        result = calculate_revenue(
            project(replace(l, rate_period="monthly", years=(y,)))
        )
        self.assertEqual(result.annual[0].sales_revenue, D(2160))
        self.assertTrue(
            calculate_revenue(
                project(replace(l, rate_period="annual", years=(y,)))
            ).issues
        )

    def test_changes_and_escalation(self):
        l = line(years=(1, 2))
        y1, y2 = l.years
        y2 = replace(
            y2,
            quantity=a(200, "m3"),
            rate=a(3, "GBP/m3"),
            escalation=a(".1", "fraction/year"),
        )
        result = calculate_revenue(
            project(replace(l, years=(y1, y2))), engineering_scenario=True
        )
        # Project schedule must match: missing year rejected rather than ignored.
        self.assertTrue(result.issues)
        p = project(replace(l, years=(y1, y2)))
        p = replace(p, schedule=(p.schedule[0], replace(p.schedule[0], year=2)))
        self.assertEqual(
            [r.sales_revenue for r in calculate_revenue(p).annual], [D(200), D(660)]
        )

    def test_environmental_eligibility_not_automatic(self):
        self.assertTrue(
            calculate_revenue(
                project(replace(line("environmental_attributes"), eligibility_basis=""))
            ).issues
        )

    def test_fixed_income_no_physical_sales(self):
        l = line("other_contractual_income")
        y = replace(
            l.years[0],
            quantity=a(0, "m3"),
            rate=a(0, "GBP/m3"),
            fixed_payment=a(500, "GBP/year"),
        )
        result = calculate_revenue(project(replace(l, years=(y,))))
        handoff = sales_from_result(result, 1, price_year=2026)
        self.assertEqual(handoff[0].sold, 0)
        self.assertEqual(handoff[0].revenue.amount, 500)
        self.assertEqual(handoff[0].revenue_category, "other_contractual_income")

    def test_snapshot_and_recalculation_dont_call_llm(self):
        p = project(line())
        restored = restore_project(freeze_project(p))
        self.assertEqual(p, restored)
        self.assertEqual(calculate_revenue(p), calculate_revenue(restored))

    def test_negative_nonfinite_wrong_units(self):
        for value, unit in [(-1, "GBP/m3"), (1, "USD/m3"), (1, "GBP/kg")]:
            l = line()
            l = replace(l, years=(replace(l.years[0], rate=a(value, unit)),))
            self.assertTrue(calculate_revenue(project(l)).issues)

    def test_excluded_income_keeps_reason(self):
        l = replace(line(), included=False, exclusion_reason="Not applicable")
        result = calculate_revenue(project(l))
        self.assertFalse(result.issues)
        self.assertEqual(result.annual[0].sales_revenue, 0)


class CommercialIntegrationTests(unittest.TestCase):
    def test_treatment_only_all_the_way_to_finance(self):
        report, config, _ = operating_fixture()
        config["sales"] = []
        life = config["financial"]["operating_years"]
        config["commercial_lines"] = [config_line(life)]
        result = calculate_operating_study(
            report, DESCRIPTION, config, calculate_capex(inputs=inputs())
        )
        self.assertFalse(result["financial"].issues)
        for annual in result["revenue"].annual:
            ledger = result["financial"].ledger[
                annual.year + config["financial"]["construction_years"]
            ]
            self.assertEqual(ledger.revenue, annual.sales_revenue)
            self.assertEqual(
                annual.sales_revenue,
                D(100)
                * D(314)
                * 24
                * D(
                    str(
                        config["financial"]["production_ramp"][
                            min(
                                annual.year - 1,
                                len(config["financial"]["production_ramp"]) - 1,
                            )
                        ]
                    )
                )
                * 2,
            )

    def test_fixed_payment_finance_validation(self):
        report, config, _ = operating_fixture()
        config["sales"] = []
        life = config["financial"]["operating_years"]
        l = config_line(life, "other_contractual_income")
        l.update(stream_key=None, property="contract_quantity")
        for y in l["years"]:
            y.update(quantity=0, rate=0, fixed_payment=1000)
        config["commercial_lines"] = [l]
        result = calculate_operating_study(
            report, DESCRIPTION, config, calculate_capex(inputs=inputs())
        )
        self.assertFalse(result["financial"].issues)
        self.assertTrue(all(r.sales_revenue == 1000 for r in result["revenue"].annual))

    def test_savings_only_reduces_target_not_revenue(self):
        report, config, _ = operating_fixture()
        config["sales"] = []
        life = config["financial"]["operating_years"]
        config["avoided_costs"] = [
            {
                "id": "avoided-disposal",
                "target_opex_id": "feed:acid",
                "rationale": "Explicit synthetic counterfactual",
                "already_applied": False,
                "years": [{"year": y, "amount": 10} for y in range(1, life + 1)],
            }
        ]
        result = calculate_operating_study(
            report, DESCRIPTION, config, calculate_capex(inputs=inputs())
        )
        self.assertFalse(result["financial"].issues)
        self.assertTrue(all(r.sales_revenue == 0 for r in result["revenue"].annual))
        for y, rows in result["detail"]["years"].items():
            target = next(r for r in result["opex"][y].lines if r.id == "feed:acid")
            self.assertEqual(target.amount, rows["materials"][0]["annual_cost"] - 10)
        bad = copy.deepcopy(config)
        bad["avoided_costs"][0]["already_applied"] = True
        with self.assertRaises(ValueError):
            calculate_operating_study(
                report, DESCRIPTION, bad, calculate_capex(inputs=inputs())
            )

    def test_savings_wrong_target_and_over_reduction(self):
        report, config, _ = operating_fixture()
        life = config["financial"]["operating_years"]
        for target, amount in [("missing", 1), ("feed:acid", 10**9)]:
            config["avoided_costs"] = [
                {
                    "id": "saving",
                    "target_opex_id": target,
                    "rationale": "Explicit assumption",
                    "already_applied": False,
                    "years": [
                        {"year": y, "amount": amount} for y in range(1, life + 1)
                    ],
                }
            ]
            with self.assertRaises(ValueError):
                calculate_operating_study(
                    report, DESCRIPTION, config, calculate_capex(inputs=inputs())
                )

    def test_structured_interpreter_calls_existing_provider_only(self):
        provider = Mock()
        provider.generate.return_value = {"commercial_lines": [], "avoided_costs": []}
        self.assertEqual(
            interpret(provider, {"description": "No income specified"}),
            provider.generate.return_value,
        )
        self.assertNotIn("research", provider.generate.call_args.kwargs)

    def test_capacity_not_annualized_from_stream_flow(self):
        report, config, capex = operating_fixture()
        config["sales"] = []
        config["commercial_lines"] = [
            config_line(config["financial"]["operating_years"], "capacity_availability")
        ]
        with self.assertRaisesRegex(ValueError, "not annual throughput"):
            calculate_operating_study(report, DESCRIPTION, config, capex)

    def test_fake_llm_sources_are_not_market_evidence(self):
        report, config, capex = operating_fixture()
        l = config_line(config["financial"]["operating_years"])
        l.update(
            arrangement="llm_proposed", source_references=["invented market survey"]
        )
        config["commercial_lines"] = [l]
        with self.assertRaisesRegex(ValueError, "supplied engineering evidence"):
            calculate_operating_study(report, DESCRIPTION, config, capex)

    def test_mixed_income_offsets_cost_plus_and_reconciles(self):
        report, config, capex = operating_fixture()
        config["sales"][0]["price_mode"] = "cost_plus"
        config["commercial_lines"] = [
            config_line(config["financial"]["operating_years"])
        ]
        for year in config["commercial_lines"][0]["years"]:
            year["rate"] = 0.001
        result = calculate_operating_study(report, DESCRIPTION, config, capex)
        self.assertFalse(result["financial"].issues)
        for r in result["revenue"].annual:
            self.assertLess(
                abs(
                    r.sales_revenue - result["opex"][r.year].annual_cash_opex * D("1.2")
                ),
                D("1e-20"),
            )
            with localcontext() as context:
                context.prec = 40
                self.assertEqual(
                    r.sales_revenue,
                    sum(
                        (
                            p.net_sales_revenue
                            for p in result["revenue"].products
                            if p.year == r.year
                        ),
                        D(0),
                    )
                    + sum(
                        (
                            c.revenue
                            for c in result["revenue"].commercial
                            if c.year == r.year
                        ),
                        D(0),
                    ),
                )
