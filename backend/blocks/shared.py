"""Shared serialization, source context and proposal adapters; no stage execution."""

import copy
import json
import re
from backend.orchestration.codec import construct, plain
from .models import DataRequired


def canonical(cls, payload):
    return construct(cls, payload)


def require_operating(ctx):
    config = copy.deepcopy(ctx.operating)
    if not config:
        raise DataRequired(
            "Data required: enter this stage’s operating assumptions, prices, schedule and price basis."
        )
    config.pop("_revenue_authority", None)
    return config


def basis_and_schedule(ctx, config):
    from backend.opex.models import Basis
    from backend.orchestration.operating_economics import operating_schedule

    try:
        basis = Basis(**config["price_basis"])
        hours, ramp = operating_schedule(config)
    except (ValueError, TypeError, KeyError) as exc:
        raise DataRequired(
            "Data required: supply currency, price period, operating days/hours, plant life and production ramp. "
            + str(exc)
        ) from exc
    return basis, hours, ramp


def proposal(ctx, sections, *, basis_only=False, allow_missing_opex=False):
    """A selected block may request a proposal; other blocks' outputs are never run."""
    if not ctx.use_ai:
        return {}, {}
    from backend.orchestration.advisor import propose

    parsed = {
        "report": ctx.report,
        "effective_report": ctx.report,
        "source_cells": ctx.upstream.get("engineering_data", {}).get(
            "source_cells", []
        ),
        "source_cells_truncated": ctx.upstream.get("engineering_data", {}).get(
            "source_cells_truncated", False
        ),
        "revenue_box": ctx.state.get("revenue_description", ""),
    }
    from backend.orchestration.provider import EngineeringProvider

    provider = ctx.provider or EngineeringProvider()
    locked = ctx.state.get("locked", [])
    if allow_missing_opex:
        locked = [section for section in locked if section != "operating_economics"]
    response, meta = propose(
        parsed,
        ctx.state.get("description", ""),
        ctx.plan,
        locked,
        ctx.store,
        provider,
        requested_sections=tuple(sections),
        stage_results={
            key: {"result": value.get("result")}
            for key, value in ctx.state.get("results", {}).get("stages", {}).items()
            if not basis_only or key == "capex"
        },
    )
    return {
        v["section"]: json.loads(v["value_json"]) for v in response["sections"]
    }, meta


def operating_proposal(ctx, owner):
    from backend.blocks.cashflow.schedule import apply_policy

    config = apply_policy(ctx.operating or {}, ctx.state.get("analysis_schedule"))
    if not isinstance(config, dict):
        raise DataRequired(
            "Data required: operating assumptions must be a structured object."
        )
    opex_fields = ("materials", "energy", "labour", "additional_expenses", "garrett_factors")
    locked = "operating_economics" in ctx.state.get("locked", [])
    fill_locked_opex = owner == "opex" and locked and any(field not in config for field in opex_fields)
    if not ctx.use_ai or (locked and not fill_locked_opex):
        return config, {}
    capital = ctx.state.get("results", {}).get("stages", {}).get("capex", {}).get("result") or {}
    sections = ("revenue", "opex")
    if owner == "revenue" and not (capital.get("currency") and capital.get("period")):
        sections = ("revenue",)
    proposed, meta = proposal(ctx, sections, basis_only=True, allow_missing_opex=fill_locked_opex)
    value = proposed.get("operating_economics", {})
    owned = {
        "revenue": (
            "sales",
            "commercial_lines",
            "avoided_costs",
            "commercial_intent",
            "pending_inputs",
            "questions",
            "intent_source",
        ),
        "opex": (*opex_fields, "scope_notes"),
    }[owner]
    for field in owned:
        if field not in value or (fill_locked_opex and field in config):
            continue
        config[field] = copy.deepcopy(value[field])
        proposed_basis = value.get("price_basis")
        if (
            owner == "opex" and field in opex_fields[:-1] and proposed_basis
            and config.get("price_basis") and proposed_basis != config["price_basis"]
        ):
            for item in config[field]:
                item.setdefault("price_basis", copy.deepcopy(proposed_basis))
    # Shared inputs may be initially proposed but are never silently replaced by another block.
    for field in (
        "methodology",
        "assumption_date",
        "origin",
        "price_basis",
        "operating",
        "financial",
    ):
        if field == "financial" and value.get(field):
            config[field] = {**value[field], **config.get(field, {})}
        elif not config.get(field) and value.get(field):
            config[field] = value[field]
    if owner == "opex":
        from backend.blocks.execution import fresh

        # Missing revenue/capital bases are pending lines, not a reason to skip
        # unrelated raw materials, utilities and labour calculations.
        for key in ("capex", "revenue"):
            if fresh(ctx.state, key) and key not in ctx.upstream:
                ctx.upstream[key] = copy.deepcopy(ctx.state["stage_outputs"][key])
    return apply_policy(config, ctx.state.get("analysis_schedule")), meta


