"""Rate-based revenue: real canonical engines, no AI/network arithmetic."""

import copy
from decimal import Decimal as D
from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from backend.tests.test_isolated_stages import study
from backend.blocks.execution import run_stage
from backend.revenue.rate_workspace import RateLine, RateStudyRequest, save_rates
from backend.revenue.indexes.openpytea.rate_model import (
    hourly_rate,
    annual_manual_quantity,
    manual_observation,
)
from backend.revenue.explicit_rates import explicit_rates


def custom():
    return {
        "id": "user-water",
        "quantity_unit": "m3",
        "manual_rate": {
            "value": 2,
            "unit": "m3/h",
            "confirmed_by_user": True,
            "rationale": "Explicit synthetic test rate",
        },
    }


def test_rate_normalization_time_and_upstream_convention():
    item = custom()
    assert hourly_rate(item)[0] == 2
    assert annual_manual_quantity(item, D(314 * 24), D(".3"))["annual_quantity"] == D(
        "4521.6"
    )
    day = copy.deepcopy(item)
    day["manual_rate"].update(value=48, unit="m3/day")
    assert hourly_rate(day)[0] == 2
    minute = copy.deepcopy(item)
    minute["manual_rate"].update(value=2000 / 60, unit="L/min")
    assert abs(hourly_rate(minute)[0] - D(2)) < D("1e-12")
    with pytest.raises(ValueError, match="time unit"):
        manual_observation(
            {**item, "manual_rate": {**item["manual_rate"], "unit": "m3"}}
        )
    with pytest.raises(ValueError, match="Confirm"):
        manual_observation(
            {**item, "manual_rate": {**item["manual_rate"], "confirmed_by_user": False}}
        )
    with pytest.raises(ValueError, match="incompatible"):
        hourly_rate({**item, "quantity_unit": "kg"})


def request(state, kind="product", approve=True):
    existing = state["plan"]["operating_economics"]
    return RateStudyRequest(
        revision=state["revision"],
        days_per_year=314,
        hours_per_day=24,
        approve=approve,
        remove=[r["id"] for r in existing.get("sales", [])],
        lines=[
            RateLine(
                id="custom-income",
                name="Test water",
                kind=kind,
                rate=2,
                rate_unit="m3/h",
                price=5,
                price_unit="m3",
            )
        ],
    )


@pytest.mark.parametrize("kind", ["product", "service"])
def test_full_rate_revenue_handoff_and_no_workbook_fabrication(study, kind):
    store, key = study
    run_stage(store, key, "engineering_data")
    state = store.get(key)
    old = copy.deepcopy(state)
    save_rates(store, key, request(state, kind))
    saved = store.get(key)
    assert saved["revenue_approval"]
    assert saved["parsed"] == old["parsed"]
    assert saved["plan"]["equipment"] == old["plan"]["equipment"]
    assert (
        saved["plan"]["operating_economics"]["labour"]
        == old["plan"]["operating_economics"]["labour"]
    )
    result = run_stage(store, key, "revenue", use_ai=False)
    stage = result["results"]["stages"]["revenue"]
    assert stage["result"], stage
    assert not stage.get("issues"), stage
    config = saved["plan"]["operating_economics"]
    ramp = config["financial"]["production_ramp"]
    annual = stage["result"]["annual"]
    expected = D(2) * D(5) * D(314) * D(24) * D(str(ramp[0]))
    assert D(annual[0]["sales_revenue"]) == expected
    assert len(annual) == config["financial"]["operating_years"]
    assert len(store.versions(key)) >= 1


@pytest.mark.parametrize("kind", ["product", "service"])
def test_selected_stream_uses_measured_rate_instead_of_manual_rate(study, kind):
    from backend.opex.consumption import observation
    store, key = study
    run_stage(store, key, "engineering_data")
    state = store.get(key)
    stream_key = state["plan"]["operating_economics"]["sales"][0]["stream_key"]
    measured = observation(state["parsed"]["report"], stream_key, "mass_flow")
    assert measured["normalized_unit"] == "kg/h"
    change = request(state, kind)
    change.lines[0].stream_key = stream_key
    change.lines[0].price_unit = "kg"
    change.lines[0].rate = None  # The dropdown sends the reference, not a copied number.
    save_rates(store, key, change)
    saved = store.get(key)
    config = saved["plan"]["operating_economics"]
    row = (config["sales"] if kind == "product" else config["commercial_lines"])[0]
    assert row["stream_key"] == stream_key and "manual_rate" not in row
    result = run_stage(store, key, "revenue", use_ai=False)
    annual = result["results"]["stages"]["revenue"]["result"]["annual"][0]
    expected = D(str(measured["normalized_value"])) * 5 * 314 * 24 * D(str(config["financial"]["production_ramp"][0]))
    assert D(annual["sales_revenue"]) == expected


