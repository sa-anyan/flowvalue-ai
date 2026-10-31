"""MIRR under explicit financing/reinvestment conventions, from the same net series."""

from decimal import Decimal

from ...cash_flow.calculator import discount, point_factor
from ...models import Metric


def mirr(recurring, point, finance_rate, reinvest_rate, convention):
    horizon = len(point) - 1
    if horizon <= 0:
        return Metric(None, "fraction/year", "undefined", "No investment horizon")
    negative = Decimal(0)
    positive = Decimal(0)
    for year, (r, p) in enumerate(zip(recurring, point)):
        # Use year-net sign, preserving its recurring/point timing components.
        if r + p < 0:
            negative -= discount(r, p, finance_rate, year, convention)
        elif r + p > 0:
            positive += discount(r, p, reinvest_rate, year, convention) / point_factor(
                reinvest_rate, horizon, convention
            )
    if negative <= 0 or positive <= 0:
        return Metric(
            None,
            "fraction/year",
            "undefined",
            "MIRR requires positive terminal value and negative present investment",
        )
    annual = (positive / negative) ** (Decimal(1) / horizon)
    result = annual - 1 if convention == "discrete_end" else annual.ln()
    return Metric(
        result,
        "fraction/year",
        "calculated",
        "Explicit finance/reinvestment rates; same timing convention and net annual flows",
    )
