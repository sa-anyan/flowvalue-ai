"""Independent finance cases and full upstream-to-ledger integration checks."""

import json
import tempfile
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import date
from decimal import Decimal as D
from decimal import localcontext
from pathlib import Path

from backend.financial_modelling import (
    calculate_financials,
    freeze_inputs,
    restore_inputs,
    save_assessment,
    snapshot_id,
)
from backend.financial_modelling.connectors.calculator import prepare_financial_inputs
from backend.financial_modelling.connectors.capex.interface import capital_from_result
from backend.financial_modelling.connectors.interface import operations_from_results
from backend.financial_modelling.connectors.playground.interface import (
    recalculate_scenario,
)
from backend.financial_modelling.depreciation.calculator import asset_schedule
from backend.financial_modelling.financial_schedules.calculator import build_timeline
from backend.financial_modelling.investment_metrics.irr.calculator import irr
from backend.financial_modelling.investment_metrics.mirr.calculator import mirr
from backend.financial_modelling.investment_metrics.npv.calculator import npv
from backend.financial_modelling.investment_metrics.payback.calculator import payback
from backend.financial_modelling.models import (
    Activity,
    CapitalItem,
    DatedMoney,
    DebtPlan,
    DepreciationPolicy,
    ExchangeRate,
    FinancialAssumptions,
    FinancialInputs,
    Money,
    OperatingCost,
    Operation,
    ProductSales,
    Spend,
    TaxPolicy,
    WorkingCapitalPlan,
)
from backend.financial_modelling.production_sales.calculator import (
    revenue_with_operating_plan,
)
from backend.financial_modelling.production_sales.models import ProductionPlan
from backend.financial_modelling.taxation.calculator import calculate_tax
from backend.revenue.models import Assumption


def p(value, unit="fraction"):
    return Assumption(
        value,
        unit,
        "Independent synthetic fixture; not an industrial assumption",
        "Synthetic test",
        "Unvalidated example",
        "user_assumption",
        "2026-10-30",
    )


def money(value, currency="GBP", price_year=2027):
    return Money(value, currency, price_year, "Independent synthetic fixture")


def fixture(construction=0, life=2, revenue=80, tax=".25"):
    start = date(2027, 1, 1)
    first = date(2027 + construction, 1, 1)
    horizon = construction + life
    policy = DepreciationPolicy(
        "straight_line",
        construction + 1,
        life,
        p(1),
        money(0),
        None,
        False,
        (),
        "Synthetic straight-line convention",
        "Generic annual full-year test, not jurisdictional law",
    )
    spend = (
        (Spend(0, p(1)),)
        if not construction
        else tuple(
            Spend(y, p(str(D(1) / construction))) for y in range(1, construction + 1)
        )
    )
    if construction == 3:
        spend = (Spend(1, p(".3")), Spend(2, p(".6")), Spend(3, p(".1")))
    asset = CapitalItem(
        "plant",
        "direct",
        money(100),
        spend,
        policy,
        horizon,
        money(0),
        "capitalized",
        "actual",
    )
    taxpolicy = TaxPolicy(
        "Explicit synthetic jurisdiction",
        tuple((y, p(tax)) for y in range(horizon + 1)),
        True,
        None,
        p(1),
        True,
        True,
        True,
        p(0),
        "Synthetic policy; no country-specific claim",
    )
    wc = WorkingCapitalPlan(
        (DatedMoney(construction, money(10)),),
        horizon,
        p(1),
        "Explicit synthetic balance",
    )
    debt = DebtPlan(
        (),
        p(".1", "fraction/year"),
        construction + 1,
        life,
        "equal_principal",
        "end",
        False,
        "residual_equity",
        (),
        "No debt synthetic case",
    )
    assumptions = FinancialAssumptions(
        start,
        construction,
        first,
        first,
        life,
        "GBP",
        2027,
        "real",
        p(0, "fraction/year"),
        p(".1", "fraction/year"),
        p(".1", "fraction/year"),
        "discrete_end",
        p(".1", "fraction/year"),
        p(".1", "fraction/year"),
        (),
        taxpolicy,
        wc,
        debt,
        money(0),
        "Synthetic independent fixture",
    )
    operations = tuple(
        Operation(
            y,
            (
                ProductSales(
                    "product",
                    "kg",
                    100,
                    100,
                    80,
                    money(revenue),
                    "Synthetic sales; not equal to production",
                ),
            ),
            (
                OperatingCost(
                    "fixed",
                    "labor",
                    "fixed",
                    "sga",
                    money(20),
                    "actual",
                    "",
                    None,
                    "",
                    "actual",
                ),
                OperatingCost(
                    "variable",
                    "feed",
                    "variable",
                    "cogs",
                    money(10),
                    "actual",
                    "",
                    None,
                    "",
                    "actual",
                ),
            ),
            (
                Activity(
                    "product:produced",
                    100,
                    "kg/year",
                    "Synthetic physical annual quantity",
                ),
            ),
            "Synthetic operation",
        )
        for y in range(construction + 1, horizon + 1)
    )
    return FinancialInputs(
        "independent",
        assumptions,
        (asset,),
        operations,
        source_references=("Independent arithmetic fixture",),
    )


