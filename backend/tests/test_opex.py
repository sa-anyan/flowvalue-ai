"""Source parameters plus independent arithmetic and failure-mode tests."""

import unittest
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal, localcontext

from backend.capex.models import CapexResult
from backend.opex import calculate_opex, get_factor_ranges, get_model, list_models
from backend.opex.advisor import DraftProposal, validate_proposal
from backend.opex.connectors import financial_handoff, prepare_opex_inputs
from backend.opex.engineering import (
    annual_interest,
    annual_power_cost,
    straight_line_depreciation,
)
from backend.opex.indexes.garrett.model import CATEGORIES, PLANT_BASE, SOURCE
from backend.opex.indexes.legacy_reference import REFERENCE
from backend.opex.models import (
    Assumption,
    Basis,
    Exclusion,
    MoneyBase,
    OpexInputs,
    freeze_assumptions,
    restore_assumptions,
    scenario,
)

D = Decimal
BASIS = Basis("GBP", "2026 annual prices")


def assumption(key, category=None, method="fixed_annual", **changes):
    values = {
        "id": key,
        "category": category or key,
        "method": method,
        "behavior": "fixed",
        "basis": BASIS,
        "rationale": "Explicit synthetic test assumption",
        "source": "Synthetic fixture, not industrial evidence",
        "uncertainty": "Unvalidated test data",
        "scopes": (category or key,),
    }
    values.update(changes)
    return Assumption(**values)


def complete(edge="minimum"):
    itemized = {
        "raw_materials": "100000",
        "utilities": "50000",
        "operating_labor": "200000",
        "interest": "1000",
    }
    rows = []
    for definition in CATEGORIES:
        if not definition.required:
            continue
        if definition.id in itemized:
            rows.append(
                assumption(
                    definition.id,
                    amount=itemized[definition.id],
                    behavior="variable"
                    if definition.id in ("raw_materials", "utilities")
                    else "fixed",
                )
            )
        else:
            rows.append(
                assumption(
                    definition.id,
                    method="percentage",
                    rate=getattr(definition, edge),
                    base=definition.base,
                )
            )
    return OpexInputs(
        BASIS,
        tuple(rows),
        (
            MoneyBase(
                PLANT_BASE,
                "1000000",
                BASIS,
                "Canonical test capital including startup/offsite, excluding WC",
            ),
            MoneyBase("annual_revenue", "2000000", BASIS, "Test sales"),
        ),
        reviewed_categories=tuple(c.id for c in CATEGORIES if c.required),
    )


def changed(inputs, key, **changes):
    return replace(
        inputs,
        assumptions=tuple(
            replace(a, **changes) if a.id == key else a for a in inputs.assumptions
        ),
    )


