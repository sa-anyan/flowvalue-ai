"""The Entry workflow explicitly connects extraction to canonical equipment costs."""

from unittest.mock import patch

from backend.blocks.engineering_workflow import queue, run
from backend.blocks.execution import fresh, view
from backend.tests.test_isolated_stages import study  # noqa: F401 -- pytest fixture


def test_entry_runs_data_then_prices_equipment_only(study):
    store, key = study
    queue(store, key)
    with patch(
        "backend.blocks.capex.runner.calculate", side_effect=AssertionError("No CAPEX")
    ), patch(
        "backend.blocks.revenue.runner.calculate",
        side_effect=AssertionError("No revenue"),
    ), patch(
        "backend.blocks.opex.runner.calculate", side_effect=AssertionError("No OPEX")
    ), patch(
        "backend.blocks.financial.runner.calculate",
        side_effect=AssertionError("No finance"),
    ):
        state = run(store, key)
    assert fresh(state, "engineering_data") and fresh(state, "equipment")
    assert set(state["stage_outputs"]) == {"engineering_data", "equipment"}
    assert any(
        row["equipment_cost"] is not None
        for row in state["results"]["stages"]["equipment"]["result"]["equipment"]
    )
    assert not state["running"]
    assert state["engineering_workflow"]["status"] == "ready"


def test_failed_extraction_does_not_run_equipment(study):
    store, key = study
    queue(store, key)
    with patch(
        "backend.blocks.engineering_data.runner.parse",
        side_effect=ValueError("Malformed workbook"),
    ), patch(
        "backend.blocks.equipment.runner.calculate",
        side_effect=AssertionError("Do not use stale data"),
    ):
        state = run(store, key)
    assert state["engineering_workflow"]["status"] == "data_required"
    assert not state["running"] and "equipment" not in state["stage_outputs"]


def test_polling_remains_active_between_connected_stages(study):
    store, key = study
    state = queue(store, key)
    state["running"] = False
    assert view(state)["running"] is True


def test_initial_run_populates_assumptions_and_prices_in_one_pass(study):
    from backend.tests.test_automatic_equipment_inputs import decision

    store, key = study
    state = store.get(key)
    state["plan"]["equipment"] = []
    state["locked"] = []
    store.put(state, state["revision"])

    class Provider:
        model = "test-no-network"

        def generate(self, *, instructions, context, schema):
            if context["task"].startswith("equipment-concept-matcher"):
                return {
                    "matches": [
                        {
                            "equipment_key": row["equipment_key"],
                            "equipment_function": "Liquid storage",
                            "match_status": "matched",
                            "match_method": "semantic_equivalence",
                            "candidate_model_ids": ["G303-144"],
                            "selected_model_id": "G303-144",
                            "model_scope": "equipment",
                            "conceptual_validation": "suitable",
                            "reason": "Explicit synthetic storage-tank match.",
                            "caveats": [],
                            "context_evidence_ids": [],
                        }
                        for row in context["equipment_register"]
                    ]
                }
            assert context["task"].startswith("equipment-input-resolution")
            rows = []
            for item in context["equipment"]:
                row = decision(item["equipment_key"])
                row["model_id"] = "G303-144"
                row["measurement_id"] = next(
                    v["id"]
                    for v in item["measurements"]
                    if v["property"] == "mass_flow"
                )
                rows.append(row)
            return {"decisions": rows}

    def review(parsed, *args):
        return parsed["report"], {}, [], {"status": "test extraction review"}

    queue(store, key)
    with patch("backend.orchestration.workbook_review.review", side_effect=review):
        result = run(store, key, use_ai=True, provider=Provider())
    assert set(result["stage_outputs"]) == {"engineering_data", "equipment"}
    assert all(s["use_ai"] for s in result["stage_runs"].values())
    assert any(
        p.get("unit_conversion", {}).get("enabled") for p in result["plan"]["equipment"]
    )
    assert any(
        e["equipment_cost"] is not None
        for e in result["results"]["stages"]["equipment"]["result"]["equipment"]
    )
