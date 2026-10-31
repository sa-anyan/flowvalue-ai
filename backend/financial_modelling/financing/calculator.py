"""One term facility; cash interest in construction/operation, no hidden capitalization."""

from decimal import Decimal

from ..assumptions.calculator import money_at, value
from ..models import DebtRow, Metric


def debt_schedule(plan, periods, assumptions):
    if (
        not plan.source
        or plan.method not in {"equal_principal", "annuity"}
        or plan.draw_timing not in {"beginning", "end"}
    ):
        raise ValueError(
            "Explicit financing source, amortization and draw timing required"
        )
    rate = value(plan.interest_rate, "fraction/year")
    if (
        isinstance(plan.repayment_years, bool)
        or not isinstance(plan.repayment_years, int)
        or plan.repayment_years <= 0
    ):
        raise ValueError("Positive repayment tenor required")
    draws = {}
    for draw in plan.draws:
        if draw.money.currency != assumptions.currency:
            raise ValueError(
                "Term facility must be denominated in project currency; foreign-debt remeasurement is not implemented"
            )
        if draw.year not in range(len(periods)) or draw.year in draws:
            raise ValueError("Debt draw years invalid/duplicated")
        if draw.year >= plan.repayment_start_year:
            raise ValueError(
                "New draws during amortization need a separate facility; unsupported"
            )
        draws[draw.year] = money_at(
            draw.money, periods[draw.year].calendar_year, assumptions
        )
    borrowed = sum(draws.values(), Decimal(0))
    if borrowed and not 1 <= plan.repayment_start_year < len(periods):
        raise ValueError("Debt amortization must begin within the project")
    if (
        borrowed
        and plan.repayment_start_year + plan.repayment_years - 1 >= len(periods)
        and not plan.balloon_at_shutdown
    ):
        raise ValueError(
            "Debt extends beyond project; declare terminal balloon or change term"
        )
    payment = (
        borrowed / plan.repayment_years
        if rate == 0
        else borrowed * rate / (1 - (1 + rate) ** (-plan.repayment_years))
    )
    balance, result = Decimal(0), {}
    for period in periods:
        year, opening, draw = period.year, balance, draws.get(period.year, Decimal(0))
        interest = (
            Decimal(0)
            if year == 0
            else (opening + (draw if plan.draw_timing == "beginning" else 0)) * rate
        )
        principal = Decimal(0)
        if (
            plan.repayment_start_year
            <= year
            < plan.repayment_start_year + plan.repayment_years
        ):
            principal = min(
                opening + draw,
                borrowed / plan.repayment_years
                if plan.method == "equal_principal"
                else max(Decimal(0), payment - interest),
            )
        if year == periods[-1].year and plan.balloon_at_shutdown:
            principal = opening + draw
        balance = opening + draw - principal
        if abs(balance) < Decimal("1e-20"):
            balance = Decimal(0)
        result[year] = DebtRow(opening, draw, interest, principal, balance)
    return result


def dscr(cfads, service):
    return Metric(
        cfads / service if service > 0 else None,
        "ratio",
        "calculated" if service > 0 else "undefined",
        "CFADS excludes debt drawdowns, capital proceeds and terminal WC recovery; divided by cash interest plus principal",
    )
