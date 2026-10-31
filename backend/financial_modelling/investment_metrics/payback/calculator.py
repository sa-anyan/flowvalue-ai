"""First cumulative recovery; interpolation is an explicitly disclosed approximation."""

from decimal import Decimal

from ...models import Metric


def payback(flows):
    total = Decimal(0)
    invested = False
    for year, flow in enumerate(flows):
        prior = total
        total += flow
        invested = invested or total < 0
        if invested and total >= 0 and flow > 0:
            return Metric(
                Decimal(year - 1) + (-prior / flow) if year else Decimal(0),
                "years",
                "calculated",
                "First cumulative recovery; linear within-year interpolation, not a dated transaction result",
            )
    return Metric(
        None,
        "years",
        "not_recovered" if invested else "undefined",
        "No cumulative investment recovery within supplied horizon",
    )
