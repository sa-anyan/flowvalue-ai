"""Cash-only OPEX import; existing depreciation and financing remain excluded."""

from decimal import Decimal

from backend.opex.models import OpexResult

from ...models import Money, OperatingCost


def costs_from_result(result, *, price_year, classifications=None):
    if (
        not isinstance(result, OpexResult)
        or result.issues
        or result.annual_cash_opex is None
    ):
        raise ValueError("Complete canonical OPEX result required")
    classifications = classifications or {}
    cash_lines = [
        line
        for line in result.lines
        if line.scope == "recurring" and line.accounting == "cash"
    ]
    cash_sum = sum((line.amount for line in cash_lines), Decimal(0))
    # Repeating cost-plus prices may differ in the final Decimal rounding place
    # when cash totals are grouped fixed/variable versus summed by line.
    if abs(cash_sum - result.annual_cash_opex) > Decimal("1e-12") * max(
        1, abs(result.annual_cash_opex)
    ):
        raise ValueError("Canonical OPEX cash lines and total do not reconcile")
    return tuple(
        OperatingCost(
            line.id,
            line.category,
            line.behavior,
            classifications.get(line.id, "unclassified"),
            Money(
                line.amount,
                result.basis.currency,
                price_year,
                "OPEX snapshot " + result.snapshot_id + "; " + line.source,
            ),
            "actual",
            "",
            None,
            "",
            "actual",
        )
        for line in result.lines
        if line.scope == "recurring" and line.accounting == "cash"
    )
