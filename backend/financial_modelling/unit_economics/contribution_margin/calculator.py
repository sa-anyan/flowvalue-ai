"""Annual sales less explicit variable cash operating expense."""

from ...models import Metric


def contribution_margin(revenue, variable, quantity):
    return Metric(
        (revenue - variable) / quantity if quantity > 0 else None,
        "currency/product unit",
        "calculated" if quantity > 0 else "undefined",
        "Sales less variable cash OPEX / quantity sold; no arbitrary product allocation",
    )
