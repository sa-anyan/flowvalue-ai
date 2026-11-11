from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.orchestration.calculation_receipts import (
    CalculationReceipt,
    CalculationScope,
    MethodIdentity,
    UpstreamReceipt,
    evaluate_dependencies,
    required_stage_graph,
    semantic_digest,
)
from backend.orchestration.store import Store


SCOPE = CalculationScope(assessment_id="assessment-a")
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def receipt(stage, *upstream, scope=SCOPE, **fields):
    return CalculationReceipt(**{
        "scope": scope,
        "stage": stage,
        "receipt_id": stage + "-1",
        "executed_at": NOW,
        "input_revision": 2,
        "input_digest": semantic_digest({"stage": stage}),
        "output_digest": semantic_digest({"result": stage}),
        "outcome": "ready",
        "upstream": tuple(UpstreamReceipt(
            scope=r.scope, stage=r.stage, receipt_id=r.receipt_id, output_digest=r.output_digest
        ) for r in upstream),
        **fields,
    })


def inputs(*receipts):
    return {r.stage: (r.input_digest, r.configuration_digest) for r in receipts}


def test_canonical_digest_and_method_identity():
    first = {"scope": "vessel", "value": Decimal("1.20"), "tags": ["A", "B"]}
    assert semantic_digest(first) == semantic_digest({
        "tags": ["A", "B"], "value": "1.20", "scope": "vessel"
    })
    assert semantic_digest(first) != semantic_digest({**first, "value": Decimal("1.21")})
    assert semantic_digest(first) != semantic_digest({**first, "tags": ["B", "A"]})
    method = MethodIdentity(method_id="vessel_hold_up", method_version="1.0.0",
                            implementation_fingerprint="sha256:observed",
                            fingerprint_scheme="flowvalue-loaded-engineering-v1",
                            execution_layer="native")
    baseline = semantic_digest({"method": method.model_dump(mode="json")})
    for change in ({"method_version": "2.0.0"}, {"implementation_fingerprint": "sha256:different"}):
        changed = method.model_copy(update=change)
        assert baseline != semantic_digest({"method": changed.model_dump(mode="json")})
    with pytest.raises(ValueError):
        semantic_digest({"value": float("nan")})


def test_direct_transitive_and_unaffected_invalidation():
    graph = required_stage_graph({})
    data = receipt("engineering_data")
    equipment = receipt("equipment", data)
    capex = receipt("capex", equipment)
    revenue = receipt("revenue", data)
    opex = receipt("opex", data)
    finance = receipt("financial", capex, revenue, opex)
    captured = (data, equipment, capex, revenue, opex, finance)
    current = inputs(*captured)
    assert all(s.state == "current" for s in evaluate_dependencies(SCOPE, graph, captured, current).values())
    current["equipment"] = (semantic_digest({"equipment:e1": "changed"}), None)
    statuses = evaluate_dependencies(SCOPE, graph, captured, current)
    assert statuses["equipment"].reasons == ("Input or configuration digest changed",)
    assert statuses["capex"].reasons == ("equipment: upstream is stale",)
    assert statuses["financial"].reasons == ("capex: upstream is stale",)
    assert statuses["revenue"].state == statuses["opex"].state == "current"


def test_optional_dependency_and_identical_upstream_rerun():
    graph = required_stage_graph({})
    data = receipt("engineering_data")
    revenue = receipt("revenue", data)
    opex = receipt("opex", data, revenue)
    rerun = receipt("revenue", data, receipt_id="revenue-2")
    checks = inputs(data, rerun, opex)
    assert evaluate_dependencies(SCOPE, graph, (data, rerun, opex), checks)["opex"].state == "current"
    changed = receipt("revenue", data, receipt_id="revenue-3", output_digest=semantic_digest(5))
    assert evaluate_dependencies(SCOPE, graph, (data, changed, opex), checks)["opex"].reasons == (
        "revenue: upstream output digest changed",
    )


def test_cycle_in_effective_graph_is_rejected():
    data = receipt("engineering_data")
    equipment = receipt("equipment", data)
    with pytest.raises(ValueError, match="Dependency cycle"):
        evaluate_dependencies(SCOPE, {"engineering_data": ("equipment",)}, (equipment,), {})


