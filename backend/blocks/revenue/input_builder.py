"""Canonical _revenue_project adapter, owned by this block."""

from backend.opex.consumption import annual_consumption, decimal, observation
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
from backend.blocks.shared import _a, operating_schedule, production_schedule


def _revenue_project(report, description, config, basis, hours, ramp, prices):
    from backend.revenue.authority import require

    require(config)
    if config.get("_revenue_authority"):
        description = config["_revenue_authority"]["text"]
    from backend.orchestration.commercial_pricing import adjusted_price

    streams = {}
    products = []
    ids = set()
    for item in config["sales"]:
        item = dict(item)
        if item.get("price_observation"):
            if item["price_mode"] != "assumed_price":
                raise ValueError(
                    "A market observation and cost-plus target cannot both own the selling price"
                )
            item["unit_price"] = adjusted_price(
                item["price_observation"],
                currency=basis.currency,
                price_period=basis.price_period,
                quantity_unit=item["quantity_unit"],
            )["unit_price"]
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
        from backend.revenue.product_basis import quantity_unit, product_observation

        unit = quantity_unit(item)
        v = product_observation(report, item)
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

    commercial, savings = commercial_inputs(
        report, description, config, basis, hours, ramp, _a
    )
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
