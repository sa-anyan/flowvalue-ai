"""A price edit preserves payment identity, updates evidence and needs new approval."""
import copy
from pathlib import Path
import tempfile

import pytest

from backend.orchestration.service import new_assessment, edit
from backend.orchestration.store import Store
from backend.revenue.authority import update, questions
from backend.revenue.price_edits import reconcile_product_price
from backend.tests.test_revenue_authority import ready

ORIGINAL = "Sell product for $15/kg"


def product():
    report, config, _ = ready()
    for entity in report["entities"]:
        if entity["key"] == config["sales"][0]["stream_key"]:
            entity["values"][0].update(property="mass_flow", normalized_unit="kg/h")
    config["commercial_lines"] = []
    config["commercial_intent"]["mechanisms"] = config["commercial_intent"]["mechanisms"][:1]
    config["commercial_intent"]["mechanisms"][0]["context_quote"] = ORIGINAL
    config["sales"][0].update(context_quote=ORIGINAL, unit_price=15, quantity_unit="kg")
    return report, config


@pytest.mark.parametrize("text,expected", [("Sell product for $20/kg", 20), ("Sell product for $0/kg", 0), ("Sell product for $15.00/kg", 15)])
def test_price_only_change_updates_price_and_both_exact_quotes(text, expected):
    report, config = product()
    changed = reconcile_product_price(config, ORIGINAL, text)
    assert changed["sales"][0]["unit_price"] == expected
    assert changed["sales"][0]["stream_key"] == config["sales"][0]["stream_key"]
    assert changed["sales"][0]["context_quote"] == text
    assert changed["commercial_intent"]["mechanisms"][0]["context_quote"] == text
    assert not questions(changed, text, report, require_approval=False)
    assert config["sales"][0]["unit_price"] == 15


@pytest.mark.parametrize("text", ["Do not sell product for $20/kg", "Charge treatment fees for $20/kg", "Sell product for $20/t", "Sell product for £20/kg", "Sell product for $20/kg and sell waste for $5/kg"])
def test_semantic_currency_unit_and_multiple_price_changes_are_not_rebound(text):
    _, config = product()
    assert reconcile_product_price(config, ORIGINAL, text) is None


def test_ambiguous_products_and_preconverted_prices_are_not_overwritten():
    _, config = product()
    multiple = copy.deepcopy(config)
    multiple["sales"].append(copy.deepcopy(multiple["sales"][0]))
    assert reconcile_product_price(multiple, ORIGINAL, "Sell product for $20/kg") is None
    config["price_basis"]["currency"] = "GBP"
    assert reconcile_product_price(config, ORIGINAL, "Sell product for $20/kg") is None


def test_resaving_repairs_a_box_that_already_has_stale_quotes():
    report, config = product()
    text = "Sell product for $20/kg"
    changed = reconcile_product_price(config, text, text)
    assert changed["sales"][0]["unit_price"] == 20
    assert not questions(changed, text, report, require_approval=False)


def test_save_and_reapprove_price_change_works_without_ai_or_recreating_sale():
    report, config = product()
    with tempfile.TemporaryDirectory() as folder:
        store = Store(Path(folder) / "test.db")
        state = new_assessment(store, b"fixture", "fixture.xlsx", "Protein process", ORIGINAL, workflow="revenue")
        state.update(parsed={"report": report}, plan={"operating_economics": config}, running=False)
        state = store.put(state, state["revision"])
        state = update(store, state["id"], state["revision"], approve=True)
        state = update(store, state["id"], state["revision"], text="Sell product for $20/kg")
        assert not state.get("revenue_approval")
        assert state["plan"]["operating_economics"]["sales"][0]["unit_price"] == 20
        assert len(state["revenue_questions"]) == 1
        assert "approve" in state["revenue_questions"][0]
        state = update(store, state["id"], state["revision"], approve=True)
        assert not state["revenue_questions"]


def test_structured_price_edit_keeps_its_source_quote_and_requires_reapproval():
    report, config = product()
    with tempfile.TemporaryDirectory() as folder:
        store = Store(Path(folder) / "test.db")
        state = new_assessment(store, b"fixture", "fixture.xlsx", "Protein process", ORIGINAL, workflow="revenue")
        state.update(parsed={"report": report}, plan={"operating_economics": config}, running=False)
        state = store.put(state, state["revision"])
        state = update(store, state["id"], state["revision"], approve=True)
        changed = copy.deepcopy(config)
        changed["sales"][0]["unit_price"] = 20
        state = edit(store, state["id"], state["revision"], "operating_economics", changed, "User changed the selling price")
        assert state["plan"]["operating_economics"]["sales"][0]["context_quote"] == ORIGINAL
        missing = questions(state["plan"]["operating_economics"], ORIGINAL, report, approval=state["revenue_approval"])
        assert len(missing) == 1 and "approve" in missing[0]
        state = update(store, state["id"], state["revision"], approve=True)
        assert not state["revenue_questions"]
