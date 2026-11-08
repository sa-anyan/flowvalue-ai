"""Explicit Entry action: engineering extraction followed by equipment pricing only."""

from .execution import fresh, queue_stage, run_stage


def queue(store, key):
    state = queue_stage(store, key, "engineering_data")
    state["engineering_workflow"] = {"status": "running", "stage": "engineering_data"}
    return store.put(state, state["revision"])


def run(store, key, *, use_ai=False, provider=None, prepare_only=False):
    try:
        state = run_stage(
            store, key, "engineering_data", use_ai=use_ai, provider=provider
        )
        if not fresh(state, "engineering_data"):
            status = "data_required"
        elif prepare_only:
            from .models import Context
            from .equipment.runner import prepare

            state["engineering_workflow"]["stage"] = "equipment_preparation"
            state = store.put(state, state["revision"])
            report = state["stage_outputs"]["engineering_data"]["report"]
            ctx = Context(
                state=state,
                report=report,
                upstream={},
                store=store,
                provider=provider,
                use_ai=use_ai,
            )
            _, plan, _, issues, matching, inputs, drops = prepare(ctx)
            state["plan"]["equipment"] = plan.get("equipment", [])
            state["equipment_preparation"] = {
                "status": "ready",
                "matching_register": matching,
                "input_resolution": inputs,
                "duplicate_review": drops,
                "issues": issues,
            }
            status = "ready"
        else:
            state["engineering_workflow"]["stage"] = "equipment"
            state = store.put(state, state["revision"])
            state = run_stage(store, key, "equipment", use_ai=use_ai, provider=provider)
            status = "ready" if fresh(state, "equipment") else "data_required"
        state["engineering_workflow"]["status"] = status
        state["status"] = (
            (
                "Engineering data prepared for equipment review"
                if prepare_only
                else "Engineering data and equipment pricing complete"
            )
            if status == "ready"
            else "Engineering workflow needs input; review stage details"
        )
        state["running"] = False
        return store.put(state, state["revision"])
    except Exception:
        state = store.get(key)
        state["engineering_workflow"] = {"status": "failed"}
        state["running"] = False
        state.pop("queued_stage", None)
        store.put(state, state["revision"])
        raise
