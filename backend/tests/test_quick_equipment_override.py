"""Cost model shortcut uses the existing explicit-user price ledger and Python stage."""

import copy
from unittest.mock import patch
import pytest
from backend.tests.test_isolated_stages import study  # noqa: F401
from backend.blocks.execution import run_stage
from backend.orchestration.service import edit


def test_override_save_recalculate_and_return_to_model_without_ai(study):
    store, key = study
    state = run_stage(store, key, "engineering_data")
    state = run_stage(store, key, "equipment")
    original = copy.deepcopy(state["plan"]["equipment"])
    rows = copy.deepcopy(original)
    rows[0].update(
        quantity=2,
        manual_price=dict(
            amount=1234,
            currency="USD",
            calculation_currency="USD",
            price_period="2026-09",
            cost_scope="purchased_equipment",
            source="User-entered equipment price override",
            notes="Synthetic user input",
            approved=True,
            approval_requested=True,
            locked=True,
            installation_factor=1.5,
            installation_rationale="Explicit retained test factor",
        ),
    )
    state = edit(
        store,
        key,
        state["revision"],
        "equipment",
        rows,
        "User changed purchase price in Cost model",
    )
    assert (
        state["plan"]["equipment"][0]["manual_price"]["approval_origin"]
        == "explicit_user_edit"
    )
    with patch(
        "backend.orchestration.provider.EngineeringProvider",
        side_effect=AssertionError("No LLM"),
    ):
        state = run_stage(store, key, "equipment", use_ai=False)
    line = state["results"]["stages"]["equipment"]["result"]["equipment"][0]
    assert line["equipment_cost"] == 2468
    assert line["installation_cost"] == 1234
    assert line["equipment_and_installation_cost"] == 3702
    assert line["calculation"]["estimate"]["period"] == "2026-09"
    assert state["stage_runs"]["equipment"]["use_ai"] is False
    assert state["plan"]["equipment"][0]["manual_price"]["locked"]
    original[0]["manual_price"] = None
    state = edit(
        store, key, state["revision"], "equipment", original, "Return to model pricing"
    )
    with patch(
        "backend.orchestration.provider.EngineeringProvider",
        side_effect=AssertionError("No LLM"),
    ):
        state = run_stage(store, key, "equipment", use_ai=False)
    assert not state["plan"]["equipment"][0].get("manual_price")
    assert (
        state["results"]["stages"]["equipment"]["result"]["equipment"][0][
            "equipment_cost"
        ]
        is not None
    )
