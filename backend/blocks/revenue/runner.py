"""Revenue-only execution from approved user intent and source quantities."""

import copy
from decimal import Decimal

from backend.revenue.authority import commercial_text

from backend.blocks.models import Product, DataRequired
from backend.blocks.shared import (
    operating_proposal,
    basis_and_schedule,
    plain,
    translate_inputs,
)
from backend.revenue.authority import runtime
from backend.revenue import calculate_revenue
from .input_builder import _revenue_project


def calculate(ctx):
    config, meta = operating_proposal(ctx, "revenue")
    updates = {"plan": {"operating_economics": config}}
    policy = runtime(
        config,
        {
            "text": commercial_text(ctx.state),
            "approval": ctx.state.get("revenue_approval"),
        },
        ctx.report,
    )
    if policy["questions"]:
        raise DataRequired(
            "Data required: " + " ".join(policy["questions"]), updates=updates
        )
    try:
        config, audit = translate_inputs(ctx, config, "revenue")
        basis, hours, ramp = basis_and_schedule(ctx, config)
    except (ValueError, TypeError, KeyError) as exc:
        raise DataRequired(str(exc), updates=updates) from exc
    config["_revenue_authority"] = policy
    result = calculate_revenue(
        _revenue_project(
            ctx.report,
            commercial_text(ctx.state),
            config,
            basis,
            hours,
            ramp,
            {},
        ),
        engineering_scenario=True,
    )
    display = plain(result)
    # A rate × price annual baseline is not a prediction of first-year uptake.
    # Keep the saved financial ramp intact; calculate this display separately.
    full_config = copy.deepcopy(config)
    if full_config.get("cashflow_schedule"):
        full_config["cashflow_schedule"]["revenue_factors"] = {}
    full_result = calculate_revenue(
        _revenue_project(ctx.report, commercial_text(ctx.state), full_config,
                         basis, hours, {year: Decimal(1) for year in ramp}, {}),
        engineering_scenario=True,
    )
    full = plain(full_result)
    first = next(iter(ramp))
    display["full_operation"] = {
        "basis": full["basis"], "issues": full["issues"],
        "annual": [row for row in full["annual"] if row["year"] == first],
        "products": [{k: row.get(k) for k in ("product_id", "year", "net_sales_revenue", "quantity_sold", "quantity_unit")}
                     for row in full["products"] if row["year"] == first],
        "commercial": [{k: row.get(k) for k in ("line_id", "year", "revenue", "quantity", "quantity_unit", "rate")}
                       for row in full["commercial"] if row["year"] == first],
    }
    display["full_operation_basis"] = {
        "throughput_fraction": "1", "annual_operating_hours": str(hours),
        "description": "100% scheduled operation at saved rates and commercial terms; not a year-one forecast.",
    }
    notice = next((row["notice"] for row in audit if "notice" in row), None)
    if notice:
        display["price_basis_notice"] = notice
    return Product(
        display,
        {
            "revenue": plain(result),
            "schedule": {"hours": str(hours), "ramp": plain(ramp)},
            # Only revenue inputs, so the saved output (and its hash) does not
            # change when unrelated OPEX or finance settings change (G4 F1).
            "config": _revenue_config(config),
        },
        updates,
        complete=not result.issues,
        issues=result.issues,
    )


REVENUE_CONFIG_KEYS = (
    "methodology", "assumption_date", "price_basis", "operating", "sales",
    "commercial_lines", "avoided_costs", "commercial_intent", "cashflow_schedule",
)
REVENUE_SCHEDULE_KEYS = (
    "operating_years", "production_ramp", "construction_years", "calendar_start_year",
)


def _revenue_config(config):
    kept = {k: config[k] for k in REVENUE_CONFIG_KEYS if k in config}
    financial = config.get("financial") or {}
    kept["financial"] = {k: financial[k] for k in REVENUE_SCHEDULE_KEYS if k in financial}
    return kept
