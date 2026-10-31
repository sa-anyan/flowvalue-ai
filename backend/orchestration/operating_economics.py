"""Canonical coupled operating study: source consumption → OPEX/revenue → annual ledger.

LLM/user supplies editable decisions; Python expands annual quantities, applies Garrett
bases and solves cost-plus/revenue-based expense coupling without iterative guessing.
"""

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


def _a(
    value,
    unit,
    config,
    rationale,
    *,
    source="Editable AI study assumption",
    status="llm_estimate",
):
    return Assumption(
        value,
        unit,
        rationale,
        source,
        "Unverified conditional planning scenario",
        status,
        config["assumption_date"],
    )


def operating_schedule(config):
    operating = config["operating"]
    days = decimal(operating["days_per_year"], maximum=366)
    hours = days * decimal(operating["hours_per_day"], maximum=24)
    if hours <= 0 or hours > 8784:
        raise ValueError(
            "Annual operating hours must be positive and physically possible"
        )
    life = int(config["financial"]["operating_years"])
    if life != config["financial"]["operating_years"] or not 1 <= life <= 50:
        raise ValueError("Integer operating life from 1–50 years required")
    ramp = [decimal(x, maximum=1) for x in config["financial"]["production_ramp"]]
    if not ramp:
        raise ValueError("Explicit production ramp required")
    return hours, {i: ramp[min(i - 1, len(ramp) - 1)] for i in range(1, life + 1)}


def _revenue_project(report, description, config, basis, hours, ramp, prices):
    from .commercial_pricing import adjusted_price
    streams = {}
    products = []
    ids = set()
    for item in config["sales"]:
        item = dict(item)
        if item.get("price_observation"):
            if item["price_mode"] != "assumed_price":
                raise ValueError("A market observation and cost-plus target cannot both own the selling price")
            item["unit_price"] = adjusted_price(item["price_observation"], currency=basis.currency,
                price_period=basis.price_period, quantity_unit=item["quantity_unit"])["unit_price"]
        if (
            not item["context_quote"].strip()
            or item["context_quote"].casefold() not in description.casefold()
        ):
            raise ValueError(
                item["name"]
                + ": sale must be linked to an explicit project-context statement"
            )
        if item["id"] in ids:
            raise ValueError("Duplicate sale product ID")
        ids.add(item["id"])
        unit = item["quantity_unit"]
        prop = "volume_flow" if unit in {"m3", "L"} else "mass_flow"
        v = observation(report, item["stream_key"], prop)
        stream = Stream(
            item["stream_key"],
            item["name"],
            _a(
                v["normalized_value"],
                v["normalized_unit"],
                config,
                "Workbook observation; quantity is not invented",
                source=v["workbook"] + "!" + v["sheet"] + "!" + v["cell"],
                status="source_supported",
            ),
            (v["id"],),
            "outlet",
            "Conditional product/service interpretation from explicit project context",
        )
        streams[stream.id] = stream
        years = []
        for year in ramp:
            adjustments = []
            for key, scope in [
                ("net_freight_deduction_per_unit", "outbound_freight"),
                ("net_packaging_deduction_per_unit", "sales_packaging"),
            ]:
                if decimal(item[key]):
                    adjustments.append(
                        Adjustment(
                            item["id"] + ":" + scope,
                            scope,
                            "deduction",
                            "per_unit",
                            _a(
                                item[key],
                                basis.currency + "/" + unit,
                                config,
                                item["rationale"],
                            ),
                            "revenue",
                        )
                    )
            years.append(
                ProductYear(
                    year,
                    _a(
                        prices.get((item["id"], year), item["unit_price"]),
                        basis.currency + "/" + unit,
                        config,
                        item["rationale"],
                    ),
                    "fraction_of_saleable",
                    _a(item["sold_fraction"], "fraction", config, item["rationale"]),
                    tuple(adjustments),
                )
            )
        products.append(
            Product(
                item["id"],
                item["name"],
                stream.id,
                item["role"],
                unit,
                _a(item["allocation_fraction"], "fraction", config, item["rationale"]),
                _a(item["saleable_fraction"], "fraction", config, item["rationale"]),
                item["specification_basis"],
                "provisional",
                "gross_quote",
                "Scenario quote in " + basis.currency + "/" + unit,
                (),
                tuple(a.cost_scope for a in (years[0].adjustments if years else ())),
                MarketStudy(
                    "Project location not independently researched",
                    item["specification_basis"],
                    historical_context="Price/demand are planning estimates, not market research",
                ),
                tuple(years),
                True,
                False,
                "",
                "",
            )
        )
    schedule = tuple(
        OperatingYear(
            y,
            _a(
                hours,
                "h/year",
                config,
                config["operating"]["rationale"],
                status="user_assumption",
                source="Shared schedule; 314 days explicitly requested by user",
            ),
            _a(ramp[y], "fraction", config, "Explicit capacity ramp"),
        )
        for y in ramp
    )
    from backend.revenue.connectors.commercial import commercial_inputs
    commercial, savings = commercial_inputs(report, description, config, basis, hours, ramp, _a)
    return RevenueProject(
        "coupled-operating-study",
        basis,
        tuple(streams.values()),
        schedule,
        tuple(products),
        description,
        commercial_lines=commercial,
        avoided_costs=savings,
    )


