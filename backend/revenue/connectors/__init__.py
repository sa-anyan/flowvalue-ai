"""Explicit import/export adapters. Never run parser, OPEX, UI or financial code."""

from backend.equipment_costing.unit_conversion import Measurement
from backend.opex.models import MoneyBase

from ..models import Assumption, Stream


def stream_from_measurement(
    *,
    stream_id,
    name,
    measurement,
    evidence,
    boundary="unresolved",
    specifications="",
    conversion_context=None,
):
    """Reuse canonical sourced Measurement; no guessing parser layouts or outlets.

    evidence supplies rationale, source, uncertainty, status and as_of. It cannot
    replace the original measured value/unit. No script, workbook or XML executes.
    """
    if not isinstance(measurement, Measurement):
        raise TypeError("Expected canonical Measurement")
    if not measurement.source:
        raise ValueError("Parsed measurement has no source provenance")
    import json

    options = (
        {} if conversion_context is None else {"conversion_context": conversion_context}
    )
    return Stream(
        stream_id,
        name,
        Assumption(measurement.value, measurement.unit, **evidence),
        (json.dumps(measurement.source, sort_keys=True, allow_nan=False),),
        boundary,
        specifications,
        **options,
    )


def annual_revenue_base(result, year):
    """Explicit annual sales base for Garrett OPEX, not an automatic application."""
    if result.status != "calculated_preliminary" or result.issues:
        raise ValueError("Only a reviewed complete revenue scenario can supply OPEX")
    annual = next((r for r in result.annual if r.year == year), None)
    if annual is None:
        raise ValueError("Revenue year unavailable")
    return MoneyBase(
        "annual_revenue",
        annual.sales_revenue,
        result.basis,
        "Net product-sales revenue; year "
        + str(year)
        + "; revenue snapshot "
        + result.snapshot_id
        + "; separate OPEX charges are not deducted here",
    )


def financial_handoff(result):
    """Keep annual sales and separately classified selling OPEX distinct."""
    if result.status != "calculated_preliminary" or result.issues:
        raise ValueError("Incomplete/draft revenue cannot be applied to financials")
    return {
        "currency": result.basis.currency,
        "price_period": result.basis.price_period,
        "revenue_snapshot_id": result.snapshot_id,
        "annual_sales": tuple((r.year, r.sales_revenue) for r in result.annual),
        "unapplied_opex_charges": tuple(
            (row.product_id, row.year, scope, amount)
            for row in result.products
            for scope, amount in row.opex_charges_separate
        ),
        "unapplied_economic_savings": result.avoided_costs,
        "commercial_payments": result.commercial,
        "instruction": "Reconcile separate selling costs with existing OPEX scopes before applying; no OPEX items were added or replaced.",
    }
