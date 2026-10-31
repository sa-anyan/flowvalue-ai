"""Canonical ownership, alternative replacement, provenance and scenario gates."""

import json
import unittest
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal, localcontext

from backend.opex.cost_register import (
    AnnualConsumption,
    BaseBinding,
    Binding,
    CostRegister,
    EstimateLine,
    EstimateOption,
    Evidence,
    Expense,
    SharedInput,
    affected_expenses,
    calculate_register,
    compare_methods,
    freeze_register,
    register_snapshot_id,
    restore_register,
    review_expense,
    revise_input,
    select_method,
)
from backend.opex.indexes.garrett.model import PLANT_BASE
from backend.opex.models import Basis
from backend.tests.test_opex import BASIS, complete


def evidence(kind="user_assumption"):
    return Evidence(
        kind,
        "Synthetic test evidence",
        "2026-10-30",
        "Test scenario only",
        "Not industrially validated",
        "One annual test case; scope must be reviewed",
    )


def fixture():
    original = complete()
    shared, expenses, bases = [], [], []
    for row in original.assumptions:
        bindings = []
        for field in ("amount", "quantity", "rate"):
            value = getattr(row, field)
            if value is None:
                continue
            key = row.id + "." + field
            kind, unit = (
                ("annual_amount", "GBP/year")
                if field == "amount"
                else ("fraction", "fraction")
            )
            shared.append(
                SharedInput(
                    key,
                    kind,
                    value,
                    unit,
                    evidence(),
                    BASIS if field == "amount" else None,
                )
            )
            bindings.append(Binding(field, key))
        template = replace(row, amount=None, quantity=None, rate=None)
        scopes = (
            ("packaging_storage:packaging", "packaging_storage:storage")
            if row.id == "packaging_storage"
            else row.scopes
        )
        option = EstimateOption(
            "garrett" if row.method == "percentage" else "itemized",
            row.id,
            (EstimateLine(template, tuple(bindings)),),
            (
                evidence(
                    "garrett_allowance"
                    if row.method == "percentage"
                    else "user_assumption"
                ),
            ),
        )
        expenses.append(
            Expense(
                row.id,
                row.id,
                row.category,
                scopes,
                (option,),
                option.id,
                True,
                "Reviewed synthetic category scope",
            )
        )
    for base in original.bases:
        kind, unit = (
            ("annual_amount", "GBP/year")
            if base.id == "annual_revenue"
            else ("capital_amount", "GBP")
        )
        shared.append(SharedInput(base.id, kind, base.amount, unit, evidence(), BASIS))
        bases.append(BaseBinding(base.id, base.id))
    return CostRegister(
        "synthetic",
        BASIS,
        tuple(expenses),
        tuple(shared),
        bases=tuple(bases),
        reviewed_categories=original.reviewed_categories,
    )


def with_packaging_options(register, missing_storage=False):
    old = next(e for e in register.expenses if e.id == "packaging_storage")
    template = replace(
        old.options[0].lines[0].template,
        method="fixed_annual",
        base="",
        scopes=("packaging_storage:packaging",),
        id="packaging_detail",
    )
    lines = (EstimateLine(template, (Binding("amount", "packaging.quote"),)),)
    if not missing_storage:
        lines += (
            EstimateLine(
                replace(
                    template, id="storage_detail", scopes=("packaging_storage:storage",)
                ),
                (Binding("amount", "storage.quote"),),
            ),
        )
    option = EstimateOption(
        "detailed",
        "Packaging and storage quote",
        lines,
        (evidence("supplier_quotation"),),
    )
    replacement = replace(old, options=old.options + (option,))
    return replace(
        register,
        expenses=tuple(replacement if e.id == old.id else e for e in register.expenses),
        inputs=register.inputs
        + (
            SharedInput(
                "packaging.quote",
                "annual_amount",
                1000,
                "GBP/year",
                evidence("supplier_quotation"),
                BASIS,
            ),
            SharedInput(
                "storage.quote",
                "annual_amount",
                500,
                "GBP/year",
                evidence("supplier_quotation"),
                BASIS,
            ),
        ),
    )


def action(register, fn, *args, **kwargs):
    return fn(
        register,
        *args,
        actor="Test reviewer",
        reason="Explicit synthetic scenario decision",
        expected_snapshot_id=register_snapshot_id(register),
        **kwargs,
    )


