"""All reported metrics consume the one canonical ledger, never independently modeled cash flows."""

from decimal import Decimal

from ..assumptions.calculator import value
from ..models import Metric
from ..unit_economics.contribution_margin.calculator import contribution_margin
from ..unit_economics.levelised_cost.calculator import levelised_cost
from ..unit_economics.production_cost.calculator import production_cost
from .break_even.calculator import break_even
from .irr.calculator import irr
from .mirr.calculator import mirr
from .npv.calculator import npv
from .payback.calculator import payback
from .profitability_index.calculator import profitability_index
from .roi.calculator import roi


def calculate_metrics(ledger, assumptions):
    result = []
    a = assumptions
    for perspective, rate in (
        ("project", value(a.project_discount_rate, "fraction/year", minimum=None)),
        ("equity", value(a.equity_discount_rate, "fraction/year", minimum=None)),
    ):
        recurring = tuple(
            getattr(r, "recurring_" + perspective + "_cash") for r in ledger
        )
        point = tuple(getattr(r, "point_" + perspective + "_cash") for r in ledger)
        discounted = tuple(
            getattr(r, "discounted_" + perspective + "_cash") for r in ledger
        )
        flows = tuple(r + p for r, p in zip(recurring, point))
        result.extend(
            (
                (
                    perspective + "_npv",
                    Metric(
                        npv(recurring, point, rate, a.discount_convention),
                        a.currency,
                        "calculated",
                        "Same annual ledger and explicit discount convention",
                    ),
                ),
                (perspective + "_irr", irr(recurring, point, a.discount_convention)),
                (
                    perspective + "_mirr",
                    mirr(
                        recurring,
                        point,
                        value(a.mirr_finance_rate, "fraction/year", minimum=None),
                        value(a.mirr_reinvestment_rate, "fraction/year", minimum=None),
                        a.discount_convention,
                    ),
                ),
                (perspective + "_payback", payback(flows)),
                (perspective + "_discounted_payback", payback(discounted)),
                (perspective + "_profitability_index", profitability_index(discounted)),
            )
        )
    result.append(("roi", roi(ledger)))
    ratios = [r.dscr.value for r in ledger if r.dscr.value is not None]
    result.append(
        (
            "minimum_dscr",
            Metric(
                min(ratios) if ratios else None,
                "ratio",
                "calculated" if ratios else "undefined",
                "Minimum annual operating cash available for debt service / interest plus principal",
            ),
        )
    )
    products = {p.id for r in ledger for p in r.products}
    if len(products) == 1:
        product = next(iter(products))
        rate = value(a.project_discount_rate, "fraction/year", minimum=None)
        result.append(
            (
                "levelised_cost",
                levelised_cost(ledger, rate, a.discount_convention, product),
            )
        )
        for row in ledger:
            sold = sum((p.sold for p in row.products), Decimal(0))
            saleable = sum((p.saleable for p in row.products), Decimal(0))
            cash, full = production_cost(
                row.fixed_opex + row.variable_opex, row.depreciation, saleable
            )
            quantity, price = break_even(
                row.revenue,
                row.variable_opex,
                row.fixed_opex,
                row.depreciation,
                row.interest,
                sold,
            )
            result.extend(
                (
                    (f"cash_production_cost.{row.period.year}", cash),
                    (f"full_production_cost.{row.period.year}", full),
                    (
                        f"contribution_margin.{row.period.year}",
                        contribution_margin(row.revenue, row.variable_opex, sold),
                    ),
                    (f"break_even_quantity.{row.period.year}", quantity),
                    (f"break_even_price.{row.period.year}", price),
                )
            )
    else:
        result.append(
            (
                "levelised_cost",
                Metric(
                    None,
                    "currency/product unit",
                    "allocation_required",
                    "Multiple products require a user-defined cost allocation; no arbitrary byproduct credit or summed incompatible product units",
                ),
            )
        )
    return tuple(result)
