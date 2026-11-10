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
