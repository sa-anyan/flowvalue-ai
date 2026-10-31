"""Independent quantities, energy physics, coupled sales factors and full annual handoff."""

import copy
import unittest
from decimal import Decimal as D

from backend.capex import calculate_capex
from backend.opex.energy_costs import equipment_energy_cost
from backend.opex.indexes.garrett.model import CATEGORIES
from backend.orchestration.operating_economics import calculate_operating_study
from backend.tests.test_capex import inputs

DESCRIPTION = "The plant sells treated water from outlet W-1 by cubic metre. These are synthetic test assumptions, not market quotations."


def fixture():
    def entity(key, kind, property, value, unit):
        return {
            "key": key,
            "kind": kind,
            "identifier": key,
            "values": [
                {
                    "id": key + ":value",
                    "property": property,
                    "component": None,
                    "normalized_value": value,
                    "normalized_unit": unit,
                    "status": "inferred",
                    "workbook": "synthetic.xlsx",
                    "sheet": "MEB",
                    "cell": "B2",
                }
            ],
        }

    report = {
        "entities": [
            entity("water", "material", "volume_flow", 100, "m3/h"),
            entity("feed", "material", "mass_flow", 2, "kg/h"),
            entity("pump", "equipment", "type", "Pump", None),
        ]
    }
    metadata = {
        "rationale": "Explicit synthetic engineering test",
        "uncertainty": "Not industrially validated",
    }
    config = {
        "methodology": "garrett",
        "assumption_date": "2026-10-31",
        "origin": "Synthetic test",
        "price_basis": {"currency": "USD", "price_period": "early 1987"},
        "operating": {
            "days_per_year": 314,
            "hours_per_day": 24,
            "rationale": "User-requested planning assumption, not maximum efficiency",
        },
        "sales": [
            {
                "id": "water-sales",
                "name": "Treated water",
                "stream_key": "water",
                "context_quote": "sells treated water",
                "role": "main_product",
                "quantity_unit": "m3",
                "allocation_fraction": 1,
                "saleable_fraction": 0.9,
                "sold_fraction": 0.8,
                "price_mode": "assumed_price",
                "unit_price": 1,
                "cost_markup_fraction": 0.2,
                "net_freight_deduction_per_unit": 0.1,
                "net_packaging_deduction_per_unit": 0,
                "specification_basis": "Synthetic conditional grade",
                **metadata,
            }
        ],
        "materials": [
            {
                "id": "acid",
                "name": "Synthetic purchased acid",
                "stream_key": "feed",
                "property": "mass_flow",
                "component": None,
                "quantity_unit": "kg",
                "annual_quantity_assumption": None,
                "unit_price": 0.5,
                "category": "raw_materials",
                **metadata,
            }
        ],
        "energy": [
            {
                "id": "pump-power",
                "name": "Pump electricity",
                "equipment_key": "pump",
                "source_key": None,
                "method": "electrical_assumption",
                "utility": "electricity",
                "power_kw": 10,
                "efficiency": 1,
                "load_fraction": 0.8,
                "tariff_per_kwh": 0.05,
                "behavior": "variable",
                **metadata,
            }
        ],
        "labour": [
            {
                "id": "operators",
                "role": "Operators",
                "headcount_fte": 3,
                "annual_base_salary": 30000,
                "allocation_fraction": 1,
                "arrangement": "new_hire",
                "category": "operating_labor",
                "behavior": "fixed",
                **metadata,
            }
        ],
        "additional_expenses": [],
        "garrett_factors": {
            c.id: {
                "fraction": c.minimum,
                "rationale": "Synthetic selection at documented minimum",
            }
            for c in CATEGORIES
            if c.base
        },
        "financial": {
            "operating_years": 3,
            "construction_years": 1,
            "construction_spend_fractions": [1],
            "production_ramp": [0.6, 0.8, 1],
            "discount_rate": 0.1,
            "tax_rate": 0.25,
            "depreciation_years": 3,
            "salvage_fraction": 0,
            "working_capital_recovery_fraction": 1,
            "closure_allowance": 0,
            "rationale": "Synthetic flat policy; not legal guidance",
        },
        "scope_notes": ["Synthetic fixture only"],
        "questions": [],
    }
    return report, config, calculate_capex(inputs=inputs())


