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
