"""Explicit, approved downstream batch using the same independent stage runners."""

from datetime import datetime, timezone
from .execution import fresh, run_stage, _digest

ORDER = ("equipment", "capex", "revenue", "opex", "financial")


def approved(state):
    return fresh(state, "engineering_data") and state.get(
        "engineering_approval", {}
    ).get("fingerprint") == _digest(
        state.get("stage_outputs", {}).get("engineering_data")
    )


def approve(store, key, revision):
    state = store.get(key)
    if state["revision"] != revision or state.get("running"):
        raise ValueError("Assessment changed or is running; reload before approving")
    if not fresh(state, "engineering_data"):
        raise ValueError("Extract engineering data before approving")
    store.version(key, "Before engineering data approval")
    state["engineering_approval"] = {
        "fingerprint": _digest(state["stage_outputs"]["engineering_data"]),
        "approved_at": datetime.now(timezone.utc).isoformat(),
    }
    return store.put(state, revision)


def queue(store, key):
    state = store.get(key)
    if state.get("running"):
        raise ValueError("Another stage is running")
    if not approved(state):
        raise ValueError(
            "Review and approve Engineering Data before running downstream stages"
        )
    store.version(key, "Before run all stages")
    state["stage_workflow"] = {
        "status": "running",
        "stage": ORDER[0],
        "order": list(ORDER),
        "completed": [],
    }
    state.update(running=True, queued_stage=ORDER[0])
    return store.put(state, state["revision"])


def run(store, key, *, use_ai=False, provider=None):
    """No extraction rerun, no automatic revenue approval, no alternate calculators."""
    try:
        for stage in ORDER:
            state = store.get(key)
            state["stage_workflow"].update(stage=stage)
            state.update(running=True, queued_stage=stage)
            store.put(state, state["revision"])
            state = run_stage(store, key, stage, use_ai=use_ai, provider=provider)
            state["stage_workflow"]["completed"].append(
                {"stage": stage, "status": state["stage_runs"][stage]["status"]}
            )
            store.put(state, state["revision"])
        state = store.get(key)
        state["stage_workflow"]["status"] = (
            "complete"
            if all(fresh(state, stage) for stage in ORDER)
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
