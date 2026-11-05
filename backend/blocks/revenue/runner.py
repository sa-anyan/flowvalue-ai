"""Revenue-only execution from approved user intent and source quantities."""

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
            "text": ctx.state.get("revenue_description", ""),
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
            ctx.state.get("revenue_description", ""),
            config,
            basis,
            hours,
            ramp,
            {},
        ),
        engineering_scenario=True,
    )
    return Product(
        plain(result),
        {
            "revenue": plain(result),
            "schedule": {"hours": str(hours), "ramp": plain(ramp)},
            "config": {k: v for k, v in config.items() if k != "_revenue_authority"},
        },
        updates,
        complete=not result.issues,
        issues=result.issues,
    )
