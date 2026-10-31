"""Cash-flow profitability index; all negative discounted net cash flows form denominator."""

from decimal import Decimal

from ...models import Metric


def profitability_index(discounted_flows):
    positive = sum((max(Decimal(0), x) for x in discounted_flows), Decimal(0))
    negative = -sum((min(Decimal(0), x) for x in discounted_flows), Decimal(0))
    return Metric(
        positive / negative if negative > 0 else None,
        "ratio",
        "calculated" if negative > 0 else "undefined",
        "PV positive net annual cash flows / absolute PV negative net annual cash flows",
    )