from decimal import Decimal
from backend.revenue.models import Assumption
from backend.opex.consumption import decimal


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
    return hours, production_schedule(config)


def production_schedule(config):
    life = int(config["financial"]["operating_years"])
    if life != config["financial"]["operating_years"] or not 1 <= life <= 50:
        raise ValueError("Integer operating life from 1–50 years required")
    ramp = [decimal(x, maximum=1) for x in config["financial"]["production_ramp"]]
    if not ramp:
        raise ValueError("Explicit production ramp required")
    return {i: ramp[min(i - 1, len(ramp) - 1)] for i in range(1, life + 1)}


def translate_inputs(ctx, config, owner):
    """Rebase this block's prices only; never inspect another block's missing prices."""
    policy = ctx.plan.get("cost_translation")
    if not policy or policy.get("enabled") is False:
        return config, []
    from backend.equipment_costing.cost_to_future.cost_translation import (
        MissingIndexObservation,
        numeric,
        price_years,
        year,
    )
    from backend.equipment_costing.cost_to_future.operating_prices import (
        translate_operating_prices,
    )

    groups = {
        "revenue": ("sales", "commercial_lines", "avoided_costs"),
        "opex": ("materials", "energy", "labour", "additional_expenses"),
        "financial": ("financial",),
    }[owner]
    basis = config.get("price_basis") or {}
    target_currency = basis.get("currency")
    if owner == "financial":
        financial = config.get("financial") or {}
        closure = financial.get("closure_allowance")
        if closure is None or numeric(closure) == 0:
            return config, []
        basis = financial.get("price_basis") or basis
        try:
            year(basis.get("price_period"))
        except ValueError as exc:
            raise DataRequired(
                "Enter a dated price basis for the closure allowance in Financial "
                "assumptions, or select the project price basis."
            ) from exc
        capital = ctx.upstream.get("capex", {}).get("capital", {})
        target_currency = capital.get("currency") or target_currency or basis.get("currency")
    target = {
        "currency": target_currency,
        "price_period": policy.get("target_period"),
    }

    notice = None
    if owner == "revenue" and not price_years(basis.get("price_period")):
        # The project basis is an allowed fallback only when the user explicitly
        # chose it. Operating years, units and billing periods are not price dates.
        selected = re.search(
            r"(?:^|[.!?]\s+|\n)\s*use\s+(?:the\s+)?(?:project(?:['’]s)?\s+)?saved\s+(?:project\s+)?(?:([A-Z]{3})\s+)?price\s+basis\b",
            ctx.state.get("revenue_description", ""),
            re.IGNORECASE,
        )
        if (
            not selected
            or not basis.get("currency")
            or (selected[1] and selected[1].upper() != basis["currency"])
            or not re.fullmatch(r"\d{4}(?:-(?:0[1-9]|1[0-2]))?", str(target["price_period"]))
        ):
            raise ValueError(
                "Revenue needs a dated price basis (YYYY or YYYY-MM). Enter it under "
                "Review & calculate → Edit assumptions, or explicitly choose the saved project price basis."
            )
        year(target["price_period"])
        basis = target
        notice = f"Revenue uses the saved project price basis ({basis['currency']} {basis['price_period']}), as requested in the Revenue Box."
    part = {"price_basis": basis, **{k: config[k] for k in groups if k in config}}

    try:
        changed, audit = translate_operating_prices(part, target_basis=target, policy=policy)
    except MissingIndexObservation:
        if owner != "revenue":
            raise
        # Keep the approved scenario basis when its index observation is unavailable.
        changed, audit = translate_operating_prices(
            part, target_basis=basis, policy={**policy, "target_period": basis["price_period"]}
        )
        audit.append({
            "notice": "Revenue uses the approved price period because an index observation is unavailable."
        })
    if notice:
        audit.append({"notice": notice, "original_price_basis": config.get("price_basis")})
    result = copy.deepcopy(config)
    result.update(changed)
    return result, audit
