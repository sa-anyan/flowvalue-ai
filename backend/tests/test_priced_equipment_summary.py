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


def test_scope_components_reconcile_without_inventing_installation():
    result = {"subtotals": [
        {"amount": "1329281.5085903038", "currency": "USD", "period": "2026-09", "cost_scope": "purchased_equipment", "equipment_tags": ["T-001", "R-001"]},
        {"amount": "295054.0445171098", "currency": "USD", "period": "2026-09", "cost_scope": "unit_capital", "equipment_tags": ["P-001"]},
    ]}
    row = priced_summary(result)["amounts"][0]
    assert row['amount'] == '1624335.5531074136'
    assert row['components'] == [
        {'cost_scope': 'purchased_equipment', 'amount': '1329281.5085903038', 'equipment_tags': ['T-001', 'R-001']},
        {'cost_scope': 'unit_capital', 'amount': '295054.0445171098', 'equipment_tags': ['P-001']},
    ]
    assert 'installation' not in {r['cost_scope'] for r in row['components']}


def test_scope_breakdown_retains_separate_bases_zero_and_unknown_scope():
    result = {'subtotals': [
        {'amount': 100, 'currency': 'USD', 'period': '2026', 'cost_scope': 'unit_capital', 'equipment_tags': ['P-1']},
        {'amount': 25, 'currency': 'USD', 'period': '2026', 'cost_scope': 'unit_capital', 'equipment_tags': ['P-2']},
        {'amount': 300, 'currency': 'GBP', 'period': '2026', 'cost_scope': 'purchased_equipment'},
        {'amount': 0, 'currency': 'USD', 'period': '2025'},
        {'amount': None, 'currency': 'USD', 'period': '2026', 'cost_scope': 'installed_equipment'},
    ]}
    rows = priced_summary(result)['amounts']
    assert [r['amount'] for r in rows] == ['125','300','0']
    assert rows[0]['components'][0]['equipment_tags'] == ['P-1','P-2']
    assert rows[2]['components'][0]['cost_scope'] == 'unspecified'


def test_capex_equipment_headline_includes_all_equipment_exactly_once_from_saved_basis():
    from copy import deepcopy
    from backend.blocks.equipment.presentation import project
    capital = {'currency':'USD', 'period':'2026-09', 'purchased_equipment':'1329281.50859030395',
               'scope_subtotals':{'purchased_equipment':'1329281.50859030395','installed_equipment':'0','unit_capital':'295054.0445171098'},
               'inclusion_records':[{'tag':'P-001','scope':'unit_capital'}]}
    state = {'results':{'stages':{'capex':{'result':capital},'equipment':{'result':{'subtotals':[{'amount':9999999}]}}}}}
    saved = deepcopy(state)
    view = project(deepcopy(state))
    summary = view['results']['stages']['capex']['result']['equipment_summary']
    assert summary['amounts'][0]['amount'] == '1624335.55310741375'
    assert summary['amounts'][0]['components'][1]['equipment_tags'] == ['P-001']
    assert capital == saved['results']['stages']['capex']['result']
    assert capital['purchased_equipment'] == '1329281.50859030395'  # Factor base remains unchanged.


def test_missing_capex_basis_is_not_mislabelled_as_a_complete_equipment_cost():
    from backend.blocks.equipment.presentation import capex_summary
    assert capex_summary({'purchased_equipment':'100'})['amounts'] == []
    assert capex_summary({'scope_subtotals':{'purchased_equipment':None,'unit_capital':'100'}})['amounts'] == []
