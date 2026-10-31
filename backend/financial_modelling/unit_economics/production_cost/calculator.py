"""Annual cash/full production cost on explicitly declared saleable product output."""

from ...models import Metric


def production_cost(cash_cost, depreciation, quantity):
    if quantity <= 0:
        return Metric(
            None, "currency/product unit", "undefined", "No saleable output"
        ), Metric(None, "currency/product unit", "undefined", "No saleable output")
    return Metric(
        cash_cost / quantity,
        "currency/product unit",
        "calculated",
        "Annual cash OPEX / saleable output",
    ), Metric(
        (cash_cost + depreciation) / quantity,
        "currency/product unit",
        "calculated",
        "Annual cash OPEX plus depreciation / saleable output; financing excluded",
    )
