from backend.blocks.equipment.presentation import priced_summary


def test_known_equipment_prices_are_shown_even_with_an_unpriced_reactor():
    result = {"equipment_cost_total": None,
              "subtotals": [{"amount": 77657.21, "currency": "USD", "period": "2026-09", "cost_index": 1,
                             "index_series": "project", "cost_scope": "purchased_equipment"},
                            {"amount": 781560.80, "currency": "USD", "period": "2026-09", "cost_index": 1,
                             "index_series": "project", "cost_scope": "unit_capital"}],
              "equipment": [{"amount": 77657.21}, {"amount": 781560.80}, {"amount": None}]}
    summary = priced_summary(result)
    assert summary["amounts"][0]["amount"] == "859218.01"
    assert summary["priced_count"] == 2 and summary["unpriced_count"] == 1
    assert result["equipment_cost_total"] is None  # No fake complete total passed downstream.


def test_currencies_and_dates_are_not_silently_combined():
    result = {"subtotals": [{"amount": 100, "currency": "USD", "period": "2026"},
                            {"amount": 200, "currency": "GBP", "period": "2026"},
                            {"amount": 300, "currency": "USD", "period": "2025"}]}
    assert [row["amount"] for row in priced_summary(result)["amounts"]] == ["100", "200", "300"]


def test_aliases_do_not_inflate_the_unpriced_count_and_real_zero_is_retained():
    result = {"equipment": [{"amount": None, "parsed_source": {"confirmed_alias": True}},
                            {"amount": 0}, {"amount": None}],
              "subtotals": [{"amount": 0, "currency": "USD", "period": "2026"}]}
    summary = priced_summary(result)
    assert summary["priced_count"] == summary["unpriced_count"] == 1
    assert summary["amounts"][0]["amount"] == "0"
