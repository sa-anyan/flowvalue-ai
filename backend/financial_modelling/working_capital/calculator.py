"""Explicit required balances, cash changes and terminal recovery, never OPEX."""

from decimal import Decimal

from ..assumptions.calculator import money_at, value


def working_capital_schedule(plan, periods, assumptions):
    requirements = {x.year: x.money for x in plan.requirements}
    if (
        len(requirements) != len(plan.requirements)
        or not requirements
        or not plan.source
    ):
        raise ValueError(
            "Explicit unique working-capital requirements and source required"
        )
    if (
        set(requirements) - set(range(len(periods)))
        or plan.recovery_year != periods[-1].year
    ):
        raise ValueError(
            "Working capital must use supported years and terminal recovery"
        )
    recovery_fraction = value(plan.recovery_fraction, maximum=Decimal(1))
    balance, required, result = Decimal(0), Decimal(0), {}
    for period in periods:
        opening = balance
        if period.year in requirements:
            required = money_at(
                requirements[period.year], period.calendar_year, assumptions
            )
        investment = required - balance
        recovery = (
            required * recovery_fraction
            if period.year == plan.recovery_year
            else Decimal(0)
        )
        balance = required - recovery
        result[period.year] = (
            opening,
            investment - recovery,
            recovery,
            balance,
            investment,
        )
    return result
