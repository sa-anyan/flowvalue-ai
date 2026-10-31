"""Asset-specific full-year depreciation; supplied MACRS tables, no inferred tax eligibility."""

from decimal import Decimal

from ..assumptions.calculator import money_at, value


def asset_schedule(item, cost, periods, assumptions):
    p = item.depreciation
    fraction = value(p.depreciable_fraction, maximum=Decimal(1))
    basis = cost * fraction
    if p.method not in {"none", "straight_line", "declining_balance", "macrs"}:
        raise ValueError("Unsupported depreciation method")
    if not p.source or not p.jurisdiction_and_convention:
        raise ValueError("Depreciation needs source and convention/applicability")
    if (
        p.service_year not in range(len(periods))
        or item.disposal_year not in range(len(periods))
        or item.disposal_year < p.service_year
    ):
        raise ValueError("Asset service/disposal dates outside timeline")
    if max(s.year for s in item.spend) > p.service_year:
        raise ValueError(
            "Asset placed in service before its capital spending is complete"
        )
    residual = money_at(
        p.residual_basis, periods[p.service_year].calendar_year, assumptions
    )
    if residual > basis:
        raise ValueError("Depreciation residual exceeds depreciable basis")
    if p.method == "none":
        if fraction != 0:
            raise ValueError(
                "Nondepreciable capital must declare zero depreciable fraction"
            )
    elif p.service_year == 0:
        raise ValueError("Annual depreciation cannot occur at instantaneous year zero")
    elif isinstance(p.life, bool) or not isinstance(p.life, int) or p.life <= 0:
        raise ValueError("Positive integer asset life required")
    rates = tuple(value(r, maximum=Decimal(1)) for r in p.macrs_rates)
    if p.method == "macrs":
        if (
            not rates
            or len(rates) != p.life
            or sum(rates, Decimal(0)) > Decimal("1.000001")
        ):
            raise ValueError(
                "MACRS needs supplied complete dated rate table and applicability, with total <=100%"
            )
        if residual != 0:
            raise ValueError(
                "MACRS rate basis must not subtract salvage; supply zero depreciation residual"
            )
    accumulated, annual = Decimal(0), {}
    for period in periods:
        age = period.year - p.service_year
        dep = Decimal(0)
        if (
            p.method != "none"
            and 0 <= age < p.life
            and period.year <= item.disposal_year
        ):
            remaining = max(Decimal(0), basis - residual - accumulated)
            if p.method == "straight_line":
                dep = (
                    remaining
                    if age == p.life - 1
                    else min(remaining, (basis - residual) / p.life)
                )
            elif p.method == "macrs":
                dep = min(basis - accumulated, basis * rates[age])
            else:
                if p.declining_factor is None:
                    raise ValueError("Declining-balance multiplier required")
                multiplier = value(p.declining_factor, "factor")
                if multiplier <= 0 or multiplier > p.life:
                    raise ValueError("Invalid declining-balance multiplier")
                dep = min(remaining, (basis - accumulated) * multiplier / p.life)
                if p.switch_to_straight_line:
                    dep = max(dep, remaining / (p.life - age))
            accumulated += dep
        annual[period.year] = dep
    # Book value includes the nondepreciable portion of the original asset.
    return annual, cost - sum(annual.values(), Decimal(0))
