"""Configurable annual tax/loss arithmetic; no implicit jurisdiction or tax refund."""

from decimal import Decimal

from ..models import TaxResult


def calculate_tax(
    income,
    lots,
    year,
    rate,
    carry_losses,
    max_offset,
    expiry_years,
    nonrefundable_credit=Decimal(0),
):
    active = [
        (origin, amount)
        for origin, amount in lots
        if expiry_years is None or year - origin <= expiry_years
    ]
    if income < 0:
        if carry_losses:
            active.append((year, -income))
        return TaxResult(income, Decimal(0), Decimal(0), tuple(active))
    allowed = income * max_offset
    used, remaining = Decimal(0), []
    for origin, amount in active:
        offset = min(amount, allowed - used)
        used += offset
        if amount > offset:
            remaining.append((origin, amount - offset))
    gross_tax = max(Decimal(0), income - used) * rate
    credit_used = min(gross_tax, nonrefundable_credit)
    return TaxResult(
        income, used, gross_tax - credit_used, tuple(remaining), credit_used
    )