class GarrettOpexTests(unittest.TestCase):
    def test_source_ranges_and_exact_bases(self):
        # Independently transcribed after visual inspection of printed p.52/PDF64.
        expected = {
            "payroll_overhead": (".22", ".45", "category:operating_labor"),
            "supervision": (".10", ".30", "category:operating_labor"),
            "laboratory": (".10", ".20", "category:operating_labor"),
            "maintenance": (".02", ".10", PLANT_BASE),
            "operating_supplies": (".005", ".03", PLANT_BASE),
            "environmental": (".005", ".05", PLANT_BASE),
            "depreciation": (".05", ".10", PLANT_BASE),
            "taxes_insurance": (".03", ".05", PLANT_BASE),
            "plant_overhead": (".01", ".05", PLANT_BASE),
            "royalties": ("0", ".05", "annual_revenue"),
            "packaging_storage": ("0", ".07", "annual_revenue"),
            "administration": (".02", ".10", "annual_revenue"),
            "distribution_sales": (".02", ".10", "annual_revenue"),
            "research_development": (".005", ".04", "annual_revenue"),
        }
        factors = {f["id"]: f for f in get_factor_ranges()}
        self.assertEqual(len(factors), 19)
        for key, values in expected.items():
            self.assertEqual(
                tuple(factors[key][v] for v in ("minimum", "maximum", "base")), values
            )
        self.assertEqual((SOURCE.printed_page, SOURCE.pdf_page), (52, 64))
        self.assertEqual(
            SOURCE.sha256,
            "fe1084a476baece3a8afd4711311780b314b08ca085dbcb766f193903bfe3eff",
        )
        self.assertIn("prose", factors["research_development"]["note"])

    def test_minimum_full_structure_independent_total(self):
        result = calculate_opex(inputs=complete())
        self.assertEqual(result.issues, ())
        self.assertEqual(result.status, "calculated_preliminary")
        self.assertEqual(result.annual_cash_opex, D("594000"))
        self.assertEqual(result.cash_variable, D("150000"))
        self.assertEqual(result.cash_fixed, D("444000"))
        self.assertEqual(result.depreciation, D("50000"))
        self.assertEqual(result.financing, D("1000"))
        self.assertEqual(
            result.annual_expense_including_depreciation_and_financing, D("645000")
        )
        self.assertEqual(len(result.lines), 18)
        self.assertEqual(result.methodology_source, SOURCE)
        payroll = next(r for r in result.lines if r.id == "payroll_overhead")
        self.assertEqual((payroll.rate, payroll.base_amount), (D(".22"), D("200000")))

    def test_maximum_full_structure_no_group_double_charge(self):
        result = calculate_opex(inputs=complete("maximum"))
        self.assertEqual(result.issues, ())
        # Individual printed sales maxima sum to 36%, despite the table's 37%
        # group check. Calculate the rows, never silently force the group total.
        self.assertEqual(result.annual_cash_opex, D("1540000"))
        self.assertEqual(
            result.annual_expense_including_depreciation_and_financing, D("1641000")
        )

    def test_selected_factors_and_all_boundaries(self):
        inputs = complete()
        result = calculate_opex(inputs=changed(inputs, "maintenance", rate=".06"))
        self.assertEqual(result.annual_cash_opex, D("634000"))
        for row in inputs.assumptions:
            if row.method != "percentage":
                continue
            definition = next(c for c in CATEGORIES if c.id == row.category)
            for rate in (D(definition.minimum), D(definition.maximum)):
                self.assertFalse(
                    calculate_opex(inputs=changed(inputs, row.id, rate=rate)).issues
                )
            invalid = calculate_opex(
                inputs=changed(inputs, row.id, rate=D(definition.maximum) + D(".001"))
            )
            self.assertIsNone(invalid.annual_cash_opex)
            if D(definition.minimum) > 0:
                self.assertTrue(
                    calculate_opex(inputs=changed(inputs, row.id, rate="0")).issues
                )

    def test_wrong_capital_base_requires_explicit_override(self):
        inputs = replace(
            complete(),
            bases=complete().bases
            + (
                MoneyBase(
                    "fixed_capital",
                    "900000",
                    BASIS,
                    "Test fixed capital excluding startup",
                ),
            ),
        )
        invalid = changed(inputs, "maintenance", base="fixed_capital")
        self.assertTrue(calculate_opex(inputs=invalid).issues)
        allowed = changed(
            invalid,
            "maintenance",
            override=True,
            override_reason="Site-specific maintenance contract",
        )
        result = calculate_opex(inputs=allowed)
        self.assertFalse(result.issues)
        self.assertEqual(
            next(r.base_amount for r in result.lines if r.id == "maintenance"),
            D("900000"),
        )
        self.assertTrue(any("override" in s for s in result.warnings))

    def test_no_default_factors_or_missing_costs_as_zero(self):
        result = calculate_opex(inputs=OpexInputs(BASIS))
        self.assertIsNone(result.annual_cash_opex)
        self.assertEqual(len(result.issues), 18)
        self.assertEqual(result.resolved_cash_subtotal, 0)

    def test_explicit_exclusions_and_conflicts(self):
        inputs = complete()
        inputs = replace(
            inputs,
            assumptions=tuple(
                a for a in inputs.assumptions if a.category == "utilities"
            ),
            exclusions=tuple(
                Exclusion(c.id, "Explicit synthetic not-applicable decision")
                for c in CATEGORIES
                if c.required and c.id != "utilities"
            ),
        )
        self.assertEqual(calculate_opex(inputs=inputs).annual_cash_opex, D("50000"))
        invalid = replace(
            inputs,
            exclusions=inputs.exclusions + (Exclusion("utilities", "Contradictory"),),
        )
        self.assertTrue(calculate_opex(inputs=invalid).issues)
        invalid = replace(
            inputs, exclusions=inputs.exclusions + (Exclusion("missing", ""),)
        )
        self.assertTrue(calculate_opex(inputs=invalid).issues)

    def test_category_completeness_must_be_reviewed(self):
        self.assertTrue(
            calculate_opex(inputs=replace(complete(), reviewed_categories=())).issues
        )

    def test_quantity_price_and_headcount_salary(self):
        inputs = changed(
            complete(),
            "raw_materials",
            method="quantity_price",
            amount=None,
            quantity="500",
            rate="200",
            quantity_unit="kg/year",
            rate_unit="kg",
        )
        inputs = changed(
            inputs,
            "operating_labor",
            method="headcount_salary",
            amount=None,
            quantity="4",
            rate="50000",
            quantity_unit="FTE",
            rate_unit="FTE/year",
        )
        result = calculate_opex(inputs=inputs)
        self.assertFalse(result.issues)
        self.assertEqual(result.annual_cash_opex, D("594000"))

    def test_incompatible_quantity_units_blocked(self):
        inputs = changed(
            complete(),
            "utilities",
            method="quantity_price",
            amount=None,
            quantity="1",
            rate="1",
            quantity_unit="MWh/year",
            rate_unit="kWh",
        )
        self.assertTrue(calculate_opex(inputs=inputs).issues)

    def test_multiple_detailed_lines_and_factor_replacement(self):
        inputs = complete()
        other = assumption(
            "steam", "utilities", amount="1000", scopes=("utilities:steam",)
        )
        inputs = changed(inputs, "utilities", scopes=("utilities:electricity",))
        result = calculate_opex(
            inputs=replace(inputs, assumptions=inputs.assumptions + (other,))
        )
        self.assertFalse(result.issues)
        self.assertEqual(result.annual_cash_opex, D("595000"))
        overlap = assumption(
            "extra_maintenance",
            "maintenance",
            amount="5",
            scopes=("maintenance:labor",),
        )
        self.assertTrue(
            calculate_opex(
                inputs=replace(inputs, assumptions=inputs.assumptions + (overlap,))
            ).issues
        )

    def test_loaded_salary_and_maintenance_labor_overlap(self):
        inputs = changed(
            complete(),
            "operating_labor",
            scopes=("operating_labor", "payroll_overhead"),
        )
        result = calculate_opex(inputs=inputs)
        self.assertTrue(any("Overlapping" in s for s in result.issues))
        self.assertTrue(any("clean operating-labor-only" in s for s in result.issues))
        inputs = changed(
            complete(),
            "supervision",
            method="headcount_salary",
            amount=None,
            rate="10000",
            quantity="2",
            quantity_unit="FTE",
            rate_unit="FTE/year",
            base="",
            scopes=("supervision", "maintenance:staff"),
        )
        self.assertTrue(
            any("Overlapping" in s for s in calculate_opex(inputs=inputs).issues)
        )

    def test_percentage_component_dependency(self):
        inputs = complete()
        fee = assumption(
            "fee",
            "other_manufacturing",
            method="percentage",
            rate=".1",
            base="item:utilities",
            override=True,
            override_reason="Test fee contract",
            scopes=("other_manufacturing",),
        )
        inputs = replace(
            inputs,
            assumptions=inputs.assumptions + (fee,),
            reviewed_categories=inputs.reviewed_categories + ("other_manufacturing",),
        )
        self.assertEqual(calculate_opex(inputs=inputs).annual_cash_opex, D("599000"))

    def test_cycle_and_missing_dependencies(self):
        inputs = changed(
            complete(),
            "raw_materials",
            method="percentage",
            amount=None,
            rate=".1",
            base="item:utilities",
            override=True,
            override_reason="Synthetic dependency",
        )
        inputs = changed(
            inputs,
            "utilities",
            method="percentage",
            amount=None,
            rate=".1",
            base="item:raw_materials",
            override=True,
            override_reason="Synthetic dependency",
        )
        self.assertTrue(
            any("Circular" in s for s in calculate_opex(inputs=inputs).issues)
        )
        self.assertTrue(
            any(
                "Missing" in s
                for s in calculate_opex(
                    inputs=changed(inputs, "utilities", base="item:absent")
                ).issues
            )
        )
        self.assertTrue(
            any(
                "Circular" in s
                for s in calculate_opex(
                    inputs=changed(
                        inputs, "raw_materials", base="category:raw_materials"
                    )
                ).issues
            )
        )

    def test_capital_wc_do_not_enter_cash_opex(self):
        inputs = complete()
        capital = assumption(
            "initial_catalyst", "raw_materials", amount="10000", scope="capex"
        )
        inventory = assumption(
            "stock", "raw_materials", amount="20000", scope="working_capital"
        )
        result = calculate_opex(
            inputs=replace(
                inputs, assumptions=inputs.assumptions + (capital, inventory)
            )
        )
        self.assertEqual(result.annual_cash_opex, D("594000"))
        self.assertEqual(
            (result.excluded_capital, result.excluded_working_capital),
            (D("10000"), D("20000")),
        )
        self.assertTrue(
            calculate_opex(
                inputs=changed(inputs, "raw_materials", scope="capex")
            ).issues
        )

    def test_unsupported_numerical_inputs(self):
        for value in (True, "NaN", "Infinity", "-1", "bad"):
            with self.assertRaises((TypeError, ValueError)):
                assumption("utilities", amount=value)
        for field, value in (
            ("amount", None),
            ("behavior", "mixed"),
            ("method", "guess"),
            ("source", ""),
            ("uncertainty", ""),
        ):
            self.assertTrue(
                calculate_opex(
                    inputs=changed(complete(), "utilities", **{field: value})
                ).issues
            )

    def test_duplicate_ids_and_bases(self):
        inputs = complete()
        self.assertTrue(
            calculate_opex(
                inputs=replace(
                    inputs, assumptions=inputs.assumptions + (inputs.assumptions[0],)
                )
            ).issues
        )
        self.assertTrue(
            calculate_opex(
                inputs=replace(inputs, bases=inputs.bases + (inputs.bases[0],))
            ).issues
        )

    def test_currency_and_price_period_no_implicit_escalation(self):
        for basis in (Basis("USD", BASIS.price_period), Basis("GBP", "1987")):
            self.assertTrue(
                calculate_opex(
                    inputs=changed(complete(), "utilities", basis=basis)
                ).issues
            )
            inputs = complete()
            self.assertTrue(
                calculate_opex(
                    inputs=replace(
                        inputs,
                        bases=(replace(inputs.bases[0], basis=basis), inputs.bases[1]),
                    )
                ).issues
            )

    def test_freeze_restore_scenario_and_decimal_context(self):
        inputs = complete()
        snapshot = freeze_assumptions(inputs)
        restored = restore_assumptions(snapshot)
        self.assertEqual(inputs, restored)
        baseline = calculate_opex(inputs=inputs)
        with localcontext() as context:
            context.prec = 3
            self.assertEqual(calculate_opex(inputs=restored), baseline)
        varied = scenario(
            inputs, assumptions=changed(inputs, "utilities", amount="75000").assumptions
        )
        self.assertEqual(calculate_opex(inputs=varied).annual_cash_opex, D("619000"))
        self.assertEqual(freeze_assumptions(inputs), snapshot)
        self.assertNotEqual(
            calculate_opex(inputs=varied).snapshot_id, baseline.snapshot_id
        )
        with self.assertRaises(FrozenInstanceError):
            inputs.assumptions[0].amount = D(1)
        with self.assertRaises(TypeError):
            replace(inputs, assumptions=list(inputs.assumptions))

    def test_market_and_engineering_evidence(self):
        for method in ("engineering", "market_price"):
            inputs = changed(complete(), "utilities", method=method)
            self.assertTrue(calculate_opex(inputs=inputs).issues)
            inputs = changed(
                inputs,
                "utilities",
                evidence=("Synthetic metered annual load and test tariff",),
                engineering_formula="annual_kWh × price_per_kWh",
            )
            self.assertFalse(calculate_opex(inputs=inputs).issues)

    def test_registry_independence_and_legacy_not_default(self):
        self.assertEqual(list_models()[0]["id"], "garrett")
        model = get_model()
        model["id"] = "tampered"
        self.assertEqual(get_model()["id"], "garrett")
        self.assertEqual(REFERENCE["worksheet"], "Opex")
        for method in ("legacy", "nottingham", None):
            with self.assertRaises(ValueError):
                get_model(method)
        with self.assertRaises(ValueError):
            get_factor_ranges(process_type="solids")
        with self.assertRaises(TypeError):
            calculate_opex(inputs={})

    def test_engineering_helpers(self):
        self.assertEqual(
            annual_power_cost(
                electrical_input_kw="100", operating_hours="8000", price_per_kwh=".1"
            ),
            D("80000"),
        )
        self.assertEqual(
            annual_interest(outstanding_principal="10000", annual_rate=".05"), D("500")
        )
        self.assertEqual(
            straight_line_depreciation(
                depreciable_asset_cost="1100",
                salvage_value="100",
                life_years=10,
                operating_year=1,
            ),
            D("100"),
        )
        self.assertEqual(
            straight_line_depreciation(
                depreciable_asset_cost="1100",
                salvage_value="100",
                life_years=10,
                operating_year=11,
            ),
            0,
        )
        with self.assertRaises(ValueError):
            annual_power_cost(
                electrical_input_kw=1, operating_hours=9000, price_per_kwh=1
            )
        with self.assertRaises(ValueError):
            straight_line_depreciation(
                depreciable_asset_cost=1,
                salvage_value=2,
                life_years=10,
                operating_year=1,
            )

    def test_canonical_capex_adapter_excludes_wc(self):
        capex = CapexResult(
            "garrett",
            "fluids",
            "provisional",
            D("100"),
            D("200"),
            D("50"),
            D("250"),
            D("300"),
            D("20"),
            D("1000"),
            D("1320"),
            "GBP",
            BASIS.price_period,
            "CEPCI",
            D("800"),
            (),
            (),
            (),
            {},
        )
        inputs = prepare_opex_inputs(
            capex,
            annual_revenue="2000",
            revenue_source="Test revenue",
            engineering_context={"streams": [{"source_cell": "Balance!C4"}]},
        )
        bases = {b.id: b.amount for b in inputs.bases}
        self.assertEqual(bases[PLANT_BASE], D("320"))
        self.assertEqual(bases["fixed_capital"], D("300"))
        self.assertNotIn("total_capex", bases)
        self.assertIn("Balance!C4", inputs.engineering_context_json)
        with self.assertRaises(ValueError):
            prepare_opex_inputs(replace(capex, issues=("Incomplete",)))
        with self.assertRaises(ValueError):
            prepare_opex_inputs(capex, annual_revenue="2000")

    def test_financial_handoff_and_draft_advisor(self):
        result = calculate_opex(inputs=complete())
        handoff = financial_handoff(result)
        self.assertEqual(handoff["annual_cash_opex"], D("594000"))
        self.assertEqual(handoff["annual_depreciation_separate"], D("50000"))
        with self.assertRaises(ValueError):
            financial_handoff(calculate_opex(inputs=OpexInputs(BASIS)))
        draft = DraftProposal(
            "garrett", complete().assumptions, (), (), "Test process evidence"
        )
        self.assertEqual(validate_proposal(draft, complete()), ())
        self.assertTrue(
            validate_proposal(replace(draft, classification_rationale=""), complete())
        )


if __name__ == "__main__":
    unittest.main()
