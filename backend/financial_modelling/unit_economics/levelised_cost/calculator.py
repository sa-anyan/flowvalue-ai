"""Pre-tax unlevered LCOP; no arbitrary multi-product allocation or double counting."""

from decimal import Decimal

from ...cash_flow.calculator import discount, recurring_factor
from ...models import Metric


def levelised_cost(ledger, rate, convention, product_id):
    numerator = Decimal(0)
    denominator = Decimal(0)
    for row in ledger:
        recurring = row.fixed_opex + row.variable_opex
        point = (
            row.capex
            + row.startup_expense
            + row.closure_expense
            + row.working_capital_change
            - row.disposal_proceeds
        )
        numerator += discount(recurring, point, rate, row.period.year, convention)
        quantity = sum(
            (p.saleable for p in row.products if p.id == product_id), Decimal(0)
        )
        denominator += quantity * recurring_factor(rate, row.period.year, convention)
    return Metric(
        numerator / denominator if denominator > 0 else None,
        "currency/product unit",
        "calculated" if denominator > 0 else "undefined",
        "Pre-tax unlevered discounted capital + cash OPEX + startup/closure + WC changes - proceeds / discounted saleable output; no taxes/interest/credits",
    )
