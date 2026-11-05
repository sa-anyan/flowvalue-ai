"""Schema-aware reporting view; financial ledger recalculated from converted Money.

The reporting FX date is separate from historical cost dates. Original plans,
source observations and index audits stay in their original currency/basis.
"""

import copy
import re

from .currency_converter import convert_currency, rate_snapshot

MONEY_FIELDS = {
    "amount",
    "known_cash_opex_subtotal",
    "known_cash_fixed",
    "known_cash_variable",
    "cash_opex",
    "free_cash_flow",
    "low_cost",
    "high_cost",
    "total",
    "equipment_cost",
    "installation_cost",
    "equipment_and_installation_cost",
    "equipment_cost_total",
    "installation_cost_total",
    "equipment_and_installation_cost_total",
    "purchased_equipment",
    "direct_costs",
    "indirect_costs",
    "plant_cost",
    "fixed_capital",
    "startup_expenses",
    "working_capital",
    "total_capex",
    "base_amount",
    "first_year_cash_opex",
    "first_year_fixed_opex",
    "first_year_variable_opex",
    "cash_fixed",
    "cash_variable",
    "annual_cash_opex",
    "depreciation",
    "financing",
    "annual_expense_including_depreciation_and_financing",
    "resolved_cash_subtotal",
    "excluded_capital",
    "excluded_working_capital",
    "annual_cost",
    "effective_annual_cost",
    "annual_allowance",
    "annual_base_salary",
    "unit_price",
    "tariff_per_kwh",
    "rate",
    "non_sales_cash_opex",
    "other_product_revenue",
    "target_total_revenue",
    "derived_target_quote_per_unit",
    "quoted_price",
    "premium_per_unit",
    "deduction_per_unit",
    "net_selling_price",
    "gross_sales",
    "net_sales_revenue",
    "sales_revenue",
    "separate_opex_charges",
    "revenue",
    "fixed_payment",
    "minimum_payment",
    "avoided_cost",
    "annual_revenue",
    "total_revenue",
}
# Evidence is not reporting money: do not relabel historical points or raw workbook data.
SOURCE_RECORDS = {
    "evidence",
    "parsed_source",
    "source",
    "methodology_source",
    "assumptions",
    "cost_translation",
    "index_adjustment",
    "fit_diagnostics",
    "applied_factors",
    "price_observation",
    "revenue_project",
    "provenance",
    "coupling",
}


def currency_view(saved, target_currency=None):
    if saved.get('execution_mode') == 'isolated_stages_v1':
        # Stage outputs keep the basis they were explicitly run in. No read-triggered engine calls.
        return saved
    if not target_currency or saved.get("running") or not saved.get("results"):
        return saved
    state = copy.deepcopy(saved)
    results = state.get("results") or {}
    stages = results.get("stages", {})
    capex = stages.get("capex", {}).get("result") or {}
    financial = stages.get("financial", {}).get("result") or {}
    source = capex.get("currency") or financial.get("currency")
    if not source:
        return state  # incomplete studies must remain pollable while a currency is selected
    snapshot = rate_snapshot()
    audit = convert_currency(1, source, target_currency, snapshot=snapshot)

    def money(value, currency=source):
        return (
            None
            if value is None
            else convert_currency(value, currency, target_currency, snapshot=snapshot)[
                "amount"
            ]
        )

    def reporting(value, currency=source):
        if isinstance(value, list):
            return [reporting(x, currency) for x in value]
        if not isinstance(value, dict):
            return value
        current = value.get("currency", currency)
        if current is None:
            if any(
                key in MONEY_FIELDS
                and item not in (None, 0, "0")
                and not isinstance(item, (dict, list))
                for key, item in value.items()
            ):
                raise ValueError("Unresolved monetary currency for a nonzero amount")
            current = currency
        if current != source:
            raise ValueError(
                "Mixed-currency reporting requires an explicit normalized project basis"
            )
        # Explicit monetary Assumption units (e.g. USD/year) are a typed
        # boundary; the value of a fraction, kWh, salary headcount etc is not FX.
        unit = value.get("unit", "")
        match = re.match(r"^([A-Z]{3})(?=/|$)", unit) if isinstance(unit, str) else None
        if match and match[1] in snapshot["rates"] and "value" in value:
            return {
                **copy.deepcopy(value),
                "value": money(value["value"], match[1]),
                "unit": target_currency + unit[3:],
            }
        out = {}
        for key, item in value.items():
            if key in SOURCE_RECORDS or key in {"historical_amount", "anchor_cost"}:
                out[key] = copy.deepcopy(item)
            elif key == "opex_charges_separate":
                out[key] = [[label, money(amount, current)] for label, amount in item]
            elif key == "currency":
                out[key] = target_currency if item is not None else None
            elif key in MONEY_FIELDS and not isinstance(item, (dict, list)):
                out[key] = money(item, current)
            else:
                out[key] = reporting(item, current)
        return out

    for name in ("equipment", "capex", "opex", "revenue"):
        result = stages.get(name, {}).get("result")
        if result:
            stages[name]["result"] = reporting(result)
    results["screening_comparisons"] = reporting(
        results.get("screening_comparisons", [])
    )
    # All canonical Money fields, including taxation/debt/working capital, are
    # converted before the existing deterministic engine recomputes its ledger.
    inputs = results.get("financial_inputs")
    if financial and financial.get("complete") is False and not inputs:
        stages["financial"]["result"] = reporting(financial)
    elif financial and not inputs:
        raise ValueError(
            "Canonical financial inputs required to convert the full financial study"
        )
    if inputs:
        from backend.financial_modelling import calculate_financials
        from backend.financial_modelling.models import FinancialInputs
        from backend.orchestration.codec import construct, plain

        def convert_inputs(value):
            if isinstance(value, list):
                return [convert_inputs(x) for x in value]
            if not isinstance(value, dict):
                return value
            if {"amount", "currency", "price_year", "source"} <= value.keys():
                if value["currency"] != source:
                    raise ValueError(
                        "Normalize mixed-currency financial inputs before reporting conversion"
                    )
                return {
                    **value,
                    "amount": money(value["amount"], value["currency"]),
                    "currency": target_currency,
                }
            return {k: convert_inputs(v) for k, v in value.items()}

        converted = convert_inputs(inputs)
        converted["assumptions"]["currency"] = target_currency
        converted["assumptions"][
            "exchange_rates"
        ] = []  # all Money now explicitly in reporting currency
        results["financial_inputs"] = converted
        stages["financial"]["result"] = plain(
            calculate_financials(construct(FinancialInputs, converted))
        )
    state["currency_view"] = {
        **audit,
        "source_amount": "1",
        "reporting_currency": target_currency,
        "notice": "Reporting FX conversion; saved input prices and evidence retain original currencies. One fixed FX snapshot applies to all years, not an FX forecast.",
    }
    return state
