"""Single anniversary-year timeline; annual cash positions, day-based active fractions."""

from datetime import date
from decimal import Decimal

from ..models import Period


def anniversary(start, years):
    try:
        return start.replace(year=start.year + years)
    except ValueError:
        return date(start.year + years, 2, 28)


def build_timeline(assumptions):
    a = assumptions
    if (
        isinstance(a.construction_years, bool)
        or not isinstance(a.construction_years, int)
        or not 0 <= a.construction_years <= 30
    ):
        raise ValueError("Construction years must be an integer from 0 to 30")
    if (
        isinstance(a.operating_years, bool)
        or not isinstance(a.operating_years, int)
        or not 1 <= a.operating_years <= 100
    ):
        raise ValueError("Operating lifetime must be an integer from 1 to 100")
    construction_end = anniversary(a.start_date, a.construction_years)
    if (
        not a.start_date
        <= construction_end
        <= a.commissioning_date
        <= a.first_production_date
    ):
        raise ValueError(
            "Construction, commissioning and first production dates are inconsistent"
        )
    shutdown = anniversary(a.first_production_date, a.operating_years)
    rows = [Period(0, a.start_date, a.start_date, a.start_date.year, Decimal(0))]
    for year in range(1, 152):
        start, end = (
            anniversary(a.start_date, year - 1),
            anniversary(a.start_date, year),
        )
        if start >= shutdown:
            break
        days = max(0, (min(end, shutdown) - max(start, a.first_production_date)).days)
        rows.append(
            Period(
                year,
                start,
                end,
                start.year,
                Decimal(days) / Decimal((end - start).days),
            )
        )
    else:
        raise ValueError("Timeline exceeds supported 150 annual periods")
    return tuple(rows)
