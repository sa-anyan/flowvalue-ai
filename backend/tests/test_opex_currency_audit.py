"""Adversarial OPEX currency, price-date and tariff-unit cases."""

import copy
from dataclasses import replace
from decimal import Decimal

import pytest

from backend.blocks.models import Context, DataRequired
from backend.blocks.opex.input_builder import _costs_for_year, _opex
from backend.blocks.opex.runner import calculate
from backend.currency_conversion import convert_currency
from backend.opex.models import Basis
from backend.opex.reference_defaults import propose
from backend.orchestration.codec import plain
from backend.tests.test_operating_economics import fixture


@pytest.mark.parametrize("change", [{"currency": "GBP"}, {"period": "2020"}])
def test_capex_is_not_relabelled_with_opex_basis(change):
    report, config, capital = fixture()
    basis = Basis(**config["price_basis"])
    capital = replace(capital, **change)
    with pytest.raises(ValueError, match="same currency and price period"):
        _opex(capital, basis, (), None, allow_partial=True)
    ctx = Context({"plan": {"operating_economics": config}}, report,
                  {"capex": {"capital": plain(capital)}}, None)
    with pytest.raises(DataRequired, match="same currency and price period"):
        calculate(ctx)


@pytest.mark.parametrize("group", ["materials", "energy", "labour", "additional_expenses"])
@pytest.mark.parametrize("foreign", [{"currency": "GBP", "price_period": "2026-09"},
                                    {"currency": "USD", "price_period": "2020"}])
def test_line_basis_cannot_be_ignored_when_translation_is_disabled(group, foreign):
    report, config, _ = fixture()
    config["price_basis"] = {"currency": "USD", "price_period": "2026-09"}
    if group == "additional_expenses":
        config[group] = [{"id": "waste", "category": "environmental", "annual_allowance": 100,
                          "behavior": "fixed", "rationale": "Test", "uncertainty": "Test"}]
    config[group][0]["price_basis"] = foreign
    before = copy.deepcopy(config)
    costs, detail = _costs_for_year(report, config, Basis(**config["price_basis"]), 1000, 1, 1, partial=True)
    assert any(p["group"] == group and "currency and price period" in p["reason"] for p in detail["pending_items"])
    assert config == before


def _power_report():
    return {"entities": [{"key": "motor", "identifier": "P-1", "kind": "equipment", "values": [
        {"id": "power", "property": "power", "normalized_value": 10, "normalized_unit": "kW"}
    ]}], "connections": []}


@pytest.mark.parametrize("unit,value,expected", [("USD/MWh", 100, "0.1"), ("USD/kWh", 0, "0")])
def test_tariff_energy_units_and_explicit_zero_are_preserved(unit, value, expected):
    config, _ = propose({"price_basis": {"currency": "USD", "price_period": "2026-09"}},
                        _power_report(), workbook_params=[{"id": "Prices!B2", "label": "Electricity price",
                                                          "unit": unit, "value": value}])
    row = config["energy"][0]
    assert Decimal(row["tariff_per_kwh"]) == Decimal(expected)
    assert row["tariff_source"]["unit"] == unit


def test_foreign_tariff_uses_explicit_fx_and_keeps_original():
    source = {"id": "Prices!B2", "label": "Electricity price", "unit": "GBP/kWh", "value": 0.2}
    config, _ = propose({"price_basis": {"currency": "USD", "price_period": "2026-09"}},
                        _power_report(), workbook_params=[source])
    row = config["energy"][0]
    assert Decimal(row["tariff_per_kwh"]) == Decimal(convert_currency("0.2", "GBP", "USD")["amount"])
    assert row["fx_conversion"]["source_currency"] == "GBP"
    assert row["fx_conversion"]["rate_date"]
    assert row["tariff_source"] == source


@pytest.mark.parametrize("unit,value", [("cents/kWh", 20), ("p/kWh", 20), ("$/kWh", 0.2),
                                       ("USD/kWh", True), ("USD/kWh", float("inf"))])
def test_ambiguous_or_invalid_tariffs_stay_pending(unit, value):
    config, summary = propose({"price_basis": {"currency": "USD", "price_period": "2026-09"}},
                              _power_report(), workbook_params=[{"id": "B2", "label": "Electricity price",
                                                                "unit": unit, "value": value}])
    assert config["energy"][0]["tariff_per_kwh"] is None
    assert any("tariff" in q["question"].lower() for q in summary["questions"])


def test_raw_foreign_price_currency_cannot_be_silently_ignored():
    report, config, _ = fixture()
    config["materials"][0]["unit_price_currency"] = "GBP"
    _, detail = _costs_for_year(report, config, Basis(**config["price_basis"]), 1000, 1, 1, partial=True)
    assert any("convert GBP to USD" in p["reason"] for p in detail["pending_items"])
