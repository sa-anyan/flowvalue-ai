"""Apply explicit study overrides to a copied plan; never mutate accepted inputs."""

import copy

from backend.equipment_resolution.scope import equipment_paths, expand

from .discovery import get, set_value


def resolve_horizon(state, settings):
    """Distinguish omission from an explicit integer, including a saved legacy 20.

    Keep the existing Settings wire schema/default; Pydantic tracks supplied fields.
    No approved baseline or contract rows are changed by resolution.
    """
    project = (
        state.get("plan", {})
        .get("operating_economics", {})
        .get("financial", {})
        .get("operating_years")
    )
    supplied_fields = getattr(settings, "model_fields_set", None)
    # Older internal adapters use plain namespaces with an explicitly set value.
    explicit = (
        "operating_years" in supplied_fields
        if supplied_fields is not None
        else hasattr(settings, "operating_years")
    )
    selected = settings.operating_years if explicit or project is None else project
    if type(selected) is not int or not 1 <= selected <= 50:
        raise ValueError(
            "An unambiguous operating horizon from 1 to 50 years is required"
        )
    return {
        "operating_years": selected,
        "project_operating_years": project,
        "requested_operating_years": settings.operating_years if explicit else None,
        "selection": (
            "explicit"
            if explicit
            else (
                "project"
                if project is not None
                else "legacy_default_no_project_horizon"
            )
        ),
    }


def resolved_settings(state, settings):
    """Freeze the effective integer before settings are serialized to a job."""
    return settings.model_copy(
        update={"operating_years": resolve_horizon(state, settings)["operating_years"]}
    )


def _annual_rows(rows):
    """Validate identities before any explicit shorter scenario selects its years."""
    if not isinstance(rows, list):
        raise ValueError("Commercial annual schedule must be a list")
    years = [row.get("year") if isinstance(row, dict) else None for row in rows]
    if any(type(y) is not int or not 1 <= y <= 50 for y in years):
        raise ValueError(
            "Commercial years must be operating-year indexes 1–50, not calendar dates"
        )
    if len(set(years)) != len(years) or years != sorted(years):
        raise ValueError(
            "Commercial annual years must be unique and in increasing order"
        )
    return years


def prepare(state, settings):
    from backend.revenue.authority import bind, runtime

    state = bind(copy.deepcopy(state))
    plan = copy.deepcopy(state["plan"])
    report = (
        state.get("scoped_report")
        or state.get("effective_report")
        or state["parsed"]["report"]
    )
    plan.pop("_monte_carlo_revenue_approved", None)
    if plan.get("revenue_authority") and plan.get("operating_economics"):
        # Carry authorization only from the unchanged, approved snapshot. It
        # covers sensitivity calculations on the copy, never a saved approval.
        plan["_monte_carlo_revenue_approved"] = not runtime(
            plan["operating_economics"], plan["revenue_authority"], report
        )["questions"]
    from backend.equipment_costing.cost_to_future.cost_translation import DEFAULT_POLICY

    plan.setdefault("cost_translation", copy.deepcopy(DEFAULT_POLICY))
    horizon = resolve_horizon(state, settings)
    horizon["excluded_schedule_years"] = []
    plan["_monte_carlo_horizon"] = horizon
    if plan.get("operating_economics"):
        plan["operating_economics"]["financial"]["operating_years"] = horizon[
            "operating_years"
        ]
        project_years = horizon["project_operating_years"]
        shortening = (
            horizon["selection"] == "explicit"
            and type(project_years) is int
            and horizon["operating_years"] < project_years
        )
        for key in ("commercial_lines", "avoided_costs"):
            for row in plan["operating_economics"].get(key, []):
                years = _annual_rows(row.get("years", []))
                # Only an explicitly shorter scenario can select a subset. Gaps
                # remain gaps; never extend, renew, reorder or replace with zero.
                if shortening:
                    excluded = [y for y in years if y > horizon["operating_years"]]
                    if excluded:
                        horizon["excluded_schedule_years"].append(
                            {"kind": key, "id": row.get("id"), "years": excluded}
                        )
                    row["years"] = [
                        r
                        for r in row.get("years", [])
                        if r["year"] <= horizon["operating_years"]
                    ]
    by_key = {
        row["equipment_key"]: get(plan, path) for path, row in equipment_paths(plan)
    }
    report, _ = expand(report, plan)
    registered = {e["key"] for e in report["entities"] if e["kind"] == "equipment"}
    aliases = {a.equipment_key: a for a in settings.aliases}
    distinct = {d.equipment_key: d for d in settings.distinct}
    if len(distinct) != len(settings.distinct) or set(distinct) & set(aliases):
        raise ValueError("Equipment cannot be both alias and distinct")
    for key, decision in distinct.items():
        if key not in by_key or key not in registered:
            raise ValueError("Distinct decision must reference a registered equipment")
        by_key[key].update(
            scope_decision="include",
            alias_of=None,
            alias_confirmation={
                "status": "user_confirmed_distinct",
                "rationale": decision.rationale,
            },
        )
    if len(aliases) != len(settings.aliases):
        raise ValueError("Duplicate alias decision")
    if any(
        key not in registered
        or a.target_key not in registered
        or key not in by_key
        or a.target_key not in by_key
        for key, a in aliases.items()
    ):
        raise ValueError("Alias must reference registered equipment records")
    for key, a in aliases.items():
        if (
            key not in by_key
            or a.target_key not in by_key
            or key == a.target_key
            or key not in registered
            or a.target_key not in registered
        ):
            raise ValueError("Alias target must be a different registered equipment")
        visited = {key}
        target = a.target_key
        while target in aliases:
            if target in visited:
                raise ValueError("Cyclic equipment aliases")
            visited.add(target)
            target = aliases[target].target_key
        if by_key[target].get("scope_decision") == "alias" and target not in aliases:
            raise ValueError("Alias chain ends at an unconfirmed alias")
        by_key[key].update(
            scope_decision="alias",
            alias_of=target,
            alias_confirmation={
                "status": "user_confirmed_for_simulation",
                "rationale": a.rationale,
            },
        )
    # Expand only explicitly enabled default CAPEX factors in this copied plan.
    # They are already registered by canonical discovery and schema-validated.
    from .discovery import discover

    defaults = {p["id"]: p for p in discover(state)["settings"]["parameters"]}
    for parameter in getattr(settings, "parameters", ()):
        if not parameter.enabled or parameter.id not in defaults:
            continue
        for target in defaults[parameter.id]["targets"]:
            if len(target) == 3 and target[:2] == ["capex", "selected_factors"]:
                plan.setdefault("capex", {}).setdefault(
                    "selected_factors", {}
                ).setdefault(target[2], defaults[parameter.id]["mode"])
    # Sampled ranges are not recalculated as low/high endpoint envelopes in every iteration.
    for _, row in equipment_paths(plan):
        for value in (row.get("sizing") or {}).get("parameters", {}).values():
            if isinstance(value, dict):
                value.pop("low", None)
                value.pop("high", None)
    return plan


def apply(plan, parameters, draw):
    for p, value in zip(parameters, draw):
        value = value.item() if hasattr(value, "item") else value
        for target in p.targets:
            if (
                len(target) == 6
                and target[:2] == ["operating_economics", "commercial_lines"]
                and target[3] == "years"
                and target[4] >= len(get(plan, target[:4]))
            ):
                continue  # Explicitly shortened study horizon.
            set_value(plan, target, value)
