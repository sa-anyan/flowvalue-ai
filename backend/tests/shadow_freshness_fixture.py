"""Test-only comparison. Production isolated-stage freshness stays authoritative."""

from backend.blocks import execution
from backend.orchestration.calculation_receipts import evaluate_lifecycle, required_stage_graph


def compare_freshness(
    state, scope, history, current_inputs, *, current_methods=None,
    missing_observation_stages=(), graph=None,
):
    """Compare existing evidence supplied by fixtures, without synthesizing receipts."""
    if state["id"] != scope.assessment_id:
        raise ValueError("Frozen assessment does not match the receipt scope")
    stage_views = (state.get("results") or {}).get("stages", {})
    saved_outputs = state.get("stage_outputs", {})
    legacy_outputs = set(saved_outputs) | {
        name for name, stage in stage_views.items() if stage.get("result") is not None
    }
    b09 = evaluate_lifecycle(
        scope, required_stage_graph(state) if graph is None else graph,
        history, current_inputs, current_methods=current_methods, legacy_outputs=legacy_outputs,
    )
    result = {}
    for stage, view in b09.items():
        registered = stage in execution.BLOCKS
        legacy_fresh = execution.fresh(state, stage) if registered else None
        legacy_run = state.get("stage_runs", {}).get(stage, {})
        legacy_reason = None
        if not registered:
            legacy_reason = "No production stage definition"
        elif not legacy_fresh:
            if legacy_run.get("status") != "ready":
                legacy_reason = "Latest legacy stage status is not ready"
            elif stage not in saved_outputs:
                legacy_reason = "Legacy stage payload is absent"
            elif legacy_run.get("input_hash") != execution.input_fingerprint(state, stage):
                legacy_reason = "Legacy input or upstream fingerprint differs"
            else:
                legacy_reason = "A required legacy upstream stage is not fresh"
        gaps = []
        if stage in missing_observation_stages:
            gaps.append("Consumed source-observation evidence was not captured")
        if view.provenance.state == "unknown":
            gaps.extend(view.provenance.reasons)
        if view.freshness.state == "unknown":
            gaps.extend(view.freshness.reasons)
        disagreement = []
        if view.freshness.state == "unknown" or legacy_fresh != (view.freshness.state == "current"):
            disagreement.append(f"Legacy freshness is {legacy_fresh}; B09 numerical freshness is {view.freshness.state}")
            if legacy_reason:
                disagreement.append(legacy_reason)
            disagreement.extend(view.freshness.reasons)
        if view.provenance.state == "changed":
            disagreement.extend(view.provenance.reasons)
        if view.active_completeness == "partial" and legacy_fresh:
            disagreement.append("Legacy freshness can be true for a partial result")
        if view.active_receipt_id and view.active_receipt_id != view.latest_attempt_id:
            disagreement.append("B09 evaluates the retained output separately from the latest attempt")
        result[stage] = {
            "legacy_fresh": legacy_fresh,
            "legacy_status": legacy_run.get("status"),
            "legacy_complete": legacy_run.get("complete"),
            "b09": view,
            "evidence_gaps": tuple(dict.fromkeys(gaps)),
            "disagreement": tuple(disagreement),
        }
    return result