@pytest.mark.parametrize("other", [
    CalculationScope(assessment_id="assessment-b"),
    CalculationScope(assessment_id="assessment-a", scenario_id="scenario-b"),
])
def test_receipts_are_isolated_by_assessment_and_scenario(other):
    data = receipt("engineering_data", scope=other)
    with pytest.raises(ValidationError, match="different calculation scope"):
        receipt("equipment", data)
    local = receipt("equipment", receipt("engineering_data"))
    statuses = evaluate_dependencies(SCOPE, required_stage_graph({}), (data, local), inputs(local))
    assert statuses["engineering_data"].state == "missing"
    assert statuses["equipment"].state == "unknown"
    assert statuses["equipment"].reasons == ("engineering_data: upstream is missing",)


def test_legacy_and_failed_receipts_cannot_look_current():
    failed = receipt("capex", outcome="failed", output_digest=None)
    statuses = evaluate_dependencies(SCOPE, required_stage_graph({}), (failed,), {}, legacy_outputs=("equipment",))
    assert statuses["equipment"].state == "unknown"
    assert statuses["equipment"].reasons == ("Legacy output has no versioned receipt",)
    assert statuses["capex"].state == "missing"
    assert statuses["capex"].reasons == ("Execution outcome: failed",)
    previous = evaluate_dependencies(SCOPE, required_stage_graph({}), (failed,), {}, legacy_outputs=("capex",))
    assert previous["capex"].state == "unknown"


def test_missing_recorded_edge_and_current_inputs_are_unknown():
    equipment = receipt("equipment")
    state = evaluate_dependencies(SCOPE, required_stage_graph({}), (equipment,), {})
    assert state["equipment"].state == "unknown"
    assert state["equipment"].reasons == (
        "Current input identity unavailable",
        "engineering_data: original upstream receipt reference unavailable",
    )


@pytest.mark.parametrize("versioned", [True, False])
def test_named_snapshot_round_trip_preserves_original_receipt_and_bytes(tmp_path, versioned):
    store = Store(tmp_path / "assessment.sqlite")
    saved = store.create({"results": {"cost": "125.50"}}, b"fixture")
    scope = CalculationScope(assessment_id=saved["id"])
    original = receipt("equipment", scope=scope)
    if versioned:
        saved["calculation_receipts"] = [original.model_dump(mode="json")]
        saved = store.put(saved, saved["revision"])
    version = store.version(saved["id"], "Before edit")

    def snapshot():
        with store.db() as db:
            return db.execute("SELECT state FROM versions WHERE id=?", (version,)).fetchone()[0]

    before = snapshot()
    reopened = store.load(version)
    assert reopened["results"] == saved["results"]
    assert snapshot() == before
    assert store.get(saved["id"]) == saved
    if versioned:
        assert CalculationReceipt.model_validate(reopened["calculation_receipts"][0]) == original
        assert reopened["id"] != original.scope.assessment_id
    else:
        assert "calculation_receipts" not in reopened
        state = evaluate_dependencies(scope, required_stage_graph({}), (), {}, legacy_outputs=("equipment",))
        assert state["equipment"].state == "unknown"


def method(version="1"):
    return MethodIdentity(
        method_id="vessel_hold_up", method_version=version,
        implementation_fingerprint=f"sha256:method-{version}",
        fingerprint_scheme="flowvalue-loaded-engineering-v1", execution_layer="native",
    )


@pytest.mark.parametrize(("change", "freshness", "provenance"), [
    ("none", "current", "matching"),
    ("input", "current", "changed"),
    ("method", "current", "changed"),
    ("output", "stale", "matching"),
])
def test_lifecycle_equivalent_upstream_reruns(change, freshness, provenance):
    from backend.orchestration.calculation_receipts import evaluate_lifecycle

    original = receipt("engineering_data", methods=(method(),))
    dependent = receipt("equipment", original, methods=(method(),))
    changes = {
        "none": {},
        "input": {"input_digest": semantic_digest("changed input")},
        "method": {"methods": (method("2"),)},
        "output": {"output_digest": semantic_digest("changed output")},
    }
    rerun = original.model_copy(update={"receipt_id": "engineering_data-2", **changes[change]})
    views = evaluate_lifecycle(
        SCOPE, required_stage_graph({}), (original, dependent, rerun, rerun),
        inputs(rerun, dependent), current_methods={"equipment": (method(),)},
    )
    assert views["equipment"].freshness.state == freshness
    assert views["equipment"].provenance.state == provenance
    assert views["engineering_data"].active_receipt_id == rerun.receipt_id
    assert views["engineering_data"].superseded_receipt_ids == (original.receipt_id,)


