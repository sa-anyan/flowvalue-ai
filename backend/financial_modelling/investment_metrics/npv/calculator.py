"""NPV uses exactly the ledger's recurring/point timing convention."""

from decimal import Decimal, localcontext

from ...cash_flow.calculator import discount


def npv(recurring, point, rate, convention="discrete_end"):
    if len(recurring) != len(point) or not point:
        raise ValueError("Matching nonempty annual cash series required")
    with localcontext() as c:
        c.prec = 40
        return sum(
            (
                discount(r, p, rate, year, convention)
                for year, (r, p) in enumerate(zip(recurring, point))
            ),
            Decimal(0),
        )
