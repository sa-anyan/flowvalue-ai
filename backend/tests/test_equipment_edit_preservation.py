"""One edited cell preserves the remaining saved engineering ledger."""

import copy
from unittest.mock import patch
import pytest
from backend.orchestration.equipment_edits import merge_equipment_edits
from backend.orchestration.service import edit
from backend.blocks.execution import run_stage, view, fresh
from backend.tests.test_isolated_stages import study  # noqa: F401


def test_one_out_of_100_assumptions_changed_and_other_rows_retained():
    original = [
        {
            "equipment_key": "one",
            "unit_conversion": {
                "enabled": True,
                "inputs": {str(n): n for n in range(100)},
                "unit_context": {"basis": "saved"},
            },
            "matching": {"model": "saved"},
        },
        {"equipment_key": "two", "quantity": 2},
    ]
    before = copy.deepcopy(original)
    result = merge_equipment_edits(
        original, [{"equipment_key": "one", "unit_conversion": {"inputs": {"42": 999}}}]
    )
    assert original == before and result[1] == before[1]
    assert result[0]["unit_conversion"]["enabled"]
    assert result[0]["matching"] == before[0]["matching"]
    assert (
        sum(
            v == before[0]["unit_conversion"]["inputs"][k]
            for k, v in result[0]["unit_conversion"]["inputs"].items()
        )
        == 99
    )
    assert (
        merge_equipment_edits(
            result, [{"equipment_key": "one", "unit_conversion": None}]
        )[0]["unit_conversion"]
        is None
    )
    with pytest.raises(ValueError):
        merge_equipment_edits(original, {})


def test_quantity_edit_keeps_prices_visible_and_preserves_sizing_without_ai(study):
    store, key = study
    state = run_stage(store, key, "engineering_data")
    state = run_stage(store, key, "equipment")
    previous = copy.deepcopy(state["plan"]["equipment"])
    oldprice = state["results"]["stages"]["equipment"]["result"]["equipment"][0][
        "equipment_cost"
    ]
    row = previous[0]
    assert oldprice is not None
    changed = edit(
        store,
        key,
        state["revision"],
        "equipment",
        [{"equipment_key": row["equipment_key"], "quantity": 3}],
        "Three units",
    )
    assert changed["plan"]["equipment"][0]["sizing"] == row["sizing"]
    assert changed["results"]["stages"]["equipment"]["result"]["equipment"][0][
        "equipment_cost"
    ] == pytest.approx(oldprice * 3 / row["quantity"])
    assert changed["results"]["stages"]["equipment"]["result_is_stale"] and not fresh(
        changed, "equipment"
    )
    with patch(
        "backend.orchestration.provider.EngineeringProvider",
        side_effect=AssertionError("No LLM"),
    ):
        rerun = run_stage(store, key, "equipment", use_ai=False)
    assert rerun["plan"]["equipment"][0]["sizing"] == row["sizing"]
    assert rerun["results"]["stages"]["equipment"]["result"]["equipment"][0][
        "equipment_cost"
    ] == pytest.approx(oldprice * 3 / row["quantity"])
    assert not rerun["results"]["stages"]["equipment"].get("result_is_stale")


def test_failed_python_rerun_retains_previous_output_as_stale(study):
    store, key = study
    state = run_stage(store, key, "engineering_data")
    state = run_stage(store, key, "equipment")
    old = copy.deepcopy(state["results"]["stages"]["equipment"]["result"])
    with patch(
        "backend.blocks.equipment.runner.calculate",
        side_effect=ValueError("Synthetic failure"),
    ):
        failed = run_stage(store, key, "equipment", use_ai=False)
    assert failed["results"]["stages"]["equipment"]["result"] == old
    assert failed["results"]["stages"]["equipment"]["result_is_stale"]
    assert not fresh(failed, "equipment")


def test_previously_hidden_stale_equipment_is_recovered_without_execution(study):
    store, key = study
    state = run_stage(store, key, "engineering_data")
    state = run_stage(store, key, "equipment")
    old = copy.deepcopy(state["results"]["stages"]["equipment"]["result"])
    state = edit(
        store,
        key,
        state["revision"],
        "equipment",
        [
            {
                "equipment_key": state["plan"]["equipment"][0]["equipment_key"],
                "quantity": 3,
            }
        ],
        "Three units",
    )
    state["results"]["stages"]["equipment"]["result"] = None
    restored = view(state)
    assert restored["results"]["stages"]["equipment"]["result"] == old
    assert restored["results"]["stages"]["equipment"]["result_is_stale"]


def test_save_prices_only_changed_equipment_and_never_runs_ai_or_other_stages(study):
    from backend.blocks.equipment.calculation import calculate_equipment

    store, key = study
    state = run_stage(store, key, "engineering_data")
    state = run_stage(store, key, "equipment")
    row = state["plan"]["equipment"][0]
    original = copy.deepcopy(state["results"]["stages"]["equipment"]["result"])
    receipts = copy.deepcopy(state["stage_runs"])
    with patch(
        "backend.blocks.equipment.edit_preview.calculate_equipment",
        wraps=calculate_equipment,
    ) as calculate, patch(
        "backend.blocks.execution.get_runner",
        side_effect=AssertionError("No stage run"),
    ), patch(
        "backend.orchestration.provider.EngineeringProvider",
        side_effect=AssertionError("No AI"),
    ):
        saved = edit(
            store,
            key,
            state["revision"],
            "equipment",
            [{"equipment_key": row["equipment_key"], "quantity": 4}],
            "Quick quantity sensitivity",
        )
    assert calculate.call_count == 1
    scoped, plan, _ = calculate.call_args.args
    assert [e["key"] for e in scoped["entities"] if e["kind"] == "equipment"] == [
        row["equipment_key"]
    ]
    assert len(plan["equipment"]) == 1
    result = saved["results"]["stages"]["equipment"]["result"]
    for before, after in zip(original["equipment"], result["equipment"]):
        if before["parsed_source"]["equipment_key"] == row["equipment_key"]:
            assert after["equipment_cost"] == pytest.approx(
                before["equipment_cost"] * 4 / row["quantity"]
            )
        else:
            assert after == before
    assert (
        saved["stage_runs"]["equipment"]["completed_at"]
        == receipts["equipment"]["completed_at"]
    )
    assert saved["stage_outputs"] == state["stage_outputs"]