@pytest.mark.parametrize("outcome", ["failed", "blocked"])
def test_lifecycle_retains_output_without_claiming_changed_inputs_current(outcome):
    from backend.orchestration.calculation_receipts import evaluate_lifecycle

    original = receipt("engineering_data", methods=(method(),))
    attempt = receipt("engineering_data", receipt_id="attempt-2", outcome=outcome, output_digest=None)
    graph = required_stage_graph({})
    retained = evaluate_lifecycle(SCOPE, graph, (original, attempt), inputs(original),
                                  current_methods={"engineering_data": (method(),)})["engineering_data"]
    assert retained.active_receipt_id == original.receipt_id
    assert retained.latest_attempt_id == attempt.receipt_id
    assert retained.latest_outcome == outcome
    assert retained.freshness.state == "current"
    changed = evaluate_lifecycle(SCOPE, graph, (original, attempt),
                                 {"engineering_data": (semantic_digest("edited input"), None)})["engineering_data"]
    assert changed.freshness.state == "stale"
    changed_method = evaluate_lifecycle(SCOPE, graph, (original, attempt), inputs(original),
                                        current_methods={"engineering_data": (method("2"),)})["engineering_data"]
    assert changed_method.freshness.state == "unknown"
    assert changed_method.provenance.state == "changed"
    assert changed_method.approval_status == "unknown"


def test_lifecycle_partial_is_active_and_complete_output_is_retained():
    from backend.orchestration.calculation_receipts import evaluate_lifecycle

    complete = receipt("engineering_data")
    partial = receipt("engineering_data", receipt_id="partial-2", outcome="partial")
    result = evaluate_lifecycle(SCOPE, required_stage_graph({}), (complete, partial), inputs(partial))["engineering_data"]
    assert result.active_receipt_id == partial.receipt_id
    assert result.previous_complete_receipt_id == complete.receipt_id
    assert result.active_completeness == "partial"
    assert result.freshness.state == "current"
    assert result.provenance.state == "unknown"


def test_lifecycle_missing_original_lineage_and_legacy_output():
    from backend.orchestration.calculation_receipts import evaluate_lifecycle

    original = receipt("engineering_data", methods=(method(),))
    rerun = original.model_copy(update={"receipt_id": "engineering_data-2"})
    dependent = receipt("equipment", original, methods=(method(),))
    results = evaluate_lifecycle(
        SCOPE, required_stage_graph({}), (rerun, dependent), inputs(rerun, dependent),
        current_methods={"equipment": (method(),)}, legacy_outputs=("capex",),
    )
    assert results["equipment"].freshness.state == "current"
    assert results["equipment"].provenance.state == "unknown"
    assert "engineering_data: original receipt unavailable" in results["equipment"].provenance.reasons
    assert results["capex"].freshness.state == "unknown"


def test_lifecycle_rejects_reused_receipt_id_and_ignores_foreign_attempts():
    from backend.orchestration.calculation_receipts import evaluate_lifecycle

    local = receipt("engineering_data")
    conflict = local.model_copy(update={"input_digest": semantic_digest("different")})
    graph = required_stage_graph({})
    with pytest.raises(ValueError, match="Conflicting immutable receipt"):
        evaluate_lifecycle(SCOPE, graph, (local, conflict), inputs(local))
    for other in (CalculationScope(assessment_id="other"), SCOPE.model_copy(update={"scenario_id": "alt"})):
        foreign = receipt("engineering_data", scope=other, receipt_id="foreign")
        view = evaluate_lifecycle(SCOPE, graph, (local, foreign), inputs(local))["engineering_data"]
        assert view.latest_attempt_id == local.receipt_id


def test_lifecycle_fork_keeps_parent_receipt_as_original_lineage(tmp_path):
    from backend.orchestration.calculation_receipts import evaluate_lifecycle

    store = Store(tmp_path / "fork.sqlite")
    original = store.create({"results": {"cost": "20"}}, b"fixture")
    scope = CalculationScope(assessment_id=original["id"])
    run = receipt("equipment", scope=scope)
    original["calculation_receipts"] = [run.model_dump(mode="json")]
    saved = store.put(original, original["revision"])
    version = store.version(saved["id"], "Before fork")
    fork = store.load(version)
    history = tuple(CalculationReceipt.model_validate(r) for r in fork["calculation_receipts"])
    assert history == (run,)
    views = evaluate_lifecycle(CalculationScope(assessment_id=fork["id"]), required_stage_graph({}),
                               history, {}, legacy_outputs=("equipment",))
    assert views["equipment"].active_receipt_id is None
    assert views["equipment"].freshness.state == "unknown"
    assert store.get(saved["id"]) == saved

