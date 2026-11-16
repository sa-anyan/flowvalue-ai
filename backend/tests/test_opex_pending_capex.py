"""OPEX can prepare assumptions before CAPEX and calculate after it finishes."""

import copy
import json

import pytest

from backend.blocks.models import Context
from backend.blocks.opex.runner import calculate
from backend.opex.reference_defaults import for_study, resolve_price_basis
from backend.orchestration.codec import plain
from backend.orchestration.operating_advisor import generate
from backend.tests.test_operating_economics import fixture


@pytest.mark.parametrize("saved", [None, {}, {"currency": None, "price_period": None}, {"currency": "USD"}])
def test_completed_capex_fills_empty_basis_without_changing_prices(saved):
    original = {"price_basis": saved, "materials": [{"id": "feed", "unit_price": 0}]}
    before = copy.deepcopy(original)
    config, _ = for_study(original, {}, [], {"currency": "USD", "period": "2026-09"})
    assert config["price_basis"] == {"currency": "USD", "price_period": "2026-09"}
    assert config["materials"] == original["materials"]
    assert original == before


def test_saved_historical_basis_is_never_relabelled_as_completed_capex():
    config = {"price_basis": {"currency": "GBP", "price_period": "2020"}}
    updated, _ = for_study(config, {}, [], {"currency": "USD", "period": "2026-09"})
    assert updated["price_basis"] == config["price_basis"]
    assert resolve_price_basis({}, {}, {}) == {"currency": None, "price_period": None}


@pytest.mark.parametrize("currency", ["USD", "GBP"])
def test_background_ai_receives_project_basis_before_capex_and_keeps_it(monkeypatch, currency):
    from backend.orchestration import operating_advisor, reference_repair

    # This response exercises the adapter, not external AI or market research.
    response = {"financial": {}, "questions": [], "commercial_intent": {"questions": []},
                "materials": [{"id": "feed", "unit_price": 0.5, "unit_price_currency": currency}]}
    monkeypatch.setattr(operating_advisor, "validate", lambda *args: None)
    monkeypatch.setattr("backend.revenue.commercial_intent.validate_intent", lambda *args, **kwargs: None)
    monkeypatch.setattr(reference_repair, "repair", lambda value, *args: value)
    monkeypatch.setattr(reference_repair, "repair_energy", lambda value, *args: value)

    class Provider:
        def generate(self, *, instructions, context, schema):
            assert context["operating_price_basis"] == {"currency": "USD", "price_period": "2026-09"}
            assert "do not omit them merely because CAPEX totals are pending" in instructions
            return copy.deepcopy(response)

    context = {"plan": {"cost_translation": {"target_period": "2026-09"}},
               "report": {"entities": [], "connections": []}}
    before = copy.deepcopy(context)
    result = generate(Provider(), "", context)
    config = json.loads(result["sections"][0]["value_json"])
    assert config["price_basis"] == {"currency": "USD", "price_period": "2026-09"}
    from backend.currency_conversion import convert_currency
    from backend.blocks.opex.brainstorm import merge
    expected = float(convert_currency(0.5, currency, "USD")["amount"])
    assert config["materials"][0]["unit_price"] == expected
    if currency != "USD":
        saved, _ = merge({}, config)
        audit = saved["materials"][0]["fx_conversion"]
        assert audit["source_currency"] == currency and audit["original_amount"] == "0.5"
        assert audit["rate_date"] and audit["source"]
    assert context == before


def test_run_opex_uses_saved_capex_and_recalculates_factors_without_ai():
    report, config, capital = fixture()
    config["price_basis"] = {"currency": None, "price_period": None}
    state = {"plan": {"operating_economics": config,
                      "cost_translation": {"target_period": capital.period}},
             "results": {"stages": {"capex": {"result": plain(capital)}}}}
    before = copy.deepcopy(state)
    ctx = Context(state, report, {"capex": {"capital": plain(capital)}}, None)
    first = calculate(ctx)
    assert first.result["currency"] == capital.currency
    assert first.result["known_cash_opex_subtotal"] is not None
    # A changed saved CAPEX feeds the same OPEX assumptions on the next click.
    larger = copy.deepcopy(ctx.upstream)
    larger["capex"]["capital"]["fixed_capital"] = str(capital.fixed_capital * 2)
    second = calculate(Context(state, report, larger, None))
    assert float(second.result["known_cash_opex_subtotal"]) > float(first.result["known_cash_opex_subtotal"])
    assert state == before
