from copy import deepcopy

import pytest

from backend.blocks import execution
from backend.orchestration.calculation_receipts import CalculationScope, semantic_digest
from backend.orchestration.store import dump
from backend.tests.shadow_freshness_fixture import compare_freshness
from backend.tests.test_calculation_receipts import SCOPE, inputs, method, receipt
from backend.tests.test_execution_observation import fresh_stage


def frozen_study(scope=SCOPE):
    state = execution.initialize({
        "id": scope.assessment_id, "revision": 7, "source_sha256": "workbook-a",
        "plan": {"equipment": [{"equipment_key": "E1", "size": 4}]},
    })
    payload = {"report": {"entities": []}}
    equipment = {"total": "125.50"}
    fresh_stage(state, "engineering_data", payload)
    fresh_stage(state, "equipment", equipment)
    state["results"]["stages"]["equipment"] = {"result": {"equipment_cost_total": "125.50"}}
    data = receipt("engineering_data", scope=scope, methods=(method(),),
                   input_digest=semantic_digest({"source": state["source_sha256"]}),
                   output_digest=semantic_digest(payload))
    result = receipt("equipment", data, scope=scope, methods=(method(),),
                     input_digest=semantic_digest(state["plan"]["equipment"]),
                     output_digest=semantic_digest(equipment))
    return state, data, result


def compare_unchanged(state, scope, history, current, **kwargs):
    before = dump(state)
    evidence = tuple(run.model_dump_json() for run in history)
    views = compare_freshness(state, scope, history, current, **kwargs)
    assert dump(state) == before
    assert tuple(run.model_dump_json() for run in history) == evidence
    return views


def test_matching_source_and_output_digests():
    state, data, equipment = frozen_study()
    row = compare_unchanged(state, SCOPE, (data, equipment), inputs(data, equipment),
                            current_methods={"equipment": equipment.methods})["equipment"]
    assert row["legacy_fresh"]
    assert row["b09"].freshness.state == "current"
    assert row["b09"].provenance.state == "matching"
    assert row["disagreement"] == ()


@pytest.mark.parametrize("change", ["source", "equipment_input", "upstream_output"])
def test_edit_and_upstream_change_stale_in_both_models(change):
    state, data, equipment = frozen_study()
    current = inputs(data, equipment)
    history = (data, equipment)
    if change == "source":
        state["source_sha256"] = "workbook-b"
        current["engineering_data"] = (semantic_digest({"source": "workbook-b"}), None)
    elif change == "equipment_input":
        state["plan"]["equipment"][0]["size"] = 8
        current["equipment"] = (semantic_digest(state["plan"]["equipment"]), None)
    else:
        payload = {"report": {"entities": [{"key": "changed"}]}}
        fresh_stage(state, "engineering_data", payload)
        history += (data.model_copy(update={
            "receipt_id": "new-data", "output_digest": semantic_digest(payload),
        }),)
    row = compare_unchanged(state, SCOPE, history, current)["equipment"]
    assert not row["legacy_fresh"]
    assert row["b09"].freshness.state == "stale"
    assert row["b09"].freshness.reasons


def test_equivalent_upstream_result_preserves_numerics_with_changed_method_lineage():
    state, data, equipment = frozen_study()
    replacement = data.model_copy(update={"receipt_id": "new-data", "methods": (method("2"),)})
    row = compare_unchanged(state, SCOPE, (data, equipment, replacement), inputs(replacement, equipment),
                            current_methods={"equipment": equipment.methods})["equipment"]
    assert row["legacy_fresh"] and row["b09"].freshness.state == "current"
    assert row["b09"].provenance.state == "changed"
    assert row["disagreement"] == ("engineering_data: upstream method identity changed",)


@pytest.mark.parametrize("outcome", ["failed", "blocked"])
def test_retained_output_keeps_latest_attempt_separate(outcome):
    state, data, equipment = frozen_study()
    state["stage_runs"]["equipment"]["status"] = "data_required"
    latest = receipt("equipment", data, receipt_id="latest", outcome=outcome, output_digest=None)
    row = compare_unchanged(state, SCOPE, (data, equipment, latest), inputs(data, equipment),
                            current_methods={"equipment": equipment.methods})["equipment"]
    assert not row["legacy_fresh"]
    assert row["b09"].latest_outcome == outcome
    assert row["b09"].active_receipt_id == equipment.receipt_id
    assert row["b09"].freshness.state == "current"
    assert "retained output" in " ".join(row["disagreement"])


