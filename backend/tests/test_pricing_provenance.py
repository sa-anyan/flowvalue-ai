"""Focused provenance checks; no workbook values are used as expected estimates."""

import pytest

from backend.equipment_costing.manual import manual_result
from backend.orchestration.service import edit
from backend.orchestration.store import Store


def imported():
    return {
        "amount": 123.0,
        "currency": "USD",
        "price_period": "1987",
        "source": "Task 2 Charlie Economics 2(3).xlsx!C13",
        "notes": "Synthetic test value, not the workbook price",
        "approved": True,
        "cost_scope": "purchased_equipment",
        "cost_status": "project_benchmark",
    }


def test_seeded_approval_does_not_establish_user_price():
    with pytest.raises(ValueError, match="reference-only"):
        manual_result(imported())


def test_explicit_user_reapproval_is_recorded_by_edit_endpoint(tmp_path):
    store = Store(tmp_path / "study.sqlite3")
    row = {"equipment_key": "test", "manual_price": imported()}
    state = store.create(
        {
            "running": False,
            "plan": {"equipment": [row]},
            "locked": [],
            "assumptions": {},
        },
        b"",
    )
    price = imported()
    price["approval_requested"] = True
    updated = edit(
        store,
        state["id"],
        state["revision"],
        "equipment",
        [{**row, "manual_price": price}],
        "I explicitly accept this historical input for this scenario",
    )
    accepted = updated["plan"]["equipment"][0]["manual_price"]
    assert (
        accepted["approval_origin"] == "explicit_user_edit"
        and "approval_requested" not in accepted
    )
    assert manual_result(accepted).equipment_cost == 123


def test_previous_capex_cannot_be_an_automatic_equipment_price():
    value = imported()
    value.update(
        source="Saved project capital total",
        cost_origin="previous_capex",
        cost_status="estimate",
    )
    with pytest.raises(ValueError, match="reference-only"):
        manual_result(value)


def test_editing_notes_does_not_silently_approve_an_imported_price(tmp_path):
    store = Store(tmp_path / "study.sqlite3")
    row = {"equipment_key": "test", "manual_price": imported()}
    state = store.create(
        {
            "running": False,
            "plan": {"equipment": [row]},
            "locked": [],
            "assumptions": {},
        },
        b"",
    )
    value = imported()
    value["notes"] = "Changed only the explanatory note"
    updated = edit(
        store,
        state["id"],
        0,
        "equipment",
        [{**row, "manual_price": value}],
        "Review note only",
    )
    with pytest.raises(ValueError, match="reference-only"):
        manual_result(updated["plan"]["equipment"][0]["manual_price"])
