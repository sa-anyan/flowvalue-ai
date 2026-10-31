"""Purchased/installed/module factors are upstream; schedule explicit capital amounts only."""

from decimal import Decimal

from ..assumptions.calculator import money_at, value


def capital_schedule(items, periods, assumptions):
    result = {p.year: [] for p in periods}
    totals = {}
    for item in items:
        if (
            not item.spend
            or sum(
                (value(s.fraction, maximum=Decimal(1)) for s in item.spend), Decimal(0)
            )
            != 1
        ):
            raise ValueError(item.id + ": CAPEX allocation must sum exactly to 100%")
        years = [s.year for s in item.spend]
        if len(set(years)) != len(years):
            raise ValueError(item.id + ": duplicate spending years")
        total = Decimal(0)
        for spend in item.spend:
            if spend.year not in result:
                raise ValueError(item.id + ": spending outside timeline")
            period = periods[spend.year]
            amount = money_at(
                item.amount,
                period.calendar_year,
                assumptions,
                item.price_treatment,
                item.escalation,
            ) * value(spend.fraction)
            result[spend.year].append((item.id, item.kind, amount))
            total += amount
        totals[item.id] = total
    return result, totals
