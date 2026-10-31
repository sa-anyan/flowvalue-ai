"""Accounting operating break-even, deliberately separate from project NPV break-even."""

from ...models import Metric


def break_even(revenue, variable, fixed, depreciation, interest, sold):
    if sold <= 0:
        return (
            Metric(None, "product units", "undefined", "No product sales"),
            Metric(None, "currency/product unit", "undefined", "No product sales"),
        )
    margin = (revenue - variable) / sold
    quantity = (fixed + depreciation + interest) / margin if margin > 0 else None
    price = (fixed + variable + depreciation + interest) / sold
    return Metric(
        quantity,
        "product units",
        "calculated" if quantity is not None else "undefined",
        "Annual zero-PBT quantity at constant unit contribution; excludes startup, shutdown and disposal",
    ), Metric(
        price,
        "currency/product unit",
        "calculated",
        "Annual zero-PBT price at actual sold volume; excludes startup, shutdown and disposal",
    )