@pytest.mark.parametrize("kind", ["product", "service"])
def test_revenue_displays_full_operation_without_overwriting_a_saved_financial_ramp(study, kind):
    store, key = study
    run_stage(store, key, "engineering_data")
    state = store.get(key)
    state['plan']['operating_economics']['financial']['production_ramp'] = [0.2, 0.8]
    state = store.put(state, state['revision'])
    save_rates(store, key, request(state, kind))
    saved = store.get(key)
    before = copy.deepcopy(saved['plan'])
    actual = run_stage(store, key, "revenue", use_ai=False)
    result = actual['results']['stages']['revenue']['result']
    full = result['full_operation']['annual'][0]['sales_revenue']
    assert D(full) == D(2) * 5 * 314 * 24
    assert D(result['annual'][0]['sales_revenue']) == D(full) * D('0.2')
    assert actual['plan']['operating_economics']['financial'] == before['operating_economics']['financial']
    assert actual['plan']['operating_economics'].get('cashflow_schedule') == before['operating_economics'].get('cashflow_schedule')
    assert result['full_operation_basis']['throughput_fraction'] == '1'


def test_missing_rate_or_incompatible_units_do_not_commit_an_approved_model(study):
    store, key = study
    run_stage(store, key, "engineering_data")
    state = store.get(key)
    wrong = request(state)
    wrong.lines[0].price_unit = "kg"
    with pytest.raises(ValueError, match="compatible|measured|incompatible"):
        save_rates(store, key, wrong)
    assert store.get(key)["revision"] == state["revision"]
    with pytest.raises(ValidationError):
        RateLine(id="x", name="Test", kind="product", quantity=1000)
    missing = request(state)
    missing.lines[0].rate = None
    with pytest.raises(ValueError, match="time unit"):
        save_rates(store, key, missing)


def test_user_rate_extraction_is_literal_and_never_a_price_or_batch_quantity():
    assert explicit_rates("We sell 2m3 per hour at USD 5/m3.")[0]["value"] == 2
    assert explicit_rates("We sell 48 m³/day.")[0]["unit"] == "m3/day"
    assert not explicit_rates("A batch contains 2000 kg, sold for 5 USD/kg.")
    assert not explicit_rates("Our price is GBP 100/m3.")
    assert not explicit_rates("A negative production -2 kg/h is invalid.")


def test_installed_openpytea_321_reference_is_equivalent_with_an_explicit_calendar():
    from importlib.metadata import version, PackageNotFoundError

    try:
        if version("openpytea") != "3.2.1":
            pytest.skip("Pinned OpenPyTEA 3.2.1 reference is not installed")
    except PackageNotFoundError:
        pytest.skip("Optional pinned OpenPyTEA reference not installed")
    from openpytea.plant import Plant

    plant = SimpleNamespace(
        plant_products={"water": {"production": 48, "price": 5}},
        plant_utilization=314 / 365,
    )
    expected = annual_manual_quantity(custom(), D(314 * 24), D(1))[
        "annual_quantity"
    ] * D(5)
    assert abs(Plant.calculate_revenue(plant) - float(expected)) < 1e-8


def test_llm_can_select_only_literal_user_rates_and_cannot_approve_them():
    import json
    from backend.orchestration.operating_advisor import generate

    def example(schema):
        if "enum" in schema:
            return schema["enum"][0]
        kind = schema.get("type")
        if isinstance(kind, list):
            kind = next(k for k in kind if k != "null")
        if kind == "object":
            return {k: example(v) for k, v in schema["properties"].items()}
        if kind == "array":
            return []
        if kind in ("number", "integer"):
            return schema.get("minimum", 0)
        if kind == "boolean":
            return False
        return "Synthetic user assumption"

    box = "We sell 2 m3/hour at USD 5/m3."

    class Provider:
        def generate(self, *, instructions, context, schema):
            assert context["explicit_user_flow_rates"][0]["value"] == 2
            assert "standalone annual/batch quantity" in instructions
            value = example(schema)
            value["commercial_intent"] = {
                "status": "explicit",
                "questions": [],
                "mechanisms": [
                    {
                        "id": "water-sale",
                        "category": "product_sales",
                        "context_quote": box,
                        "interpretation": "User water sale",
                    }
                ],
            }
            sale = example(schema["properties"]["sales"]["items"])
            sale.update(
                id="water-sale",
                name="Water",
                intent_id="water-sale",
                context_quote=box,
                stream_key=None,
                manual_rate="explicit-rate-1",
                unit_price_period="2026",
                unit_price=5,
                quantity_unit="m3",
                allocation_fraction=1,
                saleable_fraction=1,
                sold_fraction=1,
            )
            value["sales"] = [sale]
            return value

    proposal = generate(
        Provider(),
        "",
        {"report": {"entities": []}, "revenue_box": box},
        revenue_only=True,
    )
    config = json.loads(proposal["sections"][0]["value_json"])
    assert config["sales"][0]["price_basis"]["price_period"] == "2026"
    rate = config["sales"][0]["manual_rate"]
    assert rate["value"] == 2 and rate["unit"] == "m3/h"
    assert rate["confirmed_by_user"] is False
    with pytest.raises(ValueError, match="Confirm"):
        hourly_rate(config["sales"][0])


