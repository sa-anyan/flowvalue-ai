"""Explicit assumption proposals, saved for review without executing calculations."""

import copy
from .models import Context, DataRequired
from .execution import fresh, _apply, refresh
from .shared import proposal, operating_proposal


def prepare_stage(store, key, stage, provider=None):
    if stage not in {"capex", "opex"}:
        raise ValueError("Only CAPEX and OPEX assumption preparation is supported")
    state = store.get(key)
    required = "equipment" if stage == "capex" else "engineering_data"
    if not fresh(state, required):
        raise DataRequired("Run " + required + " before preparing these assumptions")
    upstream = {
        k: copy.deepcopy(v)
        for k, v in state.get("stage_outputs", {}).items()
        if fresh(state, k)
    }
    ctx = Context(
        state=state,
        report=upstream.get("engineering_data", {}).get("report", {}),
        upstream=upstream,
        store=store,
        provider=provider,
        use_ai=True,
    )
    if stage == "capex":
        if "capex" in state.get("locked", []):
            changes = {"capex": state["plan"].get("capex", {})}
        else:
            values, _ = proposal(ctx, ("capex",))
            changes = {"capex": values.get("capex", state["plan"].get("capex", {}))}
    else:
        try:
            config, _ = operating_proposal(ctx, "opex")
        except DataRequired as exc:
            # Draft factors can be reviewed before their capital/revenue bases exist.
            config = exc.updates.get("plan", {}).get("operating_economics")
            if config is None:
                raise
        changes = {"operating_economics": config}
    _apply(state, stage, {"plan": changes})
    refresh(state)
    state.setdefault("stage_preparations", {})[stage] = {
        "status": "ready",
        "notice": "Assumptions proposed for review; calculation has not run",
    }
    state["running"] = False
    return store.put(state, state["revision"])