def test_partial_upstream_with_equal_digest_requires_completeness_evidence():
    state, data, equipment = frozen_study()
    state["stage_runs"]["engineering_data"]["complete"] = False
    partial = data.model_copy(update={"receipt_id": "partial", "outcome": "partial"})
    views = compare_unchanged(state, SCOPE, (data, equipment, partial), inputs(partial, equipment))
    assert views["engineering_data"]["b09"].active_completeness == "partial"
    assert views["engineering_data"]["legacy_complete"] is False
    row = views["equipment"]
    assert row["legacy_fresh"] and row["b09"].freshness.state == "unknown"
    assert "partial output" in " ".join(row["disagreement"])


def test_optional_opex_basis_supplied_versus_consumed():
    state, data, _ = frozen_study()
    fresh_stage(state, "opex", {"years": {}})
    opex = receipt("opex", data)
    revenue_payload = {"revenue": {"amount": "10"}}
    rev = receipt("revenue", data, output_digest=semantic_digest(revenue_payload))
    fresh_stage(state, "revenue", revenue_payload)
    row = compare_unchanged(state, SCOPE, (data, opex, rev), inputs(data, opex, rev))["opex"]
    assert not row["legacy_fresh"] and row["b09"].freshness.state == "current"
    consumed = receipt("opex", data, rev)
    fresh_stage(state, "opex", {"years": {}})
    replacement = {"revenue": {"amount": "20"}}
    fresh_stage(state, "revenue", replacement)
    changed = rev.model_copy(update={"receipt_id": "revised-revenue", "output_digest": semantic_digest(replacement)})
    row = compare_unchanged(state, SCOPE, (data, rev, consumed, changed), inputs(data, consumed, changed))["opex"]
    assert not row["legacy_fresh"] and row["b09"].freshness.state == "stale"


def test_missing_observation_evidence_and_legacy_receipts():
    state, data, equipment = frozen_study()
    missing = compare_unchanged(state, SCOPE, (data, equipment), inputs(data),
                                missing_observation_stages=("equipment",))["equipment"]
    assert missing["legacy_fresh"] and missing["b09"].freshness.state == "unknown"
    assert "Consumed source-observation evidence was not captured" in missing["evidence_gaps"]
    legacy = compare_unchanged(state, SCOPE, (), {})["equipment"]
    assert legacy["legacy_fresh"] and legacy["b09"].freshness.state == "unknown"
    assert legacy["b09"].active_receipt_id is None
    assert legacy["b09"].active_methods == ()


def test_unregistered_stage_unknown_and_cycle_rejected_without_mutation():
    state, data, equipment = frozen_study()
    future = receipt("future")
    row = compare_unchanged(state, SCOPE, (future,), inputs(future))["future"]
    assert row["legacy_fresh"] is None and row["b09"].freshness.state == "unknown"
    before = dump(state)
    with pytest.raises(ValueError, match="Dependency cycle"):
        compare_freshness(state, SCOPE, (data, equipment), inputs(data, equipment),
                          graph={"engineering_data": ("equipment",), "equipment": ("engineering_data",)})
    assert dump(state) == before


def test_scenario_frozen_baseline_reference_survives_original_edit():
    scenario = CalculationScope(assessment_id=SCOPE.assessment_id, scenario_id="job-a")
    baseline, _, _ = frozen_study()
    _, data, equipment = frozen_study(scenario)
    frozen = {"snapshot_id": "snapshot-a", "baseline_revision": baseline["revision"],
              "assessment": deepcopy(baseline)}
    before = dump(frozen)
    expected = compare_unchanged(frozen["assessment"], scenario, (data, equipment), inputs(data, equipment))
    baseline["revision"] += 1
    baseline["source_sha256"] = "new-workbook"
    baseline["plan"]["equipment"][0]["size"] = 9
    baseline["stage_outputs"]["equipment"]["total"] = "900"
    assert dump(frozen) == before
    assert frozen["baseline_revision"] == 7 and frozen["snapshot_id"] == "snapshot-a"
    assert compare_unchanged(frozen["assessment"], scenario, (data, equipment), inputs(data, equipment)) == expected
    assert frozen["assessment"]["stage_outputs"]["equipment"]["total"] == "125.50"
    assert expected["equipment"]["b09"].freshness.state == "current"