def test_simple_edits_preserve_existing_deductions_and_other_income(study):
    store, key = study
    run_stage(store, key, "engineering_data")
    state = store.get(key)
    existing = state["plan"]["operating_economics"]["sales"][0]
    existing["net_freight_deduction_per_unit"] = 0.2
    existing["net_packaging_deduction_per_unit"] = 0.1
    state = store.put(state, state["revision"])
    change = RateLine(
        id=existing["id"],
        name=existing["name"],
        kind="product",
        stream_key=existing["stream_key"],
        price=5,
        price_unit=existing["quantity_unit"],
    )
    save_rates(
        store,
        key,
        RateStudyRequest(
            revision=state["revision"],
            lines=[change],
            days_per_year=314,
            hours_per_day=24,
        ),
    )
    saved = store.get(key)["plan"]["operating_economics"]["sales"][0]
    assert saved["unit_price"] == 5
    assert "price_observation" not in saved
    assert saved["net_freight_deduction_per_unit"] == 0.2
    assert saved["net_packaging_deduction_per_unit"] == 0.1


def test_explicit_revenue_period_is_not_relabelled_as_historical_opex(study):
    store, key = study
    run_stage(store, key, "engineering_data")
    state = store.get(key)
    change = request(state)
    change.lines[0].price_period = "2026"
    save_rates(store, key, change)
    result = run_stage(store, key, "revenue", use_ai=False)["results"]["stages"][
        "revenue"
    ]["result"]
    assert result["basis"]["price_period"] == "2026"
    assert D(result["annual"][0]["sales_revenue"]) == D(2 * 5 * 314 * 24)


@pytest.mark.parametrize("kind", ["product", "service"])
def test_price_edit_replaces_one_line_and_updates_linked_opex(study, monkeypatch, kind):
    from backend.blocks.stage_workflow import approve
    store, key = study
    monkeypatch.setattr('backend.blocks.stage_workflow._brainstorm', lambda *args: None)
    run_stage(store, key, 'engineering_data')
    approve(store, key, store.get(key)['revision'])
    run_stage(store, key, 'equipment')
    run_stage(store, key, 'capex')
    save_rates(store, key, request(store.get(key), kind))
    run_stage(store, key, 'revenue')
    before = run_stage(store, key, 'opex')
    versions = len(store.versions(key))
    old_opex = before['results']['stages']['opex']['result']
    old_revenue = before['results']['stages']['revenue']['result']['full_operation']['annual'][0]['sales_revenue']
    change = request(before, kind)
    change.remove = []
    change.lines[0].price = 10  # Previously 5; same stable id, even after renaming.
    change.lines[0].name = 'Renamed income'
    save_rates(store, key, change)
    saved = store.get(key)
    rows = [*saved['plan']['operating_economics']['sales'], *saved['plan']['operating_economics']['commercial_lines']]
    assert len(rows) == 1 and rows[0]['id'] == 'custom-income'
    assert rows[0]['name'] == 'Renamed income'
    assert len(store.versions(key)) == versions + 1
    run_stage(store, key, 'revenue')
    after = run_stage(store, key, 'opex')
    assert D(after['results']['stages']['revenue']['result']['full_operation']['annual'][0]['sales_revenue']) == D(old_revenue) * 2
    new_opex = after['results']['stages']['opex']['result']
    assert new_opex['first_year_fixed_opex'] == old_opex['first_year_fixed_opex']
    assert D(new_opex['first_year_variable_opex']) > D(old_opex['first_year_variable_opex'])


@pytest.mark.parametrize("price,keep_review", [(10, False), (5, True)])
def test_price_review_applies_only_to_the_unchanged_price(study, price, keep_review):
    store, key = study
    run_stage(store, key, 'engineering_data')
    save_rates(store, key, request(store.get(key)))
    state = store.get(key)
    state['plan']['operating_economics']['sales'][0]['price_review'] = {'selected': 5, 'rationale': 'Old reviewed price'}
    state = store.put(state, state['revision'])
    change = request(state)
    change.remove = []
    change.lines[0].price = price
    save_rates(store, key, change)
    row = store.get(key)['plan']['operating_economics']['sales'][0]
    assert row['unit_price'] == price
    assert ('price_review' in row) is keep_review
