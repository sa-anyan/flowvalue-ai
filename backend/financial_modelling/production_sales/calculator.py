"""Reuse Revenue production math; availability and partial-year activity are applied once."""

from dataclasses import replace
from decimal import Decimal

from backend.revenue import calculate_revenue
from backend.revenue.models import OperatingYear

from ..assumptions.calculator import value
from ..financial_schedules.calculator import build_timeline


def revenue_with_operating_plan(revenue_project, plans, financial_assumptions):
    periods = {p.year: p for p in build_timeline(financial_assumptions)}
    if {p.financial_year for p in plans} != {
        p.year for p in periods.values() if p.operating_fraction > 0
    }:
        raise ValueError(
            "Explicit production plans must cover every active financial period, including partial terminal periods"
        )
    if len({p.financial_year for p in plans}) != len(plans) or len(
        {p.revenue_year for p in plans}
    ) != len(plans):
        raise ValueError("Unique production plan years required")
    if {p.revenue_year for p in plans} != {p.year for p in revenue_project.schedule}:
        raise ValueError("Production plan must explicitly match Revenue schedule")
    schedule = []
    for plan in plans:
        period = periods.get(plan.financial_year)
        if period is None or not plan.source:
            raise ValueError(
                "Sourced production plan within financial timeline required"
            )
        hours = value(plan.annual_hours, "h/year", maximum=Decimal(8784))
        availability = value(plan.availability, maximum=Decimal(1))
        value(plan.utilisation, maximum=Decimal(1))
        adjusted = replace(
            plan.annual_hours,
            value=hours * availability * period.operating_fraction,
            rationale=plan.annual_hours.rationale
            + "; availability and active-date fraction applied once",
            source=plan.source,
        )
        schedule.append(OperatingYear(plan.revenue_year, adjusted, plan.utilisation))
    return calculate_revenue(replace(revenue_project, schedule=tuple(schedule)))
