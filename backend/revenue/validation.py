"""Shared deterministic commercial validation; no inferred physical quantities."""

from decimal import Decimal

from .models import CommercialLine

CATEGORIES = (
    "product_sales",
    "processing_services",
    "capacity_availability",
    "infrastructure_usage",
    "environmental_attributes",
    "other_contractual_income",
)


def validate_line(line, schedule):
    if not isinstance(line, CommercialLine):
        raise TypeError("Expected CommercialLine")
    if line.category not in CATEGORIES:
        raise ValueError("Unsupported revenue category")
    if not all(
        isinstance(v, str) and v.strip()
        for v in (
            line.id,
            line.name,
            line.payment_id,
            line.rationale,
            line.quantity_unit,
        )
    ):
        raise ValueError(
            "Line identity, payment identity, billing unit and rationale required"
        )
    if line.arrangement not in {"user_confirmed", "user_assumption", "llm_proposed"}:
        raise ValueError("Commercial arrangement status required")
    if line.rate_period not in {"per_unit", "annual", "monthly"}:
        raise ValueError("Use per_unit, annual or monthly billing periods")
    years = [y.year for y in line.years]
    if (
        any(type(y) is not int or y < 1 for y in years)
        or len(set(years)) != len(years)
        or set(years) != set(schedule)
    ):
        raise ValueError("Each line must specify every operating year exactly once")
    if not isinstance(line.source_references, tuple) or not all(
        isinstance(v, str) for v in line.source_references
    ):
        raise ValueError("Source references must be an immutable tuple")
    if (
        line.category == "environmental_attributes"
        and not line.eligibility_basis.strip()
    ):
        raise ValueError(
            "Environmental attributes need explicit eligibility/ownership basis; no automatic credit"
        )
    if (
        type(line.included) is not bool
        or type(line.fixed_variable_distinct) is not bool
    ):
        raise ValueError("Inclusion and component separation must be boolean")
    if not line.included and not line.exclusion_reason.strip():
        raise ValueError("Excluded income requires a reason")


def calculate_payment(line, year, currency):
    from .engine import read

    unit = line.quantity_unit
    q = read(year.quantity, unit)
    minimum_q = read(year.minimum_quantity, unit)
    rate_unit = (
        currency
        + "/"
        + unit
        + ({"per_unit": "", "annual": "/year", "monthly": "/month"}[line.rate_period])
    )
    rate = read(year.rate, rate_unit)
    fixed = read(year.fixed_payment, currency + "/year")
    minimum = read(year.minimum_payment, currency + "/year")
    availability = read(year.availability, "fraction", maximum=Decimal(1))
    escalation = read(year.escalation, "fraction/year", minimum=Decimal("-0.99"))
    if (
        type(year.periods) is not int
        or year.periods not in (1, 12)
        or year.periods != (12 if line.rate_period == "monthly" else 1)
    ):
        raise ValueError("Billing periods must be 12 for monthly, otherwise 1")
    if fixed and rate and not line.fixed_variable_distinct:
        raise ValueError("Confirm fixed and variable payments buy distinct components")
    if line.category == "product_sales" and (
        fixed or minimum or minimum_q or line.rate_period != "per_unit"
    ):
        raise ValueError(
            "Product sales use actual quantity sold times net price; contract floors belong in a separate payment"
        )
    variable = max(q, minimum_q) * rate * year.periods * availability
    # Each schedule explicitly provides a base rate and cumulative year escalation.
    return (
        max(minimum, fixed + variable) * (1 + escalation) ** (year.year - 1),
        q,
        rate,
        fixed,
    )
