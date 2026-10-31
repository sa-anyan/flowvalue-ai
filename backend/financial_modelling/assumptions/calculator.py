"""Explicit currency conversion and escalation; no inferred FX or indices."""

from decimal import Decimal

from backend.revenue.engine import read


def value(parameter, unit="fraction", *, minimum=Decimal(0), maximum=None):
    return read(parameter, unit, minimum=minimum, maximum=maximum)


def money_at(money, calendar_year, assumptions, treatment="actual", escalation=None):
    if money.amount is None:
        raise ValueError("Missing monetary assumption: " + money.source)
    amount = money.amount
    if amount == 0:
        return Decimal(0)  # Known zero needs no fabricated FX or escalation rate.
    if (
        amount
        and assumptions.price_mode == "real"
        and money.price_year != assumptions.financial_base_year
    ):
        raise ValueError(
            "Real money must be aligned to the declared financial base year upstream"
        )
    if money.currency != assumptions.currency:
        matches = [
            r
            for r in assumptions.exchange_rates
            if r.currency == money.currency and r.calendar_year == calendar_year
        ]
        if len(matches) != 1:
            raise ValueError(
                "Missing/duplicate dated FX rate for "
                + money.currency
                + " in "
                + str(calendar_year)
            )
        rate = value(
            matches[0].project_currency_per_unit,
            assumptions.currency + "/" + money.currency,
        )
        if rate <= 0:
            raise ValueError("FX rate must be positive")
        amount *= rate
    if treatment not in {"base", "actual"}:
        raise ValueError("Select base or actual price treatment")
    if treatment == "actual":
        if (
            amount
            and assumptions.price_mode == "nominal"
            and money.price_year != calendar_year
        ):
            raise ValueError(
                "Actual nominal money needs the matching annual price year; use base plus explicit escalation for forecasts"
            )
        if escalation is not None:
            raise ValueError("Actual annual prices must not be escalated again")
        return amount
    rate = (
        value(escalation, "fraction/year", minimum=Decimal(-1))
        if escalation is not None
        else value(assumptions.inflation, "fraction/year", minimum=Decimal(-1))
        if assumptions.price_mode == "nominal"
        else Decimal(0)
    )
    if rate <= -1:
        raise ValueError("Escalation must exceed -100%")
    return amount * (1 + rate) ** (calendar_year - money.price_year)
