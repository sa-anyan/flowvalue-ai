"""Independent scheduled cash-flow cases; no workbook formulas or provider calls."""

import copy
from decimal import Decimal as D
import pytest

from backend.blocks.cashflow.schedule import apply_policy, make_policy, validate
from backend.blocks.cashflow.view import snapshot
from backend.blocks.execution import run_stage
from backend.blocks.cashflow.schedule import save
from backend.tests.test_isolated_stages import study
from backend.tests.test_operating_economics import fixture, DESCRIPTION
from backend.orchestration.operating_economics import calculate_operating_study


def test_cost_timing_is_validated_without_silent_normalization():
    policy = make_policy(6, 2)
    assert policy["capital_spend_fractions"] == {"1": 0.3, "2": 0.5, "3": 0.2}
    for field in ("capital_spend_fractions", "startup_spend_fractions"):
        for bad in ({"1": 0.9}, {"7": 1}, {"1": -1, "2": 2}, {"1": "NaN"}):
            with pytest.raises(ValueError):
                validate({**policy, field: bad})
    with pytest.raises(ValueError):
        validate({**policy, "working_capital_funding_year": 4})
    with pytest.raises(ValueError):
        validate({**policy, "fixed_opex_factors": {"2": 0.5}})


def test_fixed_and_variable_opex_have_separate_timing_and_reconcile():
    report, config, capex = fixture()
    baseline = copy.deepcopy(config)
    policy = make_policy(5, 2, {"production_ramp": [0.3, 0.4, 1]})
    policy.update(
        capital_spend_fractions={"1": 0.3, "2": 0.5, "3": 0.2},
        startup_spend_fractions={"3": 1},
        working_capital_funding_year=3,
    )
    config = apply_policy(config, policy)
    full = calculate_operating_study(report, DESCRIPTION, config, capex)
    config["cashflow_schedule"]["fixed_opex_factors"] = {"3": 0.5}
    half = calculate_operating_study(report, DESCRIPTION, config, capex)
    # Inspect result keys below if the public study contract changes.
    assert not half["financial"].issues
    for year in range(1, 4):
        a, b = full["opex"][year], half["opex"][year]
        assert a.cash_variable == b.cash_variable
        assert b.cash_fixed == a.cash_fixed * (D(".5") if year == 1 else 1)
        assert b.annual_cash_opex == b.cash_fixed + b.cash_variable
    assert baseline["financial"]["construction_years"] == 1
    ledger = half["financial"].ledger
    assert ledger[1].capex == capex.fixed_capital * D(".3")
    assert ledger[2].capex == capex.fixed_capital * D(".5")
    assert ledger[3].capex == capex.fixed_capital * D(".2") + capex.startup_expenses
    assert sum(r.capex for r in ledger) == capex.fixed_capital + capex.startup_expenses
    assert ledger[1].revenue == ledger[2].revenue == 0
    assert ledger[3].revenue > 0
    assert ledger[3].working_capital_change == capex.working_capital
    assert ledger[-1].working_capital_change == -capex.working_capital
    assert ledger[3].fixed_opex == half["opex"][1].cash_fixed
    assert ledger[3].variable_opex == half["opex"][1].cash_variable


def test_saved_stage_pipeline_spends_capital_once_with_overlapping_operation(study):
    store, key = study
    run_stage(store, key, "engineering_data")
    policy = make_policy(6, 2)
    save(store, key, store.get(key)["revision"], policy, approve_revenue=True)
    for stage in ("equipment", "capex", "revenue", "opex", "financial"):
        state = run_stage(store, key, stage, use_ai=False)
    result = snapshot(store.get(key))
    assert result["has_financial_ledger"], state["stage_runs"]["financial"]
    assert D(result["rows"][3]["capex"]) > 0
    assert D(result["rows"][3]["revenue"]) > 0
    assert D(result["rows"][1]["fixed_opex"]) == 0
    assert result["policy"]["working_capital_funding_year"] == 3


def test_repeating_percentage_rounding_spends_complete_budget():
    report, config, capex = fixture()
    policy = make_policy(6, 3)
    revised = apply_policy(config, policy)
    result = calculate_operating_study(report, DESCRIPTION, revised, capex)
    assert not result["financial"].issues
    assert abs(
        sum(r.capex for r in result["financial"].ledger)
        - capex.fixed_capital
        - capex.startup_expenses
    ) < D("1e-20")
