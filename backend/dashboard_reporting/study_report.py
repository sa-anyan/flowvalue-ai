"""Self-contained study report from one saved scenario; no independent economics."""

import json
from decimal import Decimal, InvalidOperation
from html import escape


def text(value):
    if value is None:
        return "Not applicable / not reached"
    if isinstance(value, (dict, list, tuple)):
        return escape(str(value))
    try:
        number = Decimal(str(value))
        if number.is_finite():
            return f"{number:,.6f}".rstrip("0").rstrip(".")
    except InvalidOperation:
        pass
    return escape(str(value))


def table(columns, rows):
    return (
        '<div class="table"><table><thead><tr>'
        + "".join("<th>" + escape(label) + "</th>" for _, label in columns)
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>"
            + "".join("<td>" + text(row.get(key)) + "</td>" for key, _ in columns)
            + "</tr>"
            for row in rows
        )
        + "</tbody></table></div>"
    )


def render_study(state):
    results = state.get("results") or {}
    stages = results.get("stages", {})
    financial = stages.get("financial", {}).get("result") or {}
    if not financial.get("ledger"):
        raise ValueError("Calculate the financial study before opening its report")
    config = state["plan"]["operating_economics"]
    opex = stages["opex"]["result"]
    detail = opex["operating_detail"]
    first = detail["years"][next(iter(detail["years"]))]
    metrics = dict(financial["metrics"])
    currency = financial["currency"]
    price_year = financial["financial_base_year"]
    blocks = [
        '<p class="eyebrow">FLOWVALUE AI · PRELIMINARY PROCESS ECONOMICS</p><h1>Techno-economic assessment</h1>',
        "<p>Source: "
        + escape(state["filename"])
        + " · assessment "
        + escape(state["id"])
        + " · revision "
        + str(state["revision"])
        + "</p>",
        '<p class="notice">Conditional engineering/commercial scenario. '
        + escape(currency)
        + " at "
        + str(price_year)
        + " constant prices; no current market-price claim. Equipment exclusions remain part of the study scope. This report is a saved calculation record, not an independently validated industrial design.</p>",
        "<h2>Project and saleable output</h2><p>"
        + escape(state["description"])
        + "</p>",
        "<h2>Study basis</h2><p>"
        + text(config["operating"]["days_per_year"])
        + " days/year · "
        + text(detail["annual_hours"])
        + " hours/year. The 314-day basis is a user planning assumption, not a universal maximum efficiency.</p><p>"
        + escape(config["financial"]["rationale"])
        + "</p>",
    ]
    selected = []
    for key in (
        "project_npv",
        "project_irr",
        "project_mirr",
        "project_payback",
        "project_discounted_payback",
        "levelised_cost",
        "roi",
    ):
        metric = metrics[key]
        value = metric["value"]
        if key in {"project_irr", "project_mirr", "roi"} and value is not None:
            value = str(Decimal(value) * 100) + "%"
        selected.append(
            {
                "name": key.replace("_", " "),
                "value": value,
                "unit": metric["unit"],
                "status": metric["status"],
            }
        )
    blocks += [
        "<h2>Investment metrics</h2>",
        table(
            [
                ("name", "Metric"),
                ("value", "Value"),
                ("unit", "Unit"),
                ("status", "Outcome"),
            ],
            selected,
        ),
    ]
    equipment = stages["equipment"]["result"]["equipment"]
    blocks += [
        "<h2>Equipment and capital scope</h2>",
        table(
            [
                ("equipment_tag", "Equipment"),
                ("curve_id", "Garrett model"),
                ("equipment_cost", "Purchased cost"),
                ("installation_cost", "Installation"),
                ("equipment_and_installation_cost", "Combined"),
                ("status", "Basis"),
            ],
            equipment,
        ),
    ]
    capex = stages["capex"]["result"]
    blocks += [
        table(
            [
                ("id", "Capital item"),
                ("base", "Calculation base"),
                ("fraction", "Selected fraction"),
                ("amount", "Amount"),
            ],
            capex["lines"],
        )
    ]
    blocks += [
        "<p>Total scoped CAPEX: <strong>"
        + text(capex["total_capex"])
        + " "
        + escape(currency)
        + "</strong>; working capital "
        + text(capex["working_capital"])
        + ".</p>"
    ]
    blocks += [
        "<h2>First operating-year feeds and materials</h2>",
        table(
            [
                ("name", "Material"),
                ("annual_quantity", "Annual quantity"),
                ("quantity_unit", "Unit"),
                ("unit_price", "Price per unit"),
                ("annual_cost", "Annual cost"),
                ("rationale", "Engineering basis"),
            ],
            first["materials"],
        ),
    ]
    energy = []
    for row in first["energy"]:
        energy.append(dict(row, rationale=row["assumptions"]["rationale"]))
    blocks += [
        "<h2>Equipment utilities</h2>",
        table(
            [
                ("name", "Duty"),
                ("utility", "Utility"),
                ("method", "Method"),
                ("input_kw", "Input kW"),
                ("annual_energy_kwh", "Annual kWh"),
                ("tariff_per_kwh", "Tariff/kWh"),
                ("annual_cost", "Annual cost"),
                ("rationale", "Source / assumption"),
            ],
            energy,
        ),
    ]
    blocks += [
        "<h2>Staffing and expertise</h2>",
        table(
            [
                ("role", "Role"),
                ("arrangement", "Arrangement"),
                ("allocated_fte", "Allocated FTE"),
                ("annual_base_salary", "Base salary/FTE"),
                ("annual_cost", "Annual cost"),
                ("rationale", "Engineering basis"),
            ],
            first["labour"],
        ),
    ]
    blocks += [
        "<h2>Garrett manufacturing-cost ledger — first operating year</h2>",
        table(
            [
                ("category", "Category"),
                ("method", "Method"),
                ("calculation_base", "Base"),
                ("base_amount", "Base amount"),
                ("rate", "Rate/fraction"),
                ("behavior", "Cost behavior"),
                ("accounting", "Accounting"),
                ("amount", "Annual amount"),
                ("rationale", "Basis"),
            ],
            opex["first_year_lines"],
        ),
    ]
    blocks += [
        "<p>Cash OPEX: "
        + text(opex["first_year_cash_opex"])
        + "; fixed "
        + text(opex["first_year_fixed_opex"])
        + "; variable "
        + text(opex["first_year_variable_opex"])
        + ". Depreciation and financing reference rows are not added to cash OPEX.</p>"
    ]
    revenue = stages["revenue"]["result"]
    blocks += [
        "<h2>Production, saleability and annual revenue</h2>",
        table(
            [
                ("year", "Operating year"),
                ("product_id", "Product"),
                ("quantity_unit", "Unit"),
                ("produced_quantity", "Produced"),
                ("saleable_quantity", "Saleable"),
                ("quantity_sold", "Sold"),
                ("net_selling_price", "Net price"),
                ("net_sales_revenue", "Revenue"),
            ],
            revenue["products"],
        ),
    ]
    if revenue.get("commercial"):
        blocks += ["<h2>Commercial income by payment mechanism</h2>", table([
            ("line_id", "Payment"), ("category", "Category"), ("year", "Year"),
            ("quantity", "Billable quantity"), ("quantity_unit", "Unit"),
            ("rate", "Rate"), ("fixed_payment", "Fixed payment"), ("revenue", "Annual revenue"),
            ("status", "Assumption status")], revenue["commercial"])]
    if revenue.get("avoided_costs"):
        blocks += ["<h2>Avoided costs — OPEX reductions, excluded from sales</h2>",
            table([("id", "Saving"), ("target_opex_id", "OPEX owner"), ("rationale", "Basis")], revenue["avoided_costs"])]
    if state.get("commercial_strategy"):
        blocks += ["<h2>Commercial Strategy Analyst — saved decision record</h2><pre>" + escape(json.dumps(state["commercial_strategy"], indent=2)) + "</pre>"]
    if detail["coupling"]:
        blocks += [
            "<h2>Coupled cost-plus target pricing</h2><p>This is an operating-cost-plus target price, not evidence of market acceptance or a verified selling price.</p>",
            table(
                [
                    ("year", "Year"),
                    ("non_sales_cash_opex", "Non-sales cash costs"),
                    ("sales_cost_fraction", "Sales-based fraction"),
                    ("cost_markup_fraction", "Cost markup"),
                    ("target_total_revenue", "Target revenue"),
                    ("derived_target_quote_per_unit", "Target unit quote"),
                ],
                detail["coupling"],
            ),
        ]
    ledger = [dict(r, year=r["period"]["year"]) for r in financial["ledger"]]
    blocks += [
        "<h2>Annual financial schedule</h2>",
        table(
            [
                ("year", "Year"),
                ("revenue", "Revenue"),
                ("fixed_opex", "Fixed OPEX"),
                ("variable_opex", "Variable OPEX"),
                ("depreciation", "Depreciation"),
                ("income_tax", "Tax"),
                ("net_income", "Net income"),
                ("capex", "Capital spending"),
                ("working_capital_change", "WC change"),
                ("working_capital_recovery", "WC recovery"),
                ("fcff", "Project cash flow"),
                ("cumulative_project_cash", "Cumulative cash flow"),
            ],
            ledger,
        ),
    ]
    blocks += [
        "<h2>Factor selections and justifications</h2>",
        table(
            [
                ("category", "Garrett category"),
                ("fraction", "Selected factor"),
                ("rationale", "Selection basis"),
            ],
            [dict(category=k, **v) for k, v in config["garrett_factors"].items()],
        ),
    ]
    blocks += [
        "<h2>Exclusions and remaining review</h2>",
        table(
            [("equipment_tag", "Equipment"), ("reason", "Unpriced/excluded scope")],
            results.get("exclusions", []),
        ),
    ]
    notes = config.get("scope_notes", []) + state.get("questions", [])
    blocks += [
        "<ul>" + "".join("<li>" + escape(n) + "</li>" for n in notes) + "</ul>",
        "<p>Method: Garrett Chapter 4 manufacturing-cost parameters; existing canonical equipment, CAPEX, revenue and financial engines. Source quantities come from workbook cells; assumed prices, staffing, duties and policies remain editable. Original legacy workbook formulas were not used.</p>",
    ]
    if state.get("analyst_reviews"):
        blocks.append("<h2>Specialist engineering and material review</h2>")
        for review in state["analyst_reviews"]:
            blocks.append("<h3>" + escape(review["role"].replace("_", " ")) + "</h3><p>" + escape(review.get("summary", review.get("notice", ""))) + "</p>")
            blocks.append(table([("topic", "Topic"), ("requirement", "Requirement"), ("recommendation", "Recommendation"), ("rationale", "Reasoning"), ("alternatives", "Alternatives"), ("challenge", "Challenge"), ("uncertainty", "Uncertainty"), ("proposed_cost_owner", "Cost owner")], review.get("findings", [])))
        blocks.append("<h3>Recorded user review decisions</h3>")
        blocks.append(table([("finding_id", "Finding"), ("decision", "Decision"), ("comment", "Engineering comment")], state.get("review_decisions", [])))
    for draft in state.get("research_drafts", []):
        blocks.append("<h2>Sourced research draft</h2><p>" + escape(draft["summary"]) + "</p><p>" + escape(draft["notice"]) + "</p>")
        blocks.append(table([("name", "Candidate"), ("source_url", "Source"), ("source_date", "Date"), ("price", "Observed price"), ("currency", "Currency"), ("scope", "Scope"), ("uncertainty", "Uncertainty")], draft["candidates"]))
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>FlowValue TEA Study</title><style>body{font:14px/1.55 Arial;color:#253b31;max-width:1400px;margin:40px auto;padding:0 24px}h1{font-size:34px}h2{margin-top:38px;font-size:20px}.eyebrow{letter-spacing:2px;color:#6c855c;font-size:11px}.notice{padding:18px;background:#eff4e9;border-left:4px solid #708a5d}.table{overflow:auto}table{border-collapse:collapse;width:100%;font-size:12px}td,th{padding:9px;text-align:left;border-bottom:1px solid #dce3d7;vertical-align:top}th{background:#eff3e9}@media print{body{margin:0}h2{break-after:avoid}tr{break-inside:avoid}}</style><body>'
        + "".join(blocks)
        + "</body></html>"
    )
