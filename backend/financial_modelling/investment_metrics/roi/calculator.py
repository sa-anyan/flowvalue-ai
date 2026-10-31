"""ROI convention is lifetime accounting net income divided by gross capital invested."""

from decimal import Decimal

from ...models import Metric


def roi(ledger):
    capital = sum(
        (
            r.capex
            + r.startup_expense
            + max(Decimal(0), r.working_capital_change + r.working_capital_recovery)
            for r in ledger
        ),
        Decimal(0),
    )
    profit = sum((r.net_income for r in ledger), Decimal(0))
    return Metric(
        profit / capital if capital > 0 else None,
        "ratio",
        "calculated" if capital > 0 else "undefined",
        "Lifetime net accounting income / gross capital plus expensed startup plus positive WC investments; not annualized",
    )
