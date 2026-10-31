"""Small deterministic engineering helpers, with explicit caller-supplied data.

These do not size equipment, infer staffing, fetch tariffs or create assumptions.
"""

from decimal import localcontext

from .models import number


def annual_power_cost(*, electrical_input_kw, operating_hours, price_per_kwh):
    """Electrical input, not shaft duty; caller accounts for load/efficiency."""
    with localcontext() as context:
        context.prec = 40
        hours = number(operating_hours)
        if hours > 8784:
            raise ValueError("Annual hours cannot exceed a leap year")
        return number(electrical_input_kw) * hours * number(price_per_kwh)


def straight_line_depreciation(
    *, depreciable_asset_cost, salvage_value, life_years, operating_year
):
    """Garrett pp.58–59: depreciable assets explicitly exclude land.

    This is a preliminary straight-line allowance, not jurisdictional tax advice.
    Original asset basis and salvage must be in the same price basis.
    """
    with localcontext() as context:
        context.prec = 40
        capital, salvage, life, year = map(
            number, (depreciable_asset_cost, salvage_value, life_years, operating_year)
        )
        if (
            salvage > capital
            or life == 0
            or life != life.to_integral_value()
            or year < 1
            or year != year.to_integral_value()
        ):
            raise ValueError(
                "Invalid asset/salvage, integer lifetime or operating year"
            )
        return (capital - salvage) / life if year <= life else number(0)


def annual_interest(*, outstanding_principal, annual_rate):
    """Supplied annual opening/average principal convention must be documented."""
    with localcontext() as context:
        context.prec = 40
        return number(outstanding_principal) * number(annual_rate)