class OperatingEconomicsTests(unittest.TestCase):
    def test_quantities_use_314_day_schedule_and_ramp_once(self):
        report, config, capex = fixture()
        r = calculate_operating_study(report, DESCRIPTION, config, capex)
        self.assertEqual(r["detail"]["annual_hours"], D(7536))
        detail = r["detail"]["years"][1]
        self.assertEqual(detail["materials"][0]["annual_quantity"], D("9043.2"))
        self.assertEqual(detail["materials"][0]["annual_cost"], D("4521.60"))
        self.assertEqual(detail["energy"][0]["annual_energy_kwh"], D("36172.8"))
        self.assertEqual(detail["energy"][0]["annual_cost"], D("1808.640"))
        self.assertEqual(detail["labour"][0]["annual_cost"], D(90000))
        product = r["revenue"].products[0]
        self.assertEqual(product.quantity_sold, D("325555.20"))
        self.assertEqual(product.net_sales_revenue, D("292999.680"))
        self.assertEqual(r["financial"].status, "calculated_preliminary")
        self.assertEqual(len(r["financial"].ledger), 5)
        first = next(row for row in r["financial"].ledger if row.period.year == 2)
        self.assertEqual(first.revenue, r["revenue"].annual[0].sales_revenue)
        self.assertEqual(
            first.fixed_opex + first.variable_opex, r["opex"][1].annual_cash_opex
        )

    def test_cost_plus_solves_sales_dependent_opex_mutually(self):
        report, config, capex = fixture()
        config["sales"][0]["price_mode"] = "cost_plus"
        result = calculate_operating_study(report, DESCRIPTION, config, capex)
        for annual in result["revenue"].annual:
            self.assertLess(
                abs(
                    annual.sales_revenue
                    - result["opex"][annual.year].annual_cash_opex * D("1.2")
                ),
                D("1e-22"),
            )
        self.assertEqual(
            result["detail"]["coupling"][0]["sales_cost_fraction"], D(".025")
        )
        self.assertEqual(result["financial"].status, "calculated_preliminary")

    def test_explicit_product_statement_required_but_not_a_fake_sale(self):
        report, config, capex = fixture()
        with self.assertRaisesRegex(ValueError, "explicit project-context"):
            calculate_operating_study(
                report,
                "This is a water-treatment design with no sales statement.",
                config,
                capex,
            )

    def test_changes_propagate_and_original_stays_unchanged(self):
        report, config, capex = fixture()
        original = copy.deepcopy(config)
        baseline = calculate_operating_study(report, DESCRIPTION, config, capex)
        alternate = copy.deepcopy(config)
        alternate["energy"][0]["tariff_per_kwh"] = 0.1
        changed = calculate_operating_study(report, DESCRIPTION, alternate, capex)
        self.assertEqual(config, original)
        self.assertEqual(
            changed["opex"][1].annual_cash_opex - baseline["opex"][1].annual_cash_opex,
            D("1808.640"),
        )
        self.assertNotEqual(
            dict(changed["financial"].metrics)["project_npv"].value,
            dict(baseline["financial"].metrics)["project_npv"].value,
        )

    def test_hydraulic_and_shaft_energy_are_python_physics(self):
        report, config, _ = fixture()
        report["entities"].append(
            {
                "key": "hydraulic-feed",
                "kind": "material",
                "identifier": "H",
                "values": [
                    {
                        "id": "flow",
                        "property": "volume_flow",
                        "component": None,
                        "normalized_value": 36,
                        "normalized_unit": "m3/h",
                        "status": "verified",
                    }
                ],
            }
        )
        spec = dict(
            config["energy"][0],
            method="hydraulic",
            source_key="hydraulic-feed",
            pressure_difference_bar=1,
            efficiency=0.5,
            load_fraction=1,
            tariff_per_kwh=0.2,
        )
        r = equipment_energy_cost(spec, report, operating_hours=100)
        self.assertEqual(r["input_kw"], D(2))
        self.assertEqual(r["annual_cost"], D(40))
        spec.update(method="shaft_power", power_kw=10, efficiency=0.8)
        self.assertEqual(
            equipment_energy_cost(spec, report, operating_hours=100)["input_kw"],
            D("12.5"),
        )

    def test_detail_replaces_factor_and_duplicates_blocked(self):
        report, config, capex = fixture()
        config["labour"].append(
            dict(
                config["labour"][0],
                id="specialist",
                category="supervision",
                headcount_fte=0.2,
            )
        )
        r = calculate_operating_study(report, DESCRIPTION, config, capex)
        self.assertFalse(
            any(line.id == "garrett:supervision" for line in r["opex"][1].lines)
        )
        self.assertTrue(
            any(line.id == "staff:specialist" for line in r["opex"][1].lines)
        )
        config["materials"].append(dict(config["materials"][0], id="duplicate"))
        with self.assertRaisesRegex(ValueError, "charged more than once"):
            calculate_operating_study(report, DESCRIPTION, config, capex)

    def test_invalid_cost_plus_assumptions_do_not_make_invented_profit(self):
        report, config, capex = fixture()
        config["sales"][0]["price_mode"] = "cost_plus"
        config["sales"][0]["cost_markup_fraction"] = 100
        with self.assertRaisesRegex(ValueError, "no finite positive solution"):
            calculate_operating_study(report, DESCRIPTION, config, capex)

    def test_price_basis_not_silently_relabelled(self):
        report, config, capex = fixture()
        config["price_basis"]["price_period"] = "2026"
        with self.assertRaisesRegex(ValueError, "different currency/period"):
            calculate_operating_study(report, DESCRIPTION, config, capex)