class CostRegisterTests(unittest.TestCase):
    def test_existing_engine_arithmetic_unchanged_and_lineage_retained(self):
        register = fixture()
        result = calculate_register(register)
        self.assertFalse(result.issues)
        self.assertEqual(result.result.annual_cash_opex, Decimal(594000))
        self.assertIn("raw_materials.amount", json.loads(result.input_lineage_json))
        self.assertIn(
            "Synthetic test evidence", result.inputs.assumptions[0].evidence[0]
        )
        self.assertEqual(len(result.inputs.assumptions), 18)

    def test_inactive_methods_not_added_and_comparisons_do_not_mutate(self):
        register = with_packaging_options(fixture())
        before = freeze_register(register)
        self.assertEqual(
            calculate_register(register).result.annual_cash_opex, Decimal(594000)
        )
        comparisons = {
            c.option_id: c for c in compare_methods(register, "packaging_storage")
        }
        self.assertEqual(comparisons["detailed"].expense_annual_cost, Decimal(1500))
        self.assertEqual(comparisons["detailed"].scenario_cash_opex, Decimal(595500))
        self.assertEqual(comparisons["detailed"].cash_opex_difference, Decimal(1500))
        self.assertEqual(comparisons["detailed"].status, "preview")
        self.assertEqual(freeze_register(register), before)

    def test_method_switch_requires_review_and_preserves_baseline(self):
        baseline = with_packaging_options(fixture())
        changed = action(baseline, select_method, "packaging_storage", "detailed")
        self.assertIsNone(calculate_register(changed).result)
        reviewed = action(changed, review_expense, "packaging_storage")
        self.assertEqual(
            calculate_register(reviewed).result.annual_cash_opex, Decimal(595500)
        )
        self.assertEqual(
            calculate_register(baseline).result.annual_cash_opex, Decimal(594000)
        )
        self.assertEqual(changed.parent_snapshot_id, register_snapshot_id(baseline))
        self.assertEqual(reviewed.revision, baseline.revision + 2)

    def test_packaging_without_storage_cannot_replace_combined_allowance(self):
        register = with_packaging_options(fixture(), missing_storage=True)
        comparison = next(
            c
            for c in compare_methods(register, "packaging_storage")
            if c.option_id == "detailed"
        )
        self.assertIsNone(comparison.expense_annual_cost)
        self.assertTrue(
            any(
                "uncovered scope packaging_storage:storage" in i
                for i in comparison.issues
            )
        )

    def test_unresolved_inactive_price_does_not_block_baseline(self):
        register = with_packaging_options(fixture())
        register = replace(
            register,
            inputs=tuple(
                replace(i, value=None) if i.id == "packaging.quote" else i
                for i in register.inputs
            ),
        )
        self.assertFalse(calculate_register(register).issues)
        comparison = next(
            c
            for c in compare_methods(register, "packaging_storage")
            if c.option_id == "detailed"
        )
        self.assertTrue(
            any("Missing shared input value" in i for i in comparison.issues)
        )
        self.assertIsNone(comparison.scenario_cash_opex)

    def test_one_owner_per_expense_scope(self):
        register = fixture()
        duplicate = replace(register.expenses[0], id="second_feed_cost")
        self.assertTrue(
            any(
                "ownership overlaps" in i
                for i in calculate_register(
                    replace(register, expenses=register.expenses + (duplicate,))
                ).issues
            )
        )

    def test_missing_selection_unknown_method_and_duplicate_options(self):
        register = fixture()
        for selected in (None, "missing"):
            expenses = (
                replace(register.expenses[0], active_option_id=selected),
            ) + register.expenses[1:]
            self.assertTrue(
                any(
                    "select exactly one" in i
                    for i in calculate_register(
                        replace(register, expenses=expenses)
                    ).issues
                )
            )
        expense = register.expenses[0]
        expenses = (replace(expense, options=expense.options * 2),) + register.expenses[
            1:
        ]
        self.assertTrue(
            any(
                "option IDs" in i
                for i in calculate_register(replace(register, expenses=expenses)).issues
            )
        )

    def test_missing_shared_value_reference_duplicate_and_unit_mismatch(self):
        register = fixture()
        key = "utilities.amount"
        for change in (
            {"value": None},
            {"unit": "USD/year"},
            {"kind": "fraction"},
            {"basis": Basis("USD", "1987")},
        ):
            inputs = tuple(
                replace(i, **change) if i.id == key else i for i in register.inputs
            )
            self.assertTrue(calculate_register(replace(register, inputs=inputs)).issues)
        self.assertTrue(
            calculate_register(
                replace(
                    register, inputs=tuple(i for i in register.inputs if i.id != key)
                )
            ).issues
        )
        self.assertTrue(
            any(
                "duplicate shared input" in i
                for i in calculate_register(
                    replace(register, inputs=register.inputs + (register.inputs[0],))
                ).issues
            )
        )

    def test_evidence_dates_types_and_quotes_are_not_verification(self):
        register = fixture()
        source = register.inputs[0]
        for changes in (
            {"kind": "verified"},
            {"as_of": "unknown"},
            {"reference": ""},
            {"applicability": ""},
            {"uncertainty": ""},
        ):
            inputs = (
                replace(source, evidence=replace(source.evidence, **changes)),
            ) + register.inputs[1:]
            self.assertTrue(calculate_register(replace(register, inputs=inputs)).issues)
        self.assertEqual(calculate_register(register).status, "calculated_preliminary")

    def test_no_shadow_numeric_values_or_duplicate_bindings(self):
        register = fixture()
        expense = register.expenses[0]
        option = expense.options[0]
        line = option.lines[0]
        for modified in (
            replace(line, template=replace(line.template, amount=100)),
            replace(line, bindings=line.bindings * 2),
        ):
            replacement = replace(
                expense, options=(replace(option, lines=(modified,)),)
            )
            self.assertTrue(
                calculate_register(
                    replace(register, expenses=(replacement,) + register.expenses[1:])
                ).issues
            )

    def test_annual_consumption_shared_hours_and_tariff(self):
        register = fixture()
        old = next(e for e in register.expenses if e.id == "utilities")
        template = replace(
            old.options[0].lines[0].template,
            method="quantity_price",
            quantity_unit="kWh/year",
            rate_unit="kWh",
        )
        option = EstimateOption(
            "metered",
            "Power demand and hours",
            (
                EstimateLine(
                    template,
                    (Binding("quantity", "annual_power"), Binding("rate", "tariff")),
                ),
            ),
            (evidence("engineering_calculation"),),
        )
        register = replace(
            register,
            expenses=tuple(
                replace(e, options=(option,), active_option_id="metered")
                if e.id == "utilities"
                else e
                for e in register.expenses
            ),
            inputs=register.inputs
            + (
                SharedInput("power", "demand", 100, "kW", evidence()),
                SharedInput("hours", "hours", 8000, "h/year", evidence()),
                SharedInput("tariff", "unit_price", ".1", "kWh", evidence(), BASIS),
            ),
            annual_consumption=(
                AnnualConsumption(
                    "annual_power",
                    "power",
                    "hours",
                    "kWh/year",
                    evidence("engineering_calculation"),
                ),
            ),
        )
        result = calculate_register(register)
        self.assertFalse(result.issues)
        self.assertEqual(result.result.annual_cash_opex, Decimal(624000))
        self.assertEqual(affected_expenses(register, "hours"), ("utilities",))
        tariff = next(i for i in register.inputs if i.id == "tariff")
        updated = action(register, revise_input, replace(tariff, value=".2"))
        self.assertTrue(calculate_register(updated).issues)
        self.assertTrue(
            next(e for e in updated.expenses if e.id == "operating_labor").reviewed
        )
        reviewed = action(updated, review_expense, "utilities")
        self.assertEqual(
            calculate_register(reviewed).result.annual_cash_opex, Decimal(704000)
        )
        bad = replace(
            register,
            inputs=tuple(
                replace(i, value="9000") if i.id == "hours" else i
                for i in register.inputs
            ),
        )
        self.assertTrue(calculate_register(bad).issues)
        cycle = replace(
            register,
            annual_consumption=(
                replace(register.annual_consumption[0], demand_id="annual_power"),
            ),
        )
        self.assertTrue(any("Circular" in i for i in calculate_register(cycle).issues))

    def test_shared_labor_change_invalidates_related_factor_reviews(self):
        register = fixture()
        self.assertEqual(
            set(affected_expenses(register, "operating_labor.amount")),
            {"operating_labor", "payroll_overhead", "supervision", "laboratory"},
        )
        source = next(i for i in register.inputs if i.id == "operating_labor.amount")
        changed = action(register, revise_input, replace(source, value="250000"))
        self.assertFalse(
            next(e for e in changed.expenses if e.id == "laboratory").reviewed
        )
        self.assertTrue(
            next(e for e in changed.expenses if e.id == "maintenance").reviewed
        )

    def test_labor_method_change_recalculates_dependencies_and_invalidates_reviews(
        self,
    ):
        register = fixture()
        labor = next(e for e in register.expenses if e.id == "operating_labor")
        line = labor.options[0].lines[0]
        replacement = EstimateOption(
            "alternative",
            "Revised labor estimate",
            (replace(line, bindings=(Binding("amount", "labor.quote"),)),),
            (evidence(),),
        )
        register = replace(
            register,
            expenses=tuple(
                replace(e, options=e.options + (replacement,))
                if e.id == labor.id
                else e
                for e in register.expenses
            ),
            inputs=register.inputs
            + (
                SharedInput(
                    "labor.quote",
                    "annual_amount",
                    250000,
                    "GBP/year",
                    evidence(),
                    BASIS,
                ),
            ),
        )
        comparison = next(
            c
            for c in compare_methods(register, labor.id)
            if c.option_id == "alternative"
        )
        self.assertEqual(comparison.cash_opex_difference, Decimal(71000))
        changed = action(register, select_method, labor.id, "alternative")
        for key in ("operating_labor", "payroll_overhead", "supervision", "laboratory"):
            self.assertFalse(next(e for e in changed.expenses if e.id == key).reviewed)
            changed = action(changed, review_expense, key)
        self.assertEqual(
            calculate_register(changed).result.annual_cash_opex, Decimal(665000)
        )

    def test_initial_capital_does_not_replace_annual_expense_coverage(self):
        register = fixture()
        expense = register.expenses[0]
        option = expense.options[0]
        line = option.lines[0]
        expense = replace(
            expense,
            options=(
                replace(
                    option,
                    lines=(
                        replace(line, template=replace(line.template, scope="capex")),
                    ),
                ),
            ),
        )
        result = calculate_register(
            replace(register, expenses=(expense,) + register.expenses[1:])
        )
        self.assertTrue(any("recurring coverage" in issue for issue in result.issues))

    def test_freeze_restore_hash_determinism_and_stale_revision(self):
        register = with_packaging_options(fixture())
        self.assertEqual(restore_register(freeze_register(register)), register)
        with localcontext() as context:
            context.prec = 3
            self.assertEqual(
                calculate_register(register),
                calculate_register(restore_register(freeze_register(register))),
            )
        with self.assertRaises(ValueError):
            select_method(
                register,
                "packaging_storage",
                "detailed",
                actor="reviewer",
                reason="test",
                expected_snapshot_id="stale",
            )
        with self.assertRaises(FrozenInstanceError):
            register.expenses[0].reviewed = False
        payload = json.loads(freeze_register(register))
        payload["schema_version"] = 2
        with self.assertRaises(ValueError):
            restore_register(json.dumps(payload))

    def test_named_base_kind_validation_and_engine_exclusions_still_apply(self):
        register = fixture()
        wrong = replace(register, bases=(BaseBinding(PLANT_BASE, "annual_revenue"),))
        self.assertTrue(
            any("monetary base" in i for i in calculate_register(wrong).issues)
        )
        no_review = replace(register, reviewed_categories=())
        self.assertTrue(
            any("completeness" in i for i in calculate_register(no_review).issues)
        )

    def test_unused_bases_do_not_require_prices_but_duplicate_bindings_are_rejected(
        self,
    ):
        register = fixture()
        register = replace(
            register,
            bases=register.bases
            + (BaseBinding("installed_equipment", "not_entered_yet"),),
        )
        self.assertFalse(calculate_register(register).issues)
        duplicate = replace(register, bases=register.bases + (register.bases[0],))
        self.assertTrue(
            any(
                "Duplicate canonical base" in i
                for i in calculate_register(duplicate).issues
            )
        )


if __name__ == "__main__":
    unittest.main()
