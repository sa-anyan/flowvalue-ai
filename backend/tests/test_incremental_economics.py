"""Spreadsheet-like dependency isolation without pretending missing values are zero."""

import copy
from decimal import Decimal

from backend.orchestration.incremental_economics import calculate
from backend.orchestration.operating_economics import calculate_operating_study
from backend.tests.test_operating_economics import DESCRIPTION, fixture


def test_missing_energy_keeps_independent_sales_and_known_expenses():
    report, config, capex = fixture()
    config["energy"][0]["power_kw"] = None
    result = calculate(report, DESCRIPTION, config, capex, "missing duty")
    revenue = result["revenue"]["result"]
    assert Decimal(revenue["annual"][0]["sales_revenue"]) == Decimal("292999.680")
    assert revenue["complete"] is True
    cost = result["opex"]["result"]
    assert cost["complete"] is False
    assert cost["first_year_cash_opex"] is None
    assert Decimal(cost["known_cash_opex_subtotal"]) > 0
    assert cost["pending_items"][0]["id"] == "pump-power"
    assert result["financial"]["result"]["metrics"] == {}
    assert result["financial"]["result"]["ledger"][0]["free_cash_flow"] is None
    config["energy"][0]["power_kw"] = 10
    resolved = calculate_operating_study(report, DESCRIPTION, config, capex)
    assert resolved["financial"].status == "calculated_preliminary"


def test_invalid_second_sale_does_not_erase_first_or_opex():
    report, config, capex = fixture()
    invalid = copy.deepcopy(config["sales"][0])
    invalid.update(id="second-sale", unit_price=None)
    config["sales"].append(invalid)
    result = calculate(report, DESCRIPTION, config, capex, "invalid price")
    revenue = result["revenue"]["result"]
    assert revenue["complete"] is False
    assert Decimal(revenue["annual"][0]["sales_revenue"]) == Decimal("292999.680")
    assert len(revenue["pending_items"]) == 1
    assert result["opex"]["result"]["known_cash_opex_subtotal"] is not None


def test_revenue_does_not_require_capital_and_cost_plus_is_pending():
    report, config, capex = fixture()
    r = calculate(report, DESCRIPTION, config, None, "no capex")
    assert r["revenue"]["result"]["annual"]
    assert r["opex"]["result"]["complete"] is False
    config["sales"][0]["price_mode"] = "cost_plus"
    r = calculate(report, DESCRIPTION, config, capex, "missing cost input")
    assert r["revenue"]["result"]["annual"] == []
    assert "Cost-plus" in r["revenue"]["issues"][0]
    assert r["opex"]["result"]["known_cash_opex_subtotal"] is not None


def test_pipeline_exposes_partial_results_without_capex():
    from backend.orchestration.pipeline import empty_plan, run

    report, config, _ = fixture()
    plan = empty_plan()
    plan["operating_economics"] = config
    result = run(report, DESCRIPTION, plan)
    assert result["stages"]["revenue"]["result"]["annual"]
    assert result["stages"]["opex"]["result"]["known_cash_opex_subtotal"] is not None
    assert result["stages"]["financial"]["result"]["complete"] is False


def test_healthy_expenses_survive_a_bad_material_and_no_duplicate_charge():
    report, config, capex = fixture()
    duplicate = copy.deepcopy(config["materials"][0])
    duplicate.update(id="duplicate-acid")
    config["materials"].append(duplicate)
    r = calculate(report, DESCRIPTION, config, capex, "duplicate input")
    assert len(r["opex"]["result"]["operating_detail"]["years"]["1"]["materials"]) == 1
    assert len(r["opex"]["result"]["operating_detail"]["years"]["1"]["energy"]) == 1
    assert any("charged" in p["reason"] for p in r["opex"]["result"]["pending_items"])
    assert r["revenue"]["result"]["complete"] is True


def test_partial_currency_view_preserves_pending_and_converts_known_cells():
    from backend.currency_conversion.assessment import currency_view

    report, config, capex = fixture()
    config["energy"][0]["power_kw"] = None
    stages = calculate(report, DESCRIPTION, config, capex, "missing duty")
    stages["capex"] = {"result": {"currency": "USD"}}
    saved = {"results": {"stages": stages}}
    converted = currency_view(saved, "GBP")
    original = Decimal(stages["opex"]["result"]["known_cash_opex_subtotal"])
    reported = Decimal(
        converted["results"]["stages"]["opex"]["result"]["known_cash_opex_subtotal"]
    )
    assert original != reported
    assert (
        converted["results"]["stages"]["financial"]["result"]["ledger"][0][
            "free_cash_flow"
        ]
        is None
    )
    assert converted["results"]["stages"]["financial"]["result"]["metrics"] == {}
    assert stages["opex"]["result"]["known_cash_opex_subtotal"] == str(original)


def test_missing_operating_hours_keeps_fixed_labour():
    report, config, capex = fixture()
    config["operating"]["hours_per_day"] = None
    result = calculate(report, DESCRIPTION, config, capex, "missing hours")
    detail = result["opex"]["result"]["operating_detail"]["years"]["1"]
    assert detail["labour"][0]["annual_cost"] == "90000"
    assert result["opex"]["result"]["complete"] is False
    assert result["revenue"]["result"]["annual"] == []


def test_partial_report_does_not_require_investment_metrics():
    from backend.dashboard_reporting.study_report import render_study

    report, config, capex = fixture()
    config["energy"][0]["power_kw"] = None
    result = calculate(report, DESCRIPTION, config, capex, "missing duty")
    html = render_study({"filename": "example.xlsx", "results": {"stages": result}})
    assert "partial assessment" in html
    assert "pump-power" in html
    assert "Pending" in html


def test_price_update_recalculates_revenue_and_dependent_sales_factors():
    report, config, capex = fixture()
    config["energy"][0]["power_kw"] = None
    before = calculate(report, DESCRIPTION, config, capex, "missing power")
    config["sales"][0]["unit_price"] = 2
    after = calculate(report, DESCRIPTION, config, capex, "missing power")
    revenue_before = Decimal(before["revenue"]["result"]["annual"][0]["sales_revenue"])
    revenue_after = Decimal(after["revenue"]["result"]["annual"][0]["sales_revenue"])
    assert revenue_after - revenue_before == Decimal("325555.20")
    before_lines = before["opex"]["result"]["years"]["1"]["lines"]
    after_lines = after["opex"]["result"]["years"]["1"]["lines"]
    sales_before = sum(
        Decimal(r["amount"])
        for r in before_lines
        if r["calculation_base"] == "annual_revenue"
    )
    sales_after = sum(
        Decimal(r["amount"])
        for r in after_lines
        if r["calculation_base"] == "annual_revenue"
    )
    assert sales_after > sales_before
    assert after["opex"]["result"]["complete"] is False
