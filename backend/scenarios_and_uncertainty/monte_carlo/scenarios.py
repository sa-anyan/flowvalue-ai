"""Apply explicit study overrides to a copied plan; never mutate accepted inputs."""

import copy

from backend.equipment_resolution.scope import equipment_paths, expand

from .discovery import get, set_value


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
    if plan.get("operating_economics"):
        plan["operating_economics"]["financial"]["operating_years"] = (
            settings.operating_years
        )
        for key in ("commercial_lines", "avoided_costs"):
            for row in plan["operating_economics"].get(key, []):
                # Never invent extra contract years. Existing shorter schedules remain invalid/pending.
                if len(row.get("years", [])) > settings.operating_years:
                    row["years"] = row["years"][: settings.operating_years]
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
