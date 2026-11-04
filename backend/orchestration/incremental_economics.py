"""Resolve independent economic cells; missing inputs remain pending, never zero.

Canonical strict engines still calculate each valid input. This adapter publishes
known subtotals and dependency errors without turning a subtotal into a full total.
"""

import copy
from dataclasses import replace
from decimal import Decimal

from backend.opex.models import Basis
from backend.revenue import calculate_revenue
from backend.revenue.commercial_intent import require_resolved_intent

from .codec import plain
from .operating_economics import (
    _costs_for_year,
    _opex,
    _revenue_project,
    operating_schedule,
    production_schedule,
)

ERRORS = (ValueError, TypeError, KeyError, ArithmeticError, AttributeError)


def calculate(report, description, config, capex, root_issue):
    outputs = {}
    period = config.get("price_basis", {})
    currency = capex.currency if capex is not None else period.get("currency")
    year_basis = capex.period if capex is not None else period.get("price_period")
    if not currency or not year_basis:
        raise ValueError("Currency and price period are required for monetary cells")
    basis = Basis(currency, year_basis)
    try:
        hours, ramp = operating_schedule(config)
    except ERRORS:
        # Hour-dependent cells remain pending, while fixed annual inputs still run.
        hours, ramp = None, production_schedule(config)
    if config.get("methodology") != "garrett":
        raise ValueError("Unsupported operating methodology")
    if period and period != {"currency": currency, "price_period": year_basis}:
        raise ValueError("Operating price basis must match the selected monetary basis")
    pending = []
    accepted = copy.deepcopy(config)
    for group in ("sales", "commercial_lines", "avoided_costs"):
        accepted[group] = []
    seen = set()
    for group in ("sales", "commercial_lines", "avoided_costs"):
        for item in config.get(group, []):
            try:
                from backend.revenue.authority import require

                require(config)
                if item.get("id") in seen:
                    raise ValueError("Duplicate economic line ID")
                seen.add(item.get("id"))
                if group == "sales" and item.get("price_mode") == "cost_plus":
                    raise ValueError(
                        "Cost-plus selling price awaits complete operating costs"
                    )
                candidate = copy.deepcopy(accepted)
                candidate[group] = [*accepted[group], item]
                # Verify only included commercial mechanisms; excluded lines remain pending.
                intent = candidate.get("commercial_intent")
                if intent:
                    ids = {
                        r.get("intent_id")
                        for g in ("sales", "commercial_lines")
                        for r in candidate[g]
                    }
                    intent["mechanisms"] = [
                        m for m in intent.get("mechanisms", []) if m.get("id") in ids
                    ]
                require_resolved_intent(candidate, description)
                project = _revenue_project(
                    report, description, candidate, basis, hours, ramp, {}
                )
                checked = calculate_revenue(project, engineering_scenario=True)
                if checked.issues:
                    raise ValueError("; ".join(checked.issues))
                accepted[group].append(copy.deepcopy(item))
            except ERRORS as exc:
                pending.append(
                    {
                        "group": group,
                        "id": item.get("id", "unknown"),
                        "status": "pending",
                        "reason": str(exc),
                        "excluded_from_known_subtotal": True,
                    }
                )
    revenue = None
    if accepted["sales"] or accepted["commercial_lines"]:
        try:
            project = _revenue_project(
                report, description, accepted, basis, hours, ramp, {}
            )
            revenue = calculate_revenue(project, engineering_scenario=True)
            value = plain(revenue)
            value.update(
                status="partial" if pending else "calculated_preliminary",
                complete=not pending,
                pending_items=pending,
                subtotal_notice="Calculated revenue from resolved lines only; pending lines are not zero."
                if pending
                else "Revenue calculated independently of operating-cost completeness.",
            )
            outputs["revenue"] = {
                "status": value["status"],
                "result": value,
                "issues": [p["reason"] for p in pending],
            }
        except ERRORS as exc:
            pending.append(
                {
                    "group": "revenue",
                    "id": "reconciliation",
                    "reason": str(exc),
                    "status": "pending",
                }
            )
    if revenue is None:
        outputs["revenue"] = {
            "status": "pending",
            "result": {
                "status": "pending",
                "complete": False,
                "basis": plain(basis),
                "annual": [],
                "products": [],
                "commercial": [],
                "pending_items": pending,
            },
            "issues": [p["reason"] for p in pending]
            or ["No resolved revenue method/price available"],
        }
    annual_sales = {a.year: a.sales_revenue for a in revenue.annual} if revenue else {}
    years, details, cost_pending = {}, {}, []
    for year, fraction in ramp.items():
        try:
            costs, detail = _costs_for_year(
                report, config, basis, hours, fraction, year, partial=True
            )
            if revenue and revenue.avoided_costs:
                from backend.revenue.economic_savings.avoided_costs import apply_savings

                try:
                    costs = apply_savings(costs, revenue.avoided_costs, year)
                except ERRORS as exc:
                    detail["pending_items"].append(
                        {
                            "group": "avoided_costs",
                            "id": "cost_reconciliation",
                            "reason": str(exc),
                            "status": "pending",
                        }
                    )
            result = _opex(
                capex,
                basis,
                costs,
                annual_sales.get(year) if not pending else None,
                allow_partial=True,
            )
            issues = [p["reason"] for p in detail["pending_items"]] + list(
                result.issues
            )
            if issues:
                result = replace(
                    result,
                    status="partial",
                    annual_cash_opex=None,
                    cash_fixed=None,
                    cash_variable=None,
                    annual_expense_including_depreciation_and_financing=None,
                    issues=tuple(dict.fromkeys(issues)),
                )
            value = plain(result)
            value.update(
                complete=not issues,
                pending_items=detail["pending_items"],
                known_cash_fixed=sum(
                    (
                        r.amount
                        for r in result.lines
                        if r.scope == "recurring"
                        and r.accounting == "cash"
                        and r.behavior == "fixed"
                    ),
                    Decimal(0),
                ),
                known_cash_variable=sum(
                    (
                        r.amount
                        for r in result.lines
                        if r.scope == "recurring"
                        and r.accounting == "cash"
                        and r.behavior == "variable"
                    ),
                    Decimal(0),
                ),
            )
            years[str(year)] = plain(value)
            details[str(year)] = plain(detail)
            cost_pending.extend({"year": year, **p} for p in detail["pending_items"])
        except ERRORS as exc:
            cost_pending.append(
                {
                    "year": year,
                    "id": "operating_schedule",
                    "status": "pending",
                    "reason": str(exc),
                }
            )
    first = next(iter(years.values()), {})
    incomplete = not years or any(not y["complete"] for y in years.values())
    outputs["opex"] = {
        "status": "partial" if incomplete else "calculated_preliminary",
        "result": {
            "status": "partial" if incomplete else "calculated_preliminary",
            "complete": not incomplete,
            "currency": currency,
            "price_period": year_basis,
            "first_year_cash_opex": first.get("annual_cash_opex"),
            "first_year_fixed_opex": first.get("cash_fixed"),
            "first_year_variable_opex": first.get("cash_variable"),
            "known_cash_opex_subtotal": first.get("resolved_cash_subtotal"),
            "first_year_lines": first.get("lines", []),
            "years": years,
            "pending_items": cost_pending,
            "operating_detail": {"annual_hours": plain(hours), "years": details},
            "subtotal_notice": "Known expense subtotal excludes pending lines; it is not a complete operating budget.",
        },
        "issues": list(
            dict.fromkeys(
                [p["reason"] for p in cost_pending] + list(first.get("issues", []))
            )
        ),
    }
    outputs["financial"] = {
        "status": "pending_dependencies",
        "result": {
            "status": "pending_dependencies",
            "currency": currency,
            "price_period": year_basis,
            "complete": False,
            "ledger": [
                {
                    "period": {"year": year, "kind": "operating_year"},
                    "revenue": plain(annual_sales.get(year)),
                    "known_cash_opex_subtotal": years.get(str(year), {}).get(
                        "resolved_cash_subtotal"
                    ),
                    "cash_opex": years.get(str(year), {}).get("annual_cash_opex"),
                    "free_cash_flow": None,
                }
                for year in ramp
            ],
            "metrics": {},
            "issues": [
                "Complete cash flow and investment metrics await resolved revenue, operating costs, capital and financial policy."
            ],
            "dependency_issues": list(
                dict.fromkeys(
                    [
                        root_issue,
                        *[p["reason"] for p in pending],
                        *[p["reason"] for p in cost_pending],
                    ]
                )
            ),
        },
        "issues": [
            "Investment metrics pending; independent revenue and expense cells remain available."
        ],
    }
    return outputs