def _costs_for_year(report, config, basis, hours, ramp, year):
    costs = []
    detail = {
        "materials": [],
        "energy": [],
        "labour": [],
        "additional_expenses": [],
        "factor_replacements": [],
    }
    seen = set()

    def add(
        key,
        category,
        behavior,
        rationale,
        uncertainty,
        *,
        method,
        quantity=None,
        rate=None,
        amount=None,
        unit="",
        evidence=(),
    ):
        if key in seen:
            raise ValueError("Duplicate operating expense ID: " + key)
        seen.add(key)
        costs.append(
            Expense(
                key,
                category,
                method,
                behavior,
                basis,
                rationale,
                "Stored operating study / " + SOURCE.reference,
                uncertainty,
                (category + ":" + key,),
                amount=amount,
                quantity=quantity,
                rate=rate,
                quantity_unit=unit + "/year"
                if method == "quantity_price"
                else "FTE"
                if method == "headcount_salary"
                else "",
                rate_unit=unit
                if method == "quantity_price"
                else "FTE/year"
                if method == "headcount_salary"
                else "",
                evidence=tuple(evidence),
            )
        )

    material_sources = set()
    feed_ownership = {}
    for item in config["materials"]:
        item = dict(item)
        if item.get("price_observation"):
            from .commercial_pricing import adjusted_price
            item["unit_price"] = adjusted_price(item["price_observation"], currency=basis.currency,
                price_period=basis.price_period, quantity_unit=item["quantity_unit"])["unit_price"]
        if item["property"] == "assumed_annual":
            quantity = decimal(item["annual_quantity_assumption"]) * ramp
            lineage = {
                "basis": "Explicit assumed annual makeup/consumption, not a workbook quantity"
            }
        else:
            source_key = (item["stream_key"], item["property"], item["component"])
            if source_key in material_sources:
                raise ValueError("Same feed observation charged more than once")
            previous = feed_ownership.setdefault(item["stream_key"], [])
            component = item.get("component")
            if any(component is None or old is None or component.casefold() == old.casefold()
                   for old in previous):
                raise ValueError("Whole delivered feed and its component/alternate-unit observations cannot be charged twice")
            previous.append(component)
            material_sources.add(source_key)
            lineage = annual_consumption(
                report,
                stream_key=item["stream_key"],
                property=item["property"],
                component=item["component"],
                quantity_unit=item["quantity_unit"],
                operating_hours=hours,
                throughput_fraction=ramp,
            )
            quantity = lineage["annual_quantity"]
        add(
            "feed:" + item["id"],
            item["category"],
            "variable",
            item["rationale"],
            item["uncertainty"],
            method="quantity_price",
            quantity=quantity,
            rate=item["unit_price"],
            unit=item["quantity_unit"],
        )
        detail["materials"].append(
            dict(
                item,
                annual_quantity=quantity,
                annual_cost=quantity * decimal(item["unit_price"]),
                lineage=plain(lineage),
            )
        )
    equipment_keys = {e["key"] for e in report["entities"] if e["kind"] == "equipment"}
    for item in config["energy"]:
        if item["equipment_key"] not in equipment_keys:
            raise ValueError("Energy item must link to an actual equipment record")
        result = equipment_energy_cost(
            item, report, operating_hours=hours, throughput_fraction=ramp
        )
        add(
            "energy:" + item["id"],
            "utilities",
            item["behavior"],
            item["rationale"],
            item["uncertainty"],
            method="quantity_price",
            quantity=result["annual_energy_kwh"],
            rate=item["tariff_per_kwh"],
            unit="kWh",
            evidence=result["source_evidence"],
        )
        detail["energy"].append(result)
    for item in config["labour"]:
        fte = decimal(item["headcount_fte"]) * decimal(
            item["allocation_fraction"], maximum=1
        )
        factor_owned = fte == 0 and any(c.id == item["category"] and c.base for c in CATEGORIES)
        if item["behavior"] == "variable":
            fte *= ramp
        if not factor_owned:
            add(
                "staff:" + item["id"],
                item["category"],
                item["behavior"],
                item["rationale"],
                item["uncertainty"],
                method="headcount_salary",
                quantity=fte,
                rate=item["annual_base_salary"],
            )
        detail["labour"].append(
            dict(
                item,
                allocated_fte=fte,
                annual_cost=fte * decimal(item["annual_base_salary"]),
                **({"coverage": "No separate staffing; applicable Garrett category retained"} if factor_owned else {}),
            )
        )
    for item in config["additional_expenses"]:
        amount = decimal(item["annual_allowance"]) * (
            ramp if item["behavior"] == "variable" else 1
        )
        add(
            "other:" + item["id"],
            item["category"],
            item["behavior"],
            item["rationale"],
            item["uncertainty"],
            method="fixed_annual",
            amount=amount,
        )
        detail["additional_expenses"].append(dict(item, effective_annual_cost=amount))
    itemized = {c.category for c in costs}
    # Explicit zero allowances only for categories whose study decision is none, never missing coverage.
    for key in ("raw_materials", "utilities", "operating_labor"):
        if key not in itemized:
            raise ValueError(
                "Engineering operating plan needs "
                + key
                + " itemisation (or an explicit zero applicability item)"
            )
    costs.append(
        Expense(
            "financing:none",
            "interest",
            "fixed_annual",
            "fixed",
            basis,
            "Explicit unlevered planning study: no borrowing/interest; financing is separate from cash OPEX",
            "Study financing policy",
            "Editable unlevered scenario",
            ("interest",),
            amount=0,
        )
    )
    # Net-price deductions and OPEX allowances cannot both own the same charge.
    revenue_owned = set()
    if any(decimal(s["net_freight_deduction_per_unit"]) for s in config["sales"]):
        revenue_owned.add("distribution_sales")
    if any(decimal(s["net_packaging_deduction_per_unit"]) for s in config["sales"]):
        revenue_owned.add("packaging_storage")
    for definition in CATEGORIES:
        if not definition.base:
            continue
        choice = config["garrett_factors"][definition.id]
        if definition.id in revenue_owned and definition.id not in itemized:
            costs.append(
                Expense(
                    "revenue-owned:" + definition.id,
                    definition.id,
                    "fixed_annual",
                    "variable",
                    basis,
                    "Charge is already deducted in net selling price; blanket OPEX factor excluded. Remaining selling/packaging scope needs explicit itemisation if applicable.",
                    "Canonical revenue/OPEX charge ownership",
                    "No duplicate charge; residual scope disclosed",
                    (definition.id,),
                    amount=0,
                )
            )
            detail["factor_replacements"].append(
                {
                    "category": definition.id,
                    "selected_reference_fraction": choice["fraction"],
                    "reason": "Revenue owns the deduction; no duplicate blanket OPEX allowance. Remaining scope is not separately priced.",
                }
            )
            continue
        if definition.id in itemized:
            detail["factor_replacements"].append(
                {
                    "category": definition.id,
                    "selected_reference_fraction": choice["fraction"],
                    "reason": "Detailed itemisation replaces the blanket factor; no double counting",
                    "rationale": choice["rationale"],
                }
            )
            continue
        behavior = "variable" if definition.base == "annual_revenue" else "fixed"
        costs.append(
            Expense(
                "garrett:" + definition.id,
                definition.id,
                "percentage",
                behavior,
                basis,
                choice["rationale"],
                SOURCE.reference + "; printed p.52/Table 4-4",
                "Historical preliminary range; selected engineering assumption",
                (definition.id,),
                rate=choice["fraction"],
                base=definition.base,
            )
        )
    return tuple(costs), detail


def _opex(capex, basis, assumptions, annual_sales):
    bases = (
        MoneyBase(
            "fixed_capital", capex.fixed_capital, basis, "Current canonical CAPEX"
        ),
        MoneyBase(
            "purchased_equipment",
            capex.purchased_equipment,
            basis,
            "Current canonical purchased subset",
        ),
        MoneyBase(
            PLANT_BASE,
            capex.fixed_capital + capex.startup_expenses,
            basis,
            "Fixed capital plus startup, excluding WC",
        ),
        MoneyBase(
            "annual_revenue",
            annual_sales,
            basis,
            "Matching coupled annual product sales",
        ),
    )
    inputs = OpexInputs(
        basis, assumptions, bases, reviewed_categories=tuple(c.id for c in CATEGORIES)
    )
    result = calculate_opex(inputs=inputs)
    if result.annual_cash_opex is None:
        raise ValueError("Operating plan: " + "; ".join(result.issues))
    return result


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
                other_sales += sum((r.revenue for r in initial.commercial if r.year == year), Decimal(0))
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
