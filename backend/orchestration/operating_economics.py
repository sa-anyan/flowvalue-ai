"""Canonical coupled operating study: source consumption → OPEX/revenue → annual ledger.

LLM/user supplies editable decisions; Python expands annual quantities, applies Garrett
bases and solves cost-plus/revenue-based expense coupling without iterative guessing.
"""

import copy
from contextlib import contextmanager
from decimal import Decimal, localcontext

from backend.financial_modelling import calculate_financials
from backend.financial_modelling.connectors.operating_economics import (
    prepare_study_financials,
)
from backend.opex import calculate_opex
from backend.opex.consumption import annual_consumption, decimal, observation
from backend.opex.energy_costs import equipment_energy_cost
from backend.opex.indexes.garrett.model import CATEGORIES, PLANT_BASE, SOURCE
from backend.opex.models import Assumption as Expense
from backend.opex.models import Basis, MoneyBase, OpexInputs
from backend.revenue import calculate_revenue
from backend.revenue.models import (
    Adjustment,
    Assumption,
    MarketStudy,
    OperatingYear,
    Product,
    ProductYear,
    RevenueProject,
    Stream,
)

from .codec import plain


from backend.blocks.shared import _a, operating_schedule, production_schedule
from backend.blocks.revenue.input_builder import _revenue_project
from backend.blocks.opex.input_builder import _costs_for_year, _opex


def calculate_operating_study(
    report, description, config, capex, *, project_id="operating-study"
):
    with localcontext() as context:
        context.prec = 40
        if config.get("methodology") != "garrett":
            raise ValueError("This operating study uses Garrett exclusively")
        if capex is None or capex.total_capex is None:
            raise ValueError("Operating study requires a calculated capital scope")
        if config.get("price_basis") and config["price_basis"] != {
            "currency": capex.currency,
            "price_period": capex.period,
        }:
            raise ValueError(
                "Operating price assumptions use a different currency/period; update their stated price basis explicitly"
            )
        from backend.revenue.commercial_intent import require_resolved_intent

        require_resolved_intent(config, description)
        basis = Basis(capex.currency, capex.period)
        hours, ramp = operating_schedule(config)
        costs = {}
        details = {}
        opex = {}
        prices = {}
        coupling = []
        for year in ramp:
            costs[year], details[year] = _costs_for_year(
                report, config, basis, hours, ramp[year], year
            )
        initial = calculate_revenue(
            _revenue_project(report, description, config, basis, hours, ramp, prices),
            engineering_scenario=True,
        )
        if initial.issues:
            raise ValueError("Commercial scenario: " + "; ".join(initial.issues))
        from backend.revenue.economic_savings.avoided_costs import apply_savings

        for year in ramp:
            costs[year] = apply_savings(costs[year], initial.avoided_costs, year)
            details[year]["avoided_costs"] = plain(initial.avoided_costs)
        costplus = [s for s in config["sales"] if s["price_mode"] == "cost_plus"]
        if len(costplus) > 1:
            raise ValueError(
                "Use one cost-plus target product; other products have explicit prices"
            )
        for annual in initial.annual:
            year = annual.year
            if costplus:
                target = costplus[0]
                base = _opex(capex, basis, costs[year], Decimal(0))
                k = sum(
                    (
                        line.rate
                        for line in costs[year]
                        if line.method == "percentage"
                        and line.base == "annual_revenue"
                        and next(
                            c for c in CATEGORIES if c.id == line.category
                        ).accounting
                        == "cash"
                    ),
                    Decimal(0),
                )
                markup = decimal(target["cost_markup_fraction"])
                denominator = 1 - (1 + markup) * k
                if denominator <= 0:
                    raise ValueError(
                        "Selected cost-plus markup/sales-cost factors have no finite positive solution; lower either assumption"
                    )
                target_sales = (1 + markup) * base.annual_cash_opex / denominator
                other_sales = sum(
                    (
                        p.net_sales_revenue
                        for p in initial.products
                        if p.year == year and p.product_id != target["id"]
                    ),
                    Decimal(0),
                )
                other_sales += sum(
                    (r.revenue for r in initial.commercial if r.year == year),
                    Decimal(0),
                )
                product = next(
                    p
                    for p in initial.products
                    if p.year == year and p.product_id == target["id"]
                )
                if product.quantity_sold <= 0:
                    raise ValueError(
                        "Cost-plus target requires a positive sold quantity"
                    )
                net_target = max(Decimal(0), target_sales - other_sales)
                price = (
                    net_target / product.quantity_sold
                    + decimal(target["net_freight_deduction_per_unit"])
                    + decimal(target["net_packaging_deduction_per_unit"])
                )
                prices[target["id"], year] = price
                coupling.append(
                    {
                        "year": year,
                        "non_sales_cash_opex": base.annual_cash_opex,
                        "sales_cost_fraction": k,
                        "cost_markup_fraction": markup,
                        "target_total_revenue": target_sales,
                        "other_product_revenue": other_sales,
                        "derived_target_quote_per_unit": price,
                        "basis": "R=(1+markup)*B / (1-(1+markup)*sales_cost_fraction); target price, not market evidence",
                    }
                )
        project = _revenue_project(
            report, description, config, basis, hours, ramp, prices
        )
        revenue = calculate_revenue(project, engineering_scenario=True)
        if revenue.issues:
            raise ValueError("; ".join(revenue.issues))
        for annual in revenue.annual:
            opex[annual.year] = _opex(
                capex, basis, costs[annual.year], annual.sales_revenue
            )
        financial_inputs = prepare_study_financials(
            project_id=project_id,
            config=config,
            capex=capex,
            revenue=revenue,
            opex_by_year=opex,
        )
        financial = calculate_financials(financial_inputs)
        return {
            "revenue": revenue,
            "opex": opex,
            "financial_inputs": financial_inputs,
            "financial": financial,
            "detail": {
                "annual_hours": hours,
                "operating_days": config["operating"]["days_per_year"],
                "schedule_basis": config["operating"]["rationale"],
                "price_basis": plain(basis),
                "years": details,
                "coupling": coupling,
                "revenue_project": plain(project),
                "scope_notes": config.get("scope_notes", []),
            },
        }
