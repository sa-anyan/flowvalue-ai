"""Consume actual canonical sales quantities; no second production ramp or pricing calculation."""

from decimal import Decimal

from backend.revenue.models import RevenueResult

from ...models import Money, ProductSales


def sales_from_result(
    result, revenue_year, *, price_year, selling_cost_reconciliation=""
):
    if (
        not isinstance(result, RevenueResult)
        or result.status != "calculated_preliminary"
        or result.issues
    ):
        raise ValueError("Reviewed complete Revenue result required")
    annual = next((r for r in result.annual if r.year == revenue_year), None)
    if annual is None:
        raise ValueError("Revenue operating year missing")
    rows = [r for r in result.products if r.year == revenue_year]
    commercial = [r for r in result.commercial if r.year == revenue_year]
    if sum((r.net_sales_revenue for r in rows), Decimal(0)) + sum((r.revenue for r in commercial), Decimal(0)) != annual.sales_revenue:
        raise ValueError("Revenue lines do not reconcile")
    if annual.separate_opex_charges and not selling_cost_reconciliation.strip():
        raise ValueError(
            "Reconcile Revenue selling charges with OPEX explicitly before financial handoff"
        )
    return tuple(
        ProductSales(
            r.product_id,
            r.quantity_unit,
            r.produced_quantity,
            r.saleable_quantity,
            r.quantity_sold,
            Money(
                r.net_sales_revenue,
                result.basis.currency,
                price_year,
                "Revenue snapshot " + result.snapshot_id,
            ),
            "; ".join(r.source_references),
        )
        for r in rows
    ) + tuple(ProductSales(r.line_id, r.quantity_unit, r.quantity, r.quantity, r.quantity,
        Money(r.revenue, result.basis.currency, price_year,
            "Revenue snapshot " + result.snapshot_id + "; " + r.category),
        "; ".join(r.source_references) or "Explicit commercial assumption",
        revenue_category=r.category) for r in commercial)
