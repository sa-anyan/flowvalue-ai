"""Independent ratio checks; synthetic native index values are not real CEPCI."""

import copy
from dataclasses import replace
from decimal import Decimal as D

import pytest

from backend.capex import calculate_capex
from backend.capex.connectors import prepare_capex_inputs
from backend.equipment_costing.cost_to_future.cost_translation import (
    DEFAULT_POLICY,
    catalogue,
    translate_calculation,
    translate_cost,
)
from backend.equipment_costing.cost_to_future.operating_prices import (
    translate_operating_prices,
)
from backend.equipment_costing.total_cost import calculate_total_cost
from backend.tests.test_total_equipment_cost import exchanger


def convert(amount=100, **kwargs):
    return translate_cost(
        amount,
        currency="USD",
        source_period="early 1987",
        source_series="CEPCI",
        source_index=320,
        **kwargs,
    )


def test_official_proxy_is_same_cpi_series_not_cpi_divided_by_cepci():
    result = convert()
    assert result.amount == pytest.approx(
        D(100) * D("336.940") / D("113.6"), rel=D("1e-25")
    )
    assert result.source_index == 320
    assert result.applied_series == "US_CPI_U_NSA_1982_84"
    assert result.status == "general_inflation_proxy"
    assert "not CEPCI" in result.notice
    assert result.target_observation["frequency"] == "monthly"


def test_native_series_has_priority():
    data = catalogue()
    data["series"]["CEPCI"] = {
        "currency": "USD",
        "kind": "equipment_index",
        "observations": {
            "2026-09": {
                "value": "640",
                "source": "Synthetic unit-test index, NOT real CEPCI",
            }
        },
    }
    result = convert(indices=data)
    assert result.amount == 200
    assert result.status == "same_series_index_ratio"


@pytest.mark.parametrize(
    "method", ["garrett", "Samuel", "Michael", "future_method_987654"]
)
def test_method_name_does_not_hardcode_year(method):
    assert convert(method_id=method).multiplier == pytest.approx(
        D("336.940") / D("113.6"), rel=D("1e-25")
    )


def test_2018_uses_its_own_price_year():
    result = translate_cost(100, currency="USD", source_period="2018")
    assert result.multiplier == pytest.approx(
        D("336.940") / D("251.107"), rel=D("1e-25")
    )


@pytest.mark.parametrize("value", [-1, True, "NaN", "Infinity", "bad"])
def test_invalid_money(value):
    with pytest.raises((ValueError, TypeError)):
        convert(value)


def test_zero_preserved():
    assert convert(0).amount == 0


def test_already_2026_is_not_escalated_or_relabelled():
    result = translate_cost(100, currency="USD", source_period="2026-05")
    assert result.amount == 100
    assert result.target_period == "2026-05"
    assert result.multiplier == 1


@pytest.mark.parametrize("period", ["unknown", "1987 / 2018", "1045"])
def test_unsupported_years_are_not_invented(period):
    with pytest.raises(ValueError):
        translate_cost(100, currency="USD", source_period=period)


def test_wrong_currency_and_missing_proxy_consent():
    with pytest.raises(ValueError):
        translate_cost(100, currency="GBP", source_period="1987")
    with pytest.raises(ValueError):
        convert(
            policy={"target_period": "2026-09", "allow_general_inflation_proxy": False}
        )


def test_bad_index_and_missing_source():
    with pytest.raises(ValueError):
        translate_cost(100, currency="USD", source_period="1987", source_index=0)
    data = catalogue()
    data["series"]["US_CPI_U_NSA_1982_84"]["observations"]["1987"]["source"] = ""
    with pytest.raises(ValueError):
        convert(indices=data)


def test_equipment_installation_and_capex_are_scaled_once():
    historical = calculate_total_cost([exchanger()])
    translated = calculate_total_cost([exchanger()], translation_policy=DEFAULT_POLICY)
    ratio = float(D("336.940") / D("113.6"))
    before, after = historical.equipment[0], translated.equipment[0]
    assert after.amount == pytest.approx(before.amount * ratio)
    assert after.equipment_cost == pytest.approx(before.equipment_cost * ratio)
    if before.installation_cost is not None:
        assert after.installation_cost == pytest.approx(
            before.installation_cost * ratio
        )
        assert after.equipment_and_installation_cost == pytest.approx(
            after.equipment_cost + after.installation_cost
        )
    assert after.calculation.historical_amount == before.calculation.historical_amount
    twice = translate_calculation(
        after.calculation, method_id="garrett", policy=DEFAULT_POLICY
    )
    assert twice == after.calculation
    prepared = prepare_capex_inputs(
        translated, process_type="fluids", delivery_basis="delivered"
    )
    assert prepared.equipment[0].index_series == "PRICE_BASIS:USD:2026-09"
    assert after.calculation.estimate.index_series == "US_CPI_U_NSA_1982_84"
    assert prepared.equipment[0].period == "2026-09"
    old = calculate_capex(
        inputs=replace(
            prepare_capex_inputs(
                historical, process_type="fluids", delivery_basis="delivered"
            ),
            factor_selection="minimum",
        )
    )
    new = calculate_capex(inputs=replace(prepared, factor_selection="minimum"))
    assert float(new.total_capex) == pytest.approx(float(old.total_capex) * ratio)