@pytest.mark.parametrize("later_version", ["1", "2", None])
def test_later_attempt_never_certifies_current_method(later_version):
    from backend.orchestration.calculation_receipts import evaluate_lifecycle

    active = receipt("engineering_data", methods=(method(),))
    later = receipt("engineering_data", receipt_id="later", outcome="failed", output_digest=None,
                    methods=(method(later_version),) if later_version else ())
    views = evaluate_lifecycle(SCOPE, required_stage_graph({}), (active, later), inputs(active))
    result = views["engineering_data"]
    assert result.freshness.state == "unknown"
    assert result.provenance.state == "unknown"
    assert result.active_methods == active.methods
    assert result.latest_attempt_methods == later.methods
    assert result.current_methods is None


def test_incomplete_independent_method_evidence_cannot_fall_back_to_attempt():
    from backend.orchestration.calculation_receipts import evaluate_lifecycle

    active = receipt("engineering_data", methods=(method(),))
    later = receipt("engineering_data", receipt_id="later", outcome="blocked", output_digest=None,
                    methods=active.methods)
    incomplete = method().model_copy(update={"method_version": None})
    result = evaluate_lifecycle(SCOPE, required_stage_graph({}), (active, later), inputs(active),
                                current_methods={"engineering_data": (incomplete,)})["engineering_data"]
    assert result.provenance.state == "unknown"
    assert result.freshness.state == "unknown"
    assert result.current_methods == (incomplete,)


@pytest.mark.parametrize("invalid", ["stage", "digest", "order"])
def test_present_upstream_reference_must_match_earlier_history(invalid):
    from backend.orchestration.calculation_receipts import evaluate_lifecycle

    upstream = receipt("engineering_data")
    downstream = receipt("equipment", upstream)
    if invalid == "order":
        history = (downstream, upstream)
    else:
        changes = {"stage": "revenue"} if invalid == "stage" else {"output_digest": semantic_digest("wrong")}
        wrong = downstream.upstream[0].model_copy(update=changes)
        history = (upstream, downstream.model_copy(update={"upstream": (wrong,)}))
    with pytest.raises(ValueError, match="Invalid upstream receipt"):
        evaluate_lifecycle(SCOPE, required_stage_graph({}), history, inputs(upstream, downstream))


def test_unknown_stage_requires_explicit_graph_registration():
    from backend.orchestration.calculation_receipts import evaluate_lifecycle

    future = receipt("future_stage")
    graph = required_stage_graph({})
    result = evaluate_lifecycle(SCOPE, graph, (future,), inputs(future))["future_stage"]
    assert result.freshness.state == "unknown"
    assert result.active_receipt_id == future.receipt_id
    registered = evaluate_lifecycle(SCOPE, {**graph, "future_stage": ()}, (future,), inputs(future))
    assert registered["future_stage"].freshness.state == "current"


@pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_wire_digest_rejects_non_finite_decimals(value):
    with pytest.raises(ValueError, match="finite"):
        semantic_digest({"nested": [value]})


@pytest.mark.parametrize("bad", ["sha256:short", "sha512:" + "0" * 64, "sha256:" + "0" * 64 + "\n"])
def test_receipts_and_current_observations_reject_malformed_digests(bad):
    with pytest.raises(ValidationError):
        receipt("engineering_data", input_digest=bad)
    with pytest.raises(ValidationError):
        evaluate_dependencies(SCOPE, required_stage_graph({}), (), {"engineering_data": (bad, None)})


def test_lifecycle_partial_replacement_does_not_certify_complete_dependency():
    from backend.orchestration.calculation_receipts import evaluate_lifecycle

    complete = receipt("engineering_data", methods=(method(),))
    downstream = receipt("equipment", complete, methods=(method(),))
    partial = complete.model_copy(update={"receipt_id": "partial-2", "outcome": "partial"})
    views = evaluate_lifecycle(SCOPE, required_stage_graph({}), (complete, downstream, partial),
                               inputs(partial, downstream), current_methods={"equipment": downstream.methods})
    assert views["engineering_data"].active_completeness == "partial"
    assert views["equipment"].freshness.state == "unknown"
    assert "partial output" in " ".join(views["equipment"].freshness.reasons)