def metric(result, name):
    return dict(result.metrics)[name]


class FinancialTests(unittest.TestCase):
    def test_independent_unlevered_cash_and_metrics(self):
        result = calculate_financials(fixture())
        self.assertFalse(result.issues, result.issues)
        self.assertEqual(tuple(r.fcff for r in result.ledger), (D(-110), D(50), D(60)))
        self.assertEqual(tuple(r.fcfe for r in result.ledger), (D(-110), D(50), D(60)))
        self.assertAlmostEqual(
            metric(result, "project_npv").value,
            D(-110) + D(50) / D("1.1") + D(60) / D("1.21"),
            places=20,
        )
        self.assertAlmostEqual(metric(result, "project_irr").value, D(0), places=8)
        self.assertEqual(metric(result, "project_payback").value, D(2))
        self.assertEqual(result.ledger[1].depreciation, D(50))
        self.assertEqual(result.ledger[1].gross_profit, D(70))
        self.assertEqual(result.ledger[1].net_income, D(0))
        self.assertTrue(all(abs(r.closing_cash) < D("1e-20") for r in result.ledger))

    def test_multi_year_construction_three_years_then_production(self):
        result = calculate_financials(fixture(construction=3))
        self.assertFalse(result.issues, result.issues)
        self.assertEqual(
            tuple(r.capex for r in result.ledger),
            (D(0), D(30), D(60), D(10), D(0), D(0)),
        )
        self.assertTrue(all(r.revenue == 0 for r in result.ledger[:4]))
        self.assertEqual(result.ledger[4].revenue, D(80))
        bad = fixture(construction=3)
        bad = replace(
            bad, capital=(replace(bad.capital[0], spend=(Spend(1, p(".9")),)),)
        )
        self.assertEqual(calculate_financials(bad).status, "needs_review")

    def test_financing_tax_shield_and_project_independence(self):
        base = fixture(revenue=120)
        loan = replace(
            base.assumptions.debt,
            draws=(DatedMoney(0, money(60)),),
            source="Synthetic term debt",
        )
        result = calculate_financials(
            replace(base, assumptions=replace(base.assumptions, debt=loan))
        )
        expected = calculate_financials(base)
        self.assertFalse(result.issues, result.issues)
        self.assertEqual(
            tuple(r.fcff for r in result.ledger), tuple(r.fcff for r in expected.ledger)
        )
        self.assertEqual(
            tuple(r.fcfe for r in result.ledger), (D(-50), D("45.5"), D("57.75"))
        )
        self.assertEqual(
            tuple(r.debt.interest for r in result.ledger), (D(0), D(6), D(3))
        )
        self.assertEqual(result.ledger[1].income_tax, D("8.5"))
        self.assertEqual(result.ledger[1].project_tax, D(10))
        self.assertEqual(result.ledger[-1].debt.closing, 0)
        self.assertNotEqual(
            metric(result, "project_irr").value, metric(result, "equity_irr").value
        )

    def test_debt_grace_construction_interest_and_annuity(self):
        base = fixture(construction=2, life=3, revenue=120)
        debt = replace(
            base.assumptions.debt,
            draws=(DatedMoney(1, money(60)),),
            repayment_start_year=3,
            repayment_years=3,
            method="annuity",
            draw_timing="beginning",
        )
        result = calculate_financials(
            replace(base, assumptions=replace(base.assumptions, debt=debt))
        )
        self.assertFalse(result.issues, result.issues)
        self.assertEqual(result.ledger[1].debt.interest, D(6))
        self.assertEqual(result.ledger[2].debt.principal, 0)
        self.assertAlmostEqual(
            sum((r.debt.principal for r in result.ledger), D(0)), D(60), places=20
        )
        self.assertTrue(result.ledger[1].equity_loss_carry > 0)

    def test_balloon_and_insufficient_equity(self):
        base = fixture()
        debt = replace(
            base.assumptions.debt, draws=(DatedMoney(0, money(60)),), repayment_years=5
        )
        self.assertTrue(
            calculate_financials(
                replace(base, assumptions=replace(base.assumptions, debt=debt))
            ).issues
        )
        debt = replace(debt, balloon_at_shutdown=True)
        self.assertFalse(
            calculate_financials(
                replace(base, assumptions=replace(base.assumptions, debt=debt))
            ).issues
        )
        debt = replace(base.assumptions.debt, equity_mode="specified_equity")
        self.assertTrue(
            calculate_financials(
                replace(base, assumptions=replace(base.assumptions, debt=debt))
            ).issues
        )
        debt = replace(debt, equity_contributions=(DatedMoney(0, money(110)),))
        self.assertFalse(
            calculate_financials(
                replace(base, assumptions=replace(base.assumptions, debt=debt))
            ).issues
        )

    def test_working_capital_changes_partial_recovery(self):
        base = fixture()
        wc = replace(
            base.assumptions.working_capital,
            requirements=(DatedMoney(0, money(10)), DatedMoney(1, money(15))),
            recovery_fraction=p(".5"),
        )
        result = calculate_financials(
            replace(base, assumptions=replace(base.assumptions, working_capital=wc))
        )
        self.assertFalse(result.issues, result.issues)
        self.assertEqual(result.ledger[1].working_capital_change, D(5))
        self.assertEqual(result.ledger[-1].working_capital_recovery, D("7.5"))
        self.assertEqual(result.ledger[-1].working_capital_closing, D("7.5"))

    def test_loss_carry_expiry_offsets_and_no_refund(self):
        loss = calculate_tax(D(-100), (), 1, D(".25"), True, D(".8"), 1)
        self.assertEqual(loss.tax, 0)
        use = calculate_tax(D(50), loss.carry_lots, 2, D(".25"), True, D(".8"), 1)
        self.assertEqual(use.losses_used, D(40))
        self.assertEqual(use.tax, D("2.5"))
        expired = calculate_tax(D(50), use.carry_lots, 3, D(".25"), True, D(1), 1)
        self.assertEqual(expired.tax, D("12.5"))

    def test_depreciation_methods_non_depreciable_and_replacement(self):
        base = fixture(life=3)
        periods = build_timeline(base.assumptions)
        item = base.capital[0]
        for method in ("straight_line", "declining_balance", "macrs"):
            policy = replace(
                item.depreciation,
                method=method,
                declining_factor=p(2, "factor")
                if method == "declining_balance"
                else None,
                switch_to_straight_line=True,
                macrs_rates=tuple(p(r) for r in (".4", ".35", ".25"))
                if method == "macrs"
                else (),
            )
            schedule, book = asset_schedule(
                replace(item, depreciation=policy), D(100), periods, base.assumptions
            )
            self.assertEqual(sum(schedule.values(), D(0)), D(100))
            self.assertEqual(book, 0)
        land = replace(
            item,
            id="land",
            depreciation=replace(
                item.depreciation, method="none", depreciable_fraction=p(0)
            ),
        )
        schedule, book = asset_schedule(land, D(100), periods, base.assumptions)
        self.assertEqual(sum(schedule.values(), D(0)), 0)
        self.assertEqual(book, 100)
        replacement = replace(
            item,
            id="replacement",
            kind="replacement",
            amount=money(20),
            spend=(Spend(2, p(1)),),
            depreciation=replace(item.depreciation, service_year=2, life=2),
            disposal_year=3,
        )
        result = calculate_financials(
            replace(base, capital=base.capital + (replacement,))
        )
        self.assertFalse(result.issues, result.issues)
        self.assertEqual(result.ledger[2].capex, D(20))

    def test_disposal_gain_closure_and_tax_policy(self):
        base = fixture(revenue=120)
        asset = replace(base.capital[0], disposal_proceeds=money(20))
        a = replace(base.assumptions, closure_cost=money(4))
        result = calculate_financials(replace(base, assumptions=a, capital=(asset,)))
        self.assertFalse(result.issues, result.issues)
        self.assertEqual(result.ledger[-1].disposal_gain, D(20))
        self.assertEqual(result.ledger[-1].income_tax, D(14))
        self.assertEqual(result.ledger[-1].fcff, D(102))

    def test_startup_expensed_not_invested_and_depreciated_twice(self):
        base = fixture()
        startup = replace(
            base.capital[0],
            id="startup",
            kind="startup",
            amount=money(10),
            startup_treatment="expensed",
            depreciation=replace(
                base.capital[0].depreciation,
                method="none",
                depreciable_fraction=p(0),
                service_year=0,
            ),
        )
        result = calculate_financials(replace(base, capital=base.capital + (startup,)))
        self.assertFalse(result.issues, result.issues)
        self.assertEqual(result.ledger[0].capex, D(100))
        self.assertEqual(result.ledger[0].startup_expense, D(10))
        self.assertEqual(result.ledger[0].fcff, D(-120))
        self.assertEqual(result.ledger[-1].disposal_gain, D(0))

    def test_actual_opex_not_ramped_again_and_explicit_driver(self):
        base = fixture()
        operation = base.operations[0]
        products = (
            replace(
                operation.products[0],
                produced=D(50),
                saleable=D(50),
                sold=D(40),
                revenue=money(40),
            ),
        )
        driven = replace(
            operation.costs[1],
            method="driver",
            driver_id="product:produced",
            reference_activity=D(100),
            driver_unit="kg/year",
        )
        operation = replace(
            operation,
            products=products,
            costs=(operation.costs[0], driven),
            activities=(
                Activity("product:produced", 50, "kg/year", "Synthetic activity"),
            ),
        )
        result = calculate_financials(
            replace(base, operations=(operation,) + base.operations[1:])
        )
        self.assertFalse(result.issues, result.issues)
        self.assertEqual(result.ledger[1].variable_opex, D(5))
        self.assertEqual(result.ledger[1].fixed_opex, D(20))
        actual = replace(operation, costs=base.operations[0].costs)
        self.assertEqual(
            calculate_financials(
                replace(base, operations=(actual,) + base.operations[1:])
            )
            .ledger[1]
            .variable_opex,
            D(10),
        )

    def test_inflation_fx_missing_units_and_missing_assumptions(self):
        base = fixture()
        product = replace(
            base.operations[0].products[0],
            revenue=money(80, "USD", 2027),
            price_treatment="base",
        )
        a = replace(
            base.assumptions,
            price_mode="nominal",
            inflation=p(".1", "fraction/year"),
            exchange_rates=(ExchangeRate("USD", 2027, p(".8", "GBP/USD")),),
        )
        # Actual nominal rows need their own dated annual prices. The first
        # product is deliberately a base-price forecast instead.
        later = tuple(
            replace(
                o,
                products=tuple(
                    replace(s, revenue=replace(s.revenue, price_year=2027 + o.year - 1))
                    for s in o.products
                ),
                costs=tuple(
                    replace(c, amount=replace(c.amount, price_year=2027 + o.year - 1))
                    for c in o.costs
                ),
            )
            for o in base.operations[1:]
        )
        result = calculate_financials(
            replace(
                base,
                assumptions=a,
                operations=(replace(base.operations[0], products=(product,)),) + later,
            )
        )
        self.assertFalse(result.issues, result.issues)
        self.assertEqual(result.ledger[1].revenue, D(64))
        bad = replace(
            base,
            assumptions=replace(
                base.assumptions, project_discount_rate=p(None, "fraction/year")
            ),
        )
        self.assertEqual(calculate_financials(bad).status, "needs_review")
        bad = replace(
            base,
            assumptions=replace(
                base.assumptions, project_discount_rate=p(".1", "percent")
            ),
        )
        self.assertTrue(calculate_financials(bad).issues)
        self.assertTrue(calculate_financials(replace(base, operations=())).issues)

    def test_zero_production_period_and_negative_cash(self):
        base = fixture()
        first = replace(
            base.operations[0],
            products=(
                replace(
                    base.operations[0].products[0],
                    produced=D(0),
                    saleable=D(0),
                    sold=D(0),
                    revenue=money(0),
                ),
            ),
        )
        result = calculate_financials(
            replace(base, operations=(first,) + base.operations[1:])
        )
        self.assertFalse(result.issues, result.issues)
        self.assertLess(result.ledger[1].fcff, 0)
        self.assertIsNone(metric(result, "cash_production_cost.1").value)
        self.assertIsNone(metric(result, "project_payback").value)

    def test_irr_multiple_tangent_undefined_and_mirr(self):
        for flow, expected in (((-100, 110), ".1"), ((-100, 200, -100), "0")):
            result = irr(tuple(D(0) for _ in flow), tuple(D(x) for x in flow))
            self.assertAlmostEqual(result.value, D(expected), places=8)
        multiple = irr((D(0),) * 3, tuple(D(x) for x in (-100, 230, -132)))
        self.assertEqual(multiple.status, "multiple")
        self.assertIsNone(multiple.value)
        self.assertEqual(len(multiple.alternatives), 2)
        self.assertEqual(irr((D(0),) * 2, (D(-100), D(-10))).status, "undefined")
        self.assertAlmostEqual(
            mirr(
                (D(0),) * 2, (D(-100), D(110)), D(".1"), D(".1"), "discrete_end"
            ).value,
            D(".1"),
            places=20,
        )
        self.assertIsNone(payback((D(-100), D(1))).value)

    def test_garrett_table_6_3_matching_uniform_convention(self):
        recurring = (
            (D(0), D("2.5"), D("2.75"), D(3), D("3.25"), D("3.5"))
            + (D("3.75"),) * 5
            + (D("2.85"),) * 10
        )
        points = (D(-25),) + (D(0),) * 19 + (D("2.5"),)
        # Published table uses rounded discount factors: compare at its precision.
        self.assertAlmostEqual(
            npv(recurring, points, D(".1"), "garrett_uniform"),
            D("2.5228"),
            delta=D(".003"),
        )
        self.assertAlmostEqual(
            npv(recurring, points, D(".12"), "garrett_uniform"),
            D("-.9808"),
            delta=D(".003"),
        )
        root = irr(recurring, points, "garrett_uniform")
        self.assertEqual(root.status, "calculated")
        self.assertTrue(D(".11") < root.value < D(".12"))
        self.assertNotEqual(
            npv(recurring, points, D(".1"), "garrett_uniform"),
            npv(recurring, points, D(".1"), "discrete_end"),
        )

    def test_scenarios_snapshots_no_paid_calls_and_existing_baseline(self):
        base = fixture()
        before = freeze_inputs(base)
        modified, result = recalculate_scenario(
            base,
            actor="reviewer",
            reason="Discount sensitivity",
            expected_snapshot_id=snapshot_id(base),
            assumptions=replace(
                base.assumptions, project_discount_rate=p(".2", "fraction/year")
            ),
        )
        self.assertFalse(result.issues, result.issues)
        self.assertEqual(freeze_inputs(base), before)
        self.assertEqual(restore_inputs(freeze_inputs(modified)), modified)
        with localcontext() as context:
            context.prec = 3
            self.assertEqual(calculate_financials(modified), result)
        with self.assertRaises(FrozenInstanceError):
            base.operations = ()
        with tempfile.TemporaryDirectory() as folder:
            path = save_assessment(modified, result, Path(folder) / "financial.json")
            restored = restore_inputs(
                json.dumps(json.loads(path.read_text())["inputs"])
            )
            self.assertEqual(calculate_financials(restored), result)
            with self.assertRaises(FileExistsError):
                save_assessment(modified, result, path)

    def test_real_upstream_outputs_integrate_without_double_counting(self):
        from backend.capex import calculate_capex
        from backend.opex import calculate_opex
        from backend.revenue import calculate_revenue
        from backend.tests.test_capex import equipment
        from backend.tests.test_capex import inputs as capex_inputs
        from backend.tests.test_opex import complete as opex_inputs
        from backend.tests.test_revenue import fixture as revenue_inputs

        # Explicit synthetic upstream index translation 800/320 to a common
        # 2026 planning basis, then explicit synthetic FX .8 applied upstream
        # so Garrett OPEX capital factors use the same GBP base. No current-price claim.
        capex = calculate_capex(
            inputs=capex_inputs(
                equipment=(
                    equipment(
                        purchased_cost=2000000,
                        currency="GBP",
                        period="2026 synthetic planning basis",
                        index_value=800,
                    ),
                )
            )
        )
        revenue = calculate_revenue(revenue_inputs())
        raw_opex = opex_inputs()
        # Recalculate revenue- and capital-dependent OPEX, not stale fixture
        # values. Raw materials, utilities and operating staffing stay unchanged.
        linked_opex = replace(
            raw_opex,
            bases=tuple(
                replace(b, amount=capex.fixed_capital + capex.startup_expenses)
                if b.id == "plant_including_startup_excluding_working_capital"
                else replace(b, amount=revenue.annual[0].sales_revenue)
                if b.id == "annual_revenue"
                else b
                for b in raw_opex.bases
            ),
        )
        opex = calculate_opex(inputs=linked_opex)
        with self.assertRaises(ValueError):
            operations_from_results(
                revenue,
                {1: calculate_opex(inputs=raw_opex)},
                year_map={1: 1},
                price_year=2026,
            )
        base = fixture(life=1)
        policies = {
            key: replace(base.capital[0].depreciation, life=1)
            for key in ("direct", "indirect", "offsite", "startup")
        }
        proceeds = {
            key: Money(0, "USD", 1987, "Declared zero terminal proceeds")
            for key in policies
        }
        capital, wc = capital_from_result(
            capex,
            price_year=2026,
            spend=(Spend(0, p(1)),),
            depreciation_policies=policies,
            disposal_year=1,
            disposal_proceeds=proceeds,
            startup_treatment="capitalized",
        )
        # All cross-engine factor bases now share the explicit GBP price basis.
        policies = {k: replace(v, residual_basis=money(0)) for k, v in policies.items()}
        capital = tuple(
            replace(c, depreciation=policies[c.kind], price_treatment="actual")
            for c in capital
        )
        a = replace(
            base.assumptions,
            financial_base_year=2026,
            exchange_rates=(),
            working_capital=replace(
                base.assumptions.working_capital, requirements=(DatedMoney(0, wc),)
            ),
        )
        operations = operations_from_results(
            revenue, {1: opex}, year_map={1: 1}, price_year=2026
        )
        result = calculate_financials(
            replace(base, assumptions=a, capital=capital, operations=operations)
        )
        self.assertFalse(result.issues, result.issues)
        self.assertEqual(result.ledger[1].revenue, D(3200000))
        self.assertEqual(
            result.ledger[1].fixed_opex + result.ledger[1].variable_opex, D(946970)
        )
        self.assertEqual(result.ledger[0].capex, D(2635500) * D("2.5") * D(".8"))
        self.assertEqual(
            result.ledger[0].working_capital_change, D(251000) * D("2.5") * D(".8")
        )
        prepared = prepare_financial_inputs(
            project_id="full-upstream",
            assumptions=replace(
                a, working_capital=replace(a.working_capital, requirements=())
            ),
            capex_result=capex,
            opex_by_revenue_year={1: opex},
            revenue_result=revenue,
            year_map={1: 1},
            price_year=2026,
            capital_spend=(Spend(0, p(1)),),
            depreciation_policies=policies,
            disposal_proceeds=proceeds,
            startup_treatment="capitalized",
            working_capital_funding_year=0,
        )
        self.assertFalse(calculate_financials(prepared).issues)
        self.assertEqual(
            calculate_financials(prepared).ledger[0].capex, result.ledger[0].capex
        )
        self.assertIn("capex", json.loads(prepared.upstream_snapshots_json))

    def test_midyear_production_reuses_revenue_math_once(self):
        from backend.tests.test_revenue import fixture as revenue_inputs

        base = fixture(life=1)
        a = replace(
            base.assumptions,
            commissioning_date=date(2027, 7, 1),
            first_production_date=date(2027, 7, 1),
        )
        periods = build_timeline(a)
        self.assertTrue(0 < periods[1].operating_fraction < 1)
        revenue_project = revenue_inputs()
        revenue_project = replace(
            revenue_project,
            schedule=revenue_project.schedule
            + (replace(revenue_project.schedule[0], year=2),),
            products=tuple(
                replace(
                    product, years=product.years + (replace(product.years[0], year=2),)
                )
                for product in revenue_project.products
            ),
        )
        result = revenue_with_operating_plan(
            revenue_project,
            (
                ProductionPlan(
                    1,
                    1,
                    p(8000, "h/year"),
                    p(".5"),
                    p(".5"),
                    "Explicit synthetic physical plan",
                ),
                ProductionPlan(
                    2,
                    2,
                    p(8000, "h/year"),
                    p(".5"),
                    p(".5"),
                    "Explicit partial terminal operating plan",
                ),
            ),
            a,
        )
        self.assertFalse(result.issues, result.issues)
        expected = (
            D(100)
            * D(8000)
            * D(".5")
            * periods[1].operating_fraction
            * D(".5")
            * D(".8")
            * D(".5")
            * D(10)
        )
        self.assertAlmostEqual(result.annual[0].sales_revenue, expected, places=7)

    def test_multiple_products_do_not_receive_arbitrary_lcop_allocation(self):
        base = fixture()
        operations = tuple(
            replace(
                o,
                products=o.products
                + (replace(o.products[0], id="byproduct", unit="L"),),
            )
            for o in base.operations
        )
        result = calculate_financials(replace(base, operations=operations))
        self.assertFalse(result.issues, result.issues)
        self.assertEqual(metric(result, "levelised_cost").status, "allocation_required")

    def test_nonrefundable_credits_cap_liability_and_require_policy_source(self):
        base = fixture(revenue=120)
        tax = replace(
            base.assumptions.tax,
            annual_nonrefundable_credits=(DatedMoney(1, money(50)),),
            credit_policy_source="Explicit synthetic nonrefundable current-year credit, no eligibility claim",
        )
        result = calculate_financials(
            replace(base, assumptions=replace(base.assumptions, tax=tax))
        )
        self.assertFalse(result.issues, result.issues)
        self.assertEqual(result.ledger[1].income_tax, 0)
        self.assertEqual(result.ledger[1].equity_credit_used, D(10))
        self.assertEqual(result.ledger[2].income_tax, D(10))
        invalid = replace(
            base,
            assumptions=replace(
                base.assumptions, tax=replace(tax, credit_policy_source="")
            ),
        )
        self.assertTrue(calculate_financials(invalid).issues)

    def test_historical_actual_prices_and_missing_fx_are_not_silently_relabelled(self):
        base = fixture()
        product = replace(
            base.operations[0].products[0], revenue=money(80, "USD", 1987)
        )
        bad = replace(
            base,
            operations=(replace(base.operations[0], products=(product,)),)
            + base.operations[1:],
        )
        self.assertTrue(calculate_financials(bad).issues)
        product = replace(product, revenue=money(80, "USD", 2027))
        self.assertTrue(
            calculate_financials(
                replace(
                    base,
                    operations=(replace(base.operations[0], products=(product,)),)
                    + base.operations[1:],
                )
            ).issues
        )

    def test_capital_double_counting_driver_unit_and_instantaneous_depreciation(self):
        base = fixture()
        self.assertTrue(
            calculate_financials(replace(base, capital=base.capital * 2)).issues
        )
        self.assertTrue(
            calculate_financials(
                replace(
                    base,
                    capital=(
                        replace(
                            base.capital[0],
                            depreciation=replace(
                                base.capital[0].depreciation, service_year=0
                            ),
                        ),
                    ),
                )
            ).issues
        )
        operation = base.operations[0]
        driver = replace(
            operation.costs[1],
            method="driver",
            driver_id="product:produced",
            reference_activity=D(100),
            driver_unit="tonne/year",
        )
        self.assertTrue(
            calculate_financials(
                replace(
                    base,
                    operations=(replace(operation, costs=(operation.costs[0], driver)),)
                    + base.operations[1:],
                )
            ).issues
        )

    def test_three_year_construction_then_twenty_percent_and_full_production(self):
        base = fixture(construction=3)
        first = base.operations[0]
        product = replace(
            first.products[0],
            produced=D(20),
            saleable=D(20),
            sold=D(16),
            revenue=money(16),
        )
        variable = replace(
            first.costs[1],
            method="driver",
            driver_id="product:produced",
            reference_activity=D(100),
            driver_unit="kg/year",
        )
        first = replace(
            first,
            products=(product,),
            costs=(first.costs[0], variable),
            activities=(
                Activity(
                    "product:produced",
                    20,
                    "kg/year",
                    "Explicit independent 20% startup reference",
                ),
            ),
        )
        result = calculate_financials(
            replace(base, operations=(first, base.operations[1]))
        )
        self.assertFalse(result.issues, result.issues)
        self.assertTrue(all(row.revenue == 0 for row in result.ledger[:4]))
        self.assertEqual(result.ledger[4].revenue, D(16))
        self.assertEqual(result.ledger[4].variable_opex, D(2))
        self.assertEqual(result.ledger[4].fixed_opex, D(20))
        self.assertEqual(result.ledger[5].revenue, D(80))

    def test_unit_costs_break_even_and_lcop_have_explicit_common_basis(self):
        base = fixture(revenue=120)
        result = calculate_financials(
            replace(
                base,
                assumptions=replace(
                    base.assumptions, project_discount_rate=p(0, "fraction/year")
                ),
            )
        )
        self.assertFalse(result.issues, result.issues)
        self.assertEqual(metric(result, "cash_production_cost.1").value, D(".3"))
        self.assertEqual(metric(result, "full_production_cost.1").value, D(".8"))
        self.assertEqual(metric(result, "contribution_margin.1").value, D("1.375"))
        self.assertEqual(metric(result, "break_even_price.1").value, D(1))
        self.assertEqual(metric(result, "levelised_cost").value, D(".8"))


if __name__ == "__main__":
    unittest.main()
