"""Independent ledger identity checks; a mismatch blocks all investment metrics."""

from decimal import Decimal


def reconcile(ledger):
    errors = []

    def close(a, b):
        return abs(a - b) <= Decimal("1e-15") * max(Decimal(1), abs(a), abs(b))

    for row in ledger:
        tests = {
            "P&L": (
                row.net_income,
                row.ebitda
                - row.depreciation
                + row.disposal_gain
                - row.interest
                - row.income_tax,
            ),
            "operating cash": (
                row.operating_cash_flow,
                row.net_income
                + row.depreciation
                - row.disposal_gain
                - row.working_capital_change,
            ),
            "investing cash": (
                row.investing_cash_flow,
                -row.capex + row.disposal_proceeds,
            ),
            "FCFE": (
                row.fcfe,
                row.operating_cash_flow
                + row.investing_cash_flow
                + row.debt.draw
                - row.debt.principal,
            ),
            "project/equity bridge": (
                row.fcfe,
                row.fcff
                + row.project_tax
                - row.income_tax
                - row.interest
                + row.debt.draw
                - row.debt.principal,
            ),
            "cash balance": (
                row.operating_cash_flow
                + row.investing_cash_flow
                + row.financing_cash_flow,
                Decimal(0),
            ),
            "project timing": (
                row.fcff,
                row.recurring_project_cash + row.point_project_cash,
            ),
            "equity timing": (
                row.fcfe,
                row.recurring_equity_cash + row.point_equity_cash,
            ),
            "debt rollforward": (
                row.debt.closing,
                row.debt.opening + row.debt.draw - row.debt.principal,
            ),
            "WC rollforward": (
                row.working_capital_closing,
                row.working_capital_opening + row.working_capital_change,
            ),
        }
        for name, (left, right) in tests.items():
            if not close(left, right):
                errors.append(
                    "Year "
                    + str(row.period.year)
                    + ": "
                    + name
                    + " reconciliation failed"
                )
    return tuple(errors)
