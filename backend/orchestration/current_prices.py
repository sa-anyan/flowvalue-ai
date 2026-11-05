"""Read-only current-price calculation view; saved inputs and evidence stay intact."""

import copy
import json
from functools import lru_cache

from backend.equipment_costing.cost_to_future.cost_translation import DEFAULT_POLICY
from .pipeline import run


@lru_cache(maxsize=8)
def _calculate(payload):
    report, description, plan = json.loads(payload)
    return run(report, description, plan)


def current_price_view(saved):
    """All live views use the same saved-stage policy, regardless of workbook age."""
    from backend.blocks.execution import view

    return view(saved)


def _legacy_current_price_view_for_reference(saved):
    """Historical price-view regression reference; never called by live routes."""
    state = copy.deepcopy(saved)
    if state.get("execution_mode") == "isolated_stages_v1":
        from backend.blocks.execution import view

        return view(state)
    from backend.revenue.authority import bind, questions

    bind(state)
    report = (
        state.get("scoped_report")
        or state.get("effective_report")
        or state.get("parsed", {}).get("report")
    )
    if "revenue_description" in state:
        state["revenue_questions"] = questions(
            state.get("plan", {}).get("operating_economics", {}),
            state.get("revenue_description", ""),
            report or {},
            approval=state.get("revenue_approval"),
        )
        if state.get("results") and state["revenue_questions"]:
            for name in ("revenue", "financial"):
                state["results"].setdefault("stages", {})[name] = {
                    "status": "pending_user_input",
                    "result": None,
                    "issues": state["revenue_questions"],
                }
    if state.get("running") or not state.get("results"):
        return state
    policy = state.get("plan", {}).get("cost_translation", {})
    if policy.get("enabled") is False:
        state["price_view"] = {
            "status": "historical",
            "notice": "Historical price basis explicitly selected.",
        }
        return state
    report = (
        state.get("scoped_report")
        or state.get("effective_report")
        or state.get("parsed", {}).get("report")
    )
    if not report:
        state["price_view"] = {
            "status": "unavailable",
            "notice": "Current-price recalculation requires the saved engineering report.",
        }
        return state
    plan = copy.deepcopy(state["plan"])
    plan["cost_translation"] = {**DEFAULT_POLICY, **policy}
    # No provider calls, source edits, baseline writes or display-only multipliers.
    results = _calculate(
        json.dumps([report, state.get("description", ""), plan], sort_keys=True)
    )
    state["results"] = copy.deepcopy(results)
    state["price_view"] = {
        "status": "recalculated",
        "target_period": plan["cost_translation"]["target_period"],
        "notice": "Current-price calculation view. Original saved assumptions and historical source prices are retained. CPI purchasing-power proxy where a native equipment index is unavailable; not a vendor quotation.",
    }
    return state