class OperatingStudyLifecycleTests(unittest.TestCase):
    def test_saved_shared_assumptions_recalculate_without_ai_and_preserve_baseline(
        self,
    ):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        from backend.orchestration.codec import plain
        from backend.orchestration.service import compare, edit, execute, new_assessment
        from backend.orchestration.store import Store

        report, config, capex = fixture()

        def deterministic_run(actual_report, description, plan, **kwargs):
            r = calculate_operating_study(
                actual_report, description, plan["operating_economics"], capex
            )
            return {
                "stages": {
                    "revenue": {
                        "status": r["revenue"].status,
                        "result": plain(r["revenue"]),
                    },
                    "opex": {
                        "status": "calculated_preliminary",
                        "result": {
                            "years": {str(y): plain(v) for y, v in r["opex"].items()}
                        },
                    },
                    "financial": {
                        "status": r["financial"].status,
                        "result": plain(r["financial"]),
                    },
                },
                "scope": "Synthetic cost scope",
            }

        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "studies.db")
            state = new_assessment(store, b"", "synthetic.xlsx", DESCRIPTION)
            state.update(parsed={"report": report}, running=False)
            state["plan"]["operating_economics"] = config
            store.put(state, state["revision"])
            with (
                patch(
                    "backend.orchestration.service.run", side_effect=deterministic_run
                ),
                patch(
                    "backend.orchestration.service.propose",
                    side_effect=AssertionError("No paid call"),
                ),
            ):
                baseline = execute(store, state["id"])
                version = store.version(state["id"], "Baseline")
                alternate = copy.deepcopy(config)
                alternate["sales"][0]["unit_price"] = 2
                edit(
                    store,
                    state["id"],
                    baseline["revision"],
                    "operating_economics",
                    alternate,
                    "Independent higher-price scenario",
                )
                revised = execute(store, state["id"])
            opened = store.load(version)
            self.assertEqual(
                opened["plan"]["operating_economics"]["sales"][0]["unit_price"], 1
            )
            self.assertIn("operating_economics", revised["locked"])
            self.assertEqual(
                compare(opened, revised)["changed_sections"], ["operating_economics"]
            )
            self.assertNotEqual(
                opened["results"]["stages"]["financial"],
                revised["results"]["stages"]["financial"],
            )

    def test_shared_study_report_is_escaped_and_contains_complete_schedules(self):
        from backend.dashboard_reporting.study_report import render_study
        from backend.orchestration.codec import plain

        report, config, capex = fixture()
        r = calculate_operating_study(report, DESCRIPTION, config, capex)
        first = r["opex"][1]
        state = {
            "id": "test",
            "revision": 1,
            "filename": "test.xlsx",
            "description": "<script>alert(1)</script>",
            "plan": {"operating_economics": config},
            "questions": [],
            "results": {
                "exclusions": [],
                "stages": {
                    "equipment": {"result": {"equipment": []}},
                    "capex": {"result": plain(capex)},
                    "financial": {"result": plain(r["financial"])},
                    "revenue": {"result": plain(r["revenue"])},
                    "opex": {
                        "result": {
                            "operating_detail": plain(r["detail"]),
                            "first_year_lines": plain(first.lines),
                            "first_year_cash_opex": str(first.annual_cash_opex),
                            "first_year_fixed_opex": str(first.cash_fixed),
                            "first_year_variable_opex": str(first.cash_variable),
                        }
                    },
                },
            },
        }
        html = render_study(state)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("Annual financial schedule", html)
        self.assertIn("Equipment utilities", html)
        self.assertIn("7536", html.replace(",", ""))

    def test_revenue_deductions_have_one_cost_owner(self):
        report, config, capex = fixture()
        r = calculate_operating_study(report, DESCRIPTION, config, capex)
        self.assertFalse(
            any(line.id == "garrett:distribution_sales" for line in r["opex"][1].lines)
        )
        self.assertTrue(
            any(
                line.id == "revenue-owned:distribution_sales" and line.amount == 0
                for line in r["opex"][1].lines
            )
        )
        config["sales"][0]["net_freight_deduction_per_unit"] = 0
        r = calculate_operating_study(report, DESCRIPTION, config, capex)
        self.assertTrue(
            any(line.id == "garrett:distribution_sales" for line in r["opex"][1].lines)
        )