def test_unsupported_source_is_retained_as_unpriced_not_fake_2026():
    data = catalogue()
    data["series"]["US_CPI_U_NSA_1982_84"]["observations"].pop("1987")
    result = calculate_total_cost(
        [exchanger()], translation_policy=DEFAULT_POLICY, indices=data
    )
    assert result.equipment[0].amount is None
    assert "Missing" in result.equipment[0].issues[0]


def test_operating_prices_quantities_percentages_and_input_preservation():
    config = {
        "price_basis": {"currency": "USD", "price_period": "1987"},
        "materials": [{"unit_price": 2, "annual_quantity_assumption": 100}],
        "energy": [{"tariff_per_kwh": 0.1, "efficiency": 0.8}],
        "labour": [{"annual_base_salary": 10000, "headcount_fte": 2}],
        "additional_expenses": [{"annual_allowance": 500}],
        "sales": [{"unit_price": 5, "cost_markup_fraction": 0.2}],
        "commercial_lines": [
            {
                "years": [
                    {
                        "year": 1,
                        "rate": 3,
                        "quantity": 10,
                        "fixed_payment": 100,
                        "minimum_payment": 0,
                        "escalation": 0.02,
                    }
                ]
            }
        ],
        "avoided_costs": [{"years": [{"year": 1, "amount": 50}]}],
        "financial": {"closure_allowance": 100, "discount_rate": 0.1},
    }
    original = copy.deepcopy(config)
    result, audit = translate_operating_prices(
        config,
        target_basis={"currency": "USD", "price_period": "2026-09"},
        policy=DEFAULT_POLICY,
    )
    ratio = D("336.940") / D("113.6")
    assert D(result["materials"][0]["unit_price"]) == pytest.approx(
        D(2) * ratio, rel=D("1e-25")
    )
    assert result["materials"][0]["annual_quantity_assumption"] == 100
    assert result["financial"]["discount_rate"] == 0.1
    assert result["labour"][0]["headcount_fte"] == 2
    assert result["commercial_lines"][0]["years"][0]["quantity"] == 10
    assert result["commercial_lines"][0]["years"][0]["escalation"] == 0.02
    assert config == original
    assert audit
    second, second_audit = translate_operating_prices(
        result, target_basis=result["price_basis"], policy=DEFAULT_POLICY
    )
    assert second == result and not second_audit


def test_different_native_indices_aggregate_on_one_dated_currency_basis(monkeypatch):
    from backend.equipment_costing import registry

    original = calculate_total_cost([exchanger()]).equipment[0].calculation
    other = replace(
        original, estimate=replace(original.estimate, index_series="SYNTHETIC_OTHER")
    )
    calculations = iter([original, other])
    monkeypatch.setattr(registry, "estimate_cost", lambda *a, **k: next(calculations))
    data = catalogue()
    data["series"]["SYNTHETIC_OTHER"] = {
        "currency": "USD",
        "kind": "equipment_index",
        "observations": {
            "2026-09": {
                "value": "1280",
                "source": "Synthetic native index for tests, not published data",
            }
        },
    }
    total = calculate_total_cost(
        [exchanger("A"), exchanger("B")],
        translation_policy=DEFAULT_POLICY,
        indices=data,
    )
    assert total.total == pytest.approx(
        original.estimate.amount * (float(D("336.940") / D("113.6")) + 4)
    )
    assert total.equipment_cost_total is not None
    assert len(total.subtotals) == 1
    prepared = prepare_capex_inputs(
        total, process_type="fluids", delivery_basis="delivered"
    )
    assert {row.index_series for row in prepared.equipment} == {
        "PRICE_BASIS:USD:2026-09"
    }
    assert total.equipment[1].calculation.estimate.index_series == "SYNTHETIC_OTHER"


def test_missing_operating_basis_and_cost_plus_observation_are_rejected():
    with pytest.raises(ValueError):
        translate_operating_prices(
            {"financial": {}},
            target_basis={"currency": "USD", "price_period": "2026-09"},
            policy=DEFAULT_POLICY,
        )
    config = {
        "price_basis": {"currency": "USD", "price_period": "1987"},
        "financial": {},
        "sales": [
            {
                "price_mode": "cost_plus",
                "price_observation": {"source_url": "https://example.com"},
            }
        ],
    }
    with pytest.raises(ValueError, match="cost-plus"):
        translate_operating_prices(
            config,
            target_basis={"currency": "USD", "price_period": "2026-09"},
            policy=DEFAULT_POLICY,
        )
