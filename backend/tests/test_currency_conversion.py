"""FX backbone and schema-aware reporting, independent of network/AI."""

import copy
from decimal import Decimal

import pytest

from backend.currency_conversion import convert_currency, convert_price, rate_snapshot
from backend.currency_conversion.assessment import currency_view


def test_cross_rates_signed_amounts_and_inverse():
    result = convert_currency("100", "USD", "GBP")
    assert abs(
        Decimal(result["amount"]) - Decimal(100) * Decimal(".83580") / Decimal("1.1216")
    ) < Decimal("1e-24")
    inverse = convert_currency(result["amount"], "GBP", "USD")
    assert abs(Decimal(inverse["amount"]) - 100) < Decimal("1e-24")
    assert Decimal(convert_currency("-100", "USD", "GBP")["amount"]) < 0
    assert Decimal(convert_currency(0, "USD", "GBP")["amount"]) == 0
    assert Decimal(convert_currency("100", "GBP", "GBP")["amount"]) == 100


@pytest.mark.parametrize("amount", [True, "NaN", "Infinity", "", None])
def test_invalid_amounts(amount):
    with pytest.raises(ValueError):
        convert_currency(amount, "USD", "GBP")


@pytest.mark.parametrize("code", ["$", "usd", "ZZZ", "", None])
def test_missing_or_ambiguous_currency(code):
    with pytest.raises(ValueError):
        convert_currency(1, code, "GBP")


def test_explicit_missing_date_and_invalid_rate():
    with pytest.raises(ValueError):
        convert_currency(1, "USD", "GBP", rate_date="2025-01-01")
    rates = rate_snapshot()
    rates["rates"]["GBP"] = "0"
    with pytest.raises(ValueError):
        convert_currency(1, "USD", "GBP", snapshot=rates)


def test_quote_keeps_units_price_period_uncertainty_and_evidence():
    original = {
        "unit_price": "30",
        "currency": "GBP",
        "unit": "kg",
        "price_period": "2018",
        "source": "User assumption",
        "uncertainty": "unverified",
    }
    saved = copy.deepcopy(original)
    quote = convert_price(original, "USD", amount_field="unit_price")
    assert original == saved
    assert quote["currency"] == "USD"
    assert quote["price_period"] == "2018"
    assert quote["unit"] == "kg" and quote["uncertainty"] == "unverified"
    assert quote["fx_conversion"]["original_price"] == original


def test_reporting_preserves_physical_values_percentages_and_source_evidence():
    saved = {
        "plan": {"unit_price": 20},
        "results": {
            "stages": {
                "capex": {
                    "result": {
                        "currency": "USD",
                        "total_capex": "100",
                        "lines": [
                            {"amount": "40", "fraction": ".4", "base_amount": "100"}
                        ],
                    }
                },
                "equipment": {
                    "result": {
                        "equipment": [
                            {
                                "equipment_cost": "30",
                                "quantity": 2,
                                "calculation": {
                                    "estimate": {
                                        "size": 100,
                                        "amount": "60",
                                        "currency": "USD",
                                    },
                                    "historical_amount": 10,
                                    "evidence": {"original_amount": 10},
                                },
                            }
                        ]
                    }
                },
                "revenue": {
                    "result": {
                        "basis": {"currency": "USD"},
                        "products": [
                            {
                                "quantity_sold": "200",
                                "net_selling_price": "3",
                                "net_sales_revenue": "600",
                            }
                        ],
                    }
                },
            }
        },
    }
    original = copy.deepcopy(saved)
    view = currency_view(saved, "GBP")
    r = view["results"]["stages"]
    multiplier = Decimal(view["currency_view"]["rate"])
    assert abs(
        Decimal(r["capex"]["result"]["total_capex"]) - 100 * multiplier
    ) < Decimal("1e-24")
    assert r["capex"]["result"]["lines"][0]["fraction"] == ".4"
    item = r["equipment"]["result"]["equipment"][0]
    assert item["quantity"] == 2 and item["calculation"]["estimate"]["size"] == 100
    assert item["calculation"]["historical_amount"] == 10
    assert (
        item["calculation"]["evidence"]
        == original["results"]["stages"]["equipment"]["result"]["equipment"][0][
            "calculation"
        ]["evidence"]
    )
    assert r["revenue"]["result"]["products"][0]["quantity_sold"] == "200"
    assert saved == original
    assert view["plan"] == saved["plan"]


