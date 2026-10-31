"""Independent product sales calculator; uses shared billing validation."""

from ..models import CommercialRevenue
from ..validation import calculate_payment, validate_line


def calculate(line, *, currency, schedule):
    validate_line(line, schedule)
    if line.category != "product_sales":
        raise ValueError("Incorrect revenue category route")
    if not line.included:
        return ()
    rows = []
    for year in line.years:
        amount, quantity, rate, fixed = calculate_payment(line, year, currency)
        rows.append(
            CommercialRevenue(
                line.id,
                line.category,
                line.payment_id,
                year.year,
                quantity,
                line.quantity_unit,
                rate,
                fixed,
                amount,
                "conditional_estimate"
                if line.arrangement == "llm_proposed"
                else line.arrangement,
                line.source_references,
            )
        )
    return tuple(rows)
