"""Cashflow graph reads canonical payback and preserves unavailable/stale states."""

from decimal import Decimal
import pytest
from backend.blocks.cashflow.view import cash_break_even
from backend.financial_modelling.investment_metrics.payback.calculator import payback
from backend.orchestration.codec import plain


def result(flows):
    return {
        "ledger": [
            {"period": {"year": i}, "fcff": str(v)} for i, v in enumerate(flows)
        ],
        "metrics": [
            ["project_payback", plain(payback([Decimal(str(x)) for x in flows]))]
        ],
    }


def test_marker_uses_canonical_interpolated_payback_with_initial_investment():
    data = result([-100, 0, 40, 80])
    assert cash_break_even(data)["year"] == "2.75"
    assert cash_break_even(data)["status"] == "calculated"


def test_first_recovery_is_not_a_guarantee_of_permanent_profit():
    assert cash_break_even(result([-100, 150, -100]))["year"] == str(
        Decimal(100) / Decimal(150)
    )


def test_missing_no_recovery_and_no_investment_are_distinct():
    assert cash_break_even({})["status"] == "pending"
    assert cash_break_even(result([-100, 10, 10]))["status"] == "not_recovered"
    assert cash_break_even(result([0, 10, 10]))["status"] == "undefined"
    assert cash_break_even(result([-100, 150]), stale=True) == {
        "year": None,
        "basis": "Undiscounted cumulative project free cashflow",
        "status": "stale",
    }


@pytest.mark.parametrize("year", ["NaN", "Infinity", "-1", "100"])
def test_invalid_metric_is_not_plotted(year):
    data = result([-100, 150])
    data["metrics"][0][1]["value"] = year
    assert cash_break_even(data)["status"] == "pending"