def test_missing_financial_inputs_cannot_silently_change_npv():
    saved = {
        "results": {
            "stages": {
                "capex": {"result": {"currency": "USD"}},
                "financial": {"result": {"ledger": [1]}},
            }
        }
    }
    with pytest.raises(ValueError, match="Canonical financial inputs"):
        currency_view(saved, "GBP")


def test_financial_ledger_recomputed_and_dimensionless_metrics_unchanged():
    from backend.financial_modelling import calculate_financials
    from backend.orchestration.codec import plain
    from backend.tests.test_financial_modelling import fixture

    inputs = fixture()
    initial = plain(calculate_financials(inputs))
    saved = {
        "plan": {},
        "results": {
            "financial_inputs": plain(inputs),
            "stages": {
                "capex": {"result": {"currency": "GBP", "total_capex": "100"}},
                "financial": {"result": initial},
            },
        },
    }
    view = currency_view(saved, "USD")
    result = view["results"]["stages"]["financial"]["result"]
    scale = Decimal(view["currency_view"]["rate"])
    assert result["currency"] == "USD"
    before, after = dict(initial["metrics"]), dict(result["metrics"])
    assert abs(
        Decimal(after["project_npv"]["value"])
        - Decimal(before["project_npv"]["value"]) * scale
    ) < Decimal("1e-20")
    for key in ("project_irr", "project_payback", "project_profitability_index"):
        assert abs(
            Decimal(before[key]["value"]) - Decimal(after[key]["value"])
        ) < Decimal("1e-12")
    for old, new in zip(initial["ledger"], result["ledger"]):
        assert old["period"] == new["period"]
        assert abs(Decimal(new["fcff"]) - Decimal(old["fcff"]) * scale) < Decimal(
            "1e-20"
        )
    assert saved["results"]["stages"]["financial"]["result"] == initial


def test_service_revenue_deductions_and_explicit_money_assumptions():
    saved = {
        "results": {
            "stages": {
                "capex": {"result": {"currency": "USD", "total_capex": "100"}},
                "revenue": {
                    "result": {
                        "commercial": [
                            {"rate": "2", "revenue": "200", "quantity": "100"}
                        ],
                        "products": [{"opex_charges_separate": [["freight", "10"]]}],
                        "avoided_costs": [
                            {
                                "years": [
                                    [
                                        1,
                                        {
                                            "value": "20",
                                            "unit": "USD/year",
                                            "source": "User",
                                        },
                                    ]
                                ]
                            }
                        ],
                    }
                },
            }
        }
    }
    result = currency_view(saved, "GBP")["results"]["stages"]["revenue"]["result"]
    assert result["commercial"][0]["quantity"] == "100"
    assert (
        result["commercial"][0]["rate"] == convert_currency("2", "USD", "GBP")["amount"]
    )
    assert (
        result["products"][0]["opex_charges_separate"][0][1]
        == convert_currency("10", "USD", "GBP")["amount"]
    )
    assumption = result["avoided_costs"][0]["years"][0][1]
    assert assumption["value"] == convert_currency("20", "USD", "GBP")["amount"]
    assert assumption["unit"] == "GBP/year"


def test_currency_preference_does_not_block_new_or_running_assessments():
    for state in ({"running": True, "results": {}}, {"running": False}, {"results": {"stages": {}}}):
        assert currency_view(state, "GBP") == state
