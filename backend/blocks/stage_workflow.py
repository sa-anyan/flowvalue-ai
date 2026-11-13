"""Explicit, approved downstream batch using the same independent stage runners."""

from datetime import datetime, timezone
from .execution import fresh, run_stage, _digest

ORDER = ("equipment", "capex", "revenue", "opex", "financial")
ECONOMIC_ORDER = ("capex", "revenue", "opex", "financial")


def approved(state):
    return fresh(state, "engineering_data") and state.get(
        "engineering_approval", {}
    ).get("fingerprint") == _digest(
        state.get("stage_outputs", {}).get("engineering_data")
    )


class AssessmentBusy(ValueError):
    """The assessment is being written by a running workflow; retry when idle."""


def running_work(state):
    """Name of the workflow currently writing this assessment, or None.

    Equipment preparation after extraction runs with ``running`` already False,
    so the workflow statuses are checked as well.
    """
    for name in ("engineering_workflow", "stage_workflow"):
        workflow = state.get(name) or {}
        if workflow.get("status") == "running":
            return workflow.get("stage") or name
    if state.get("running"):
        return state.get("queued_stage") or "a stage"
    return None


def approve(store, key, revision):
    state = store.get(key)
    busy = running_work(state)
    if busy:
        raise AssessmentBusy(
            f"Engineering data cannot be approved while {busy.replace('_', ' ')} "
            "is still running; wait for it to finish, reload and approve again"
        )
    if state["revision"] != revision:
        raise ValueError("Assessment changed or is running; reload before approving")
    if not fresh(state, "engineering_data"):
        raise ValueError("Extract engineering data before approving")
    store.version(key, "Before engineering data approval")
    state["engineering_approval"] = {
        "fingerprint": _digest(state["stage_outputs"]["engineering_data"]),
        "approved_at": datetime.now(timezone.utc).isoformat(),
    }
    state = store.put(state, revision)
    _brainstorm(store, key)
    return state


def _brainstorm(store, key):
    """Start the background OPEX brainstorm for newly approved data (AI only)."""
    try:
        from backend.blocks.opex.brainstorm import kick

        kick(store, key)
    except Exception:
        pass  # the reference defaults still cover OPEX without the AI


def queue(store, key, *, economic_only=False):
    state = store.get(key)
    if state.get("running"):
        raise ValueError("Another stage is running")
    if not approved(state):
        raise ValueError(
            "Review and approve Engineering Data before running downstream stages"
        )
    _brainstorm(store, key)
    order = ECONOMIC_ORDER if economic_only and fresh(state, "equipment") else ORDER
    store.version(
        key,
        "Before coordinated economics" if economic_only else "Before run all stages",
    )
    state["stage_workflow"] = {
        "status": "running",
        "stage": order[0],
        "order": list(order),
        "completed": [],
    }
    state.update(running=True, queued_stage=order[0])
    return store.put(state, state["revision"])


def run(store, key, *, use_ai=False, provider=None):
    """No extraction rerun, no automatic revenue approval, no alternate calculators."""
    try:
        order = tuple(store.get(key)["stage_workflow"]["order"])
        for stage in order:
            state = store.get(key)
            state["stage_workflow"].update(stage=stage)
            state.update(running=True, queued_stage=stage)
            store.put(state, state["revision"])
            stage_ai = use_ai and not (
                stage == "revenue" and state.get("revenue_approval")
            )
            state = run_stage(store, key, stage, use_ai=stage_ai, provider=provider)
            state["stage_workflow"]["completed"].append(
                {"stage": stage, "status": state["stage_runs"][stage]["status"]}
            )
            store.put(state, state["revision"])
        state = store.get(key)
        state["stage_workflow"]["status"] = (
            "complete"
            if all(
                fresh(state, stage) and state["stage_runs"][stage].get("complete", True)
                for stage in order
            )
            else "needs_review"
        )
        state["status"] = (
            "Stage run complete; review partial or missing results"
            if state["stage_workflow"]["status"] == "needs_review"
            else "All stages calculated"
        )
        state["running"] = False
        return store.put(state, state["revision"])
    except Exception:
        state = store.get(key)
        state["stage_workflow"]["status"] = "failed"
        state["running"] = False
        state.pop("queued_stage", None)
        store.put(state, state["revision"])
        raise
