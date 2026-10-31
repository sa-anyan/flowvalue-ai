"""Actual costs are not scaled; driver-based costs use explicit physical ratios."""

from decimal import Decimal

from ..assumptions.calculator import money_at


def calculate_costs(operation, period, assumptions):
    if operation is None:
        return (), Decimal(0), Decimal(0), Decimal(0), False
    drivers = {a.id: a for a in operation.activities}
    if len(drivers) != len(operation.activities):
        raise ValueError("Duplicate activity drivers")
    rows, fixed, variable, cogs, unclassified = (
        [],
        Decimal(0),
        Decimal(0),
        Decimal(0),
        False,
    )
    seen = set()
    for item in operation.costs:
        if item.id in seen or not item.id:
            raise ValueError("Duplicate or missing operating-cost ID")
        seen.add(item.id)
        if item.category in {"depreciation", "interest", "financing"}:
            raise ValueError("Depreciation/financing must not enter cash OPEX")
        if item.behavior not in {"fixed", "variable"} or item.classification not in {
            "cogs",
            "sga",
            "unclassified",
        }:
            raise ValueError("Explicit OPEX behavior and P&L classification required")
        amount = money_at(
            item.amount,
            period.calendar_year,
            assumptions,
            item.price_treatment,
            item.escalation,
        )
        if item.method == "driver":
            driver = drivers.get(item.driver_id)
            if (
                item.behavior != "variable"
                or driver is None
                or driver.unit != item.driver_unit
                or not driver.source
                or item.reference_activity is None
                or item.reference_activity <= 0
            ):
                raise ValueError(
                    "Variable OPEX needs a sourced matching driver and positive reference activity"
                )
            amount *= driver.value / item.reference_activity
        elif (
            item.method != "actual"
            or item.driver_id
            or item.reference_activity is not None
        ):
            raise ValueError("Actual annual OPEX cannot be scaled again")
        rows.append((item.id, item.category, amount))
        if item.behavior == "fixed":
            fixed += amount
        else:
            variable += amount
        if item.classification == "cogs":
            cogs += amount
        if item.classification == "unclassified":
            unclassified = True
    return tuple(rows), fixed, variable, cogs, unclassified
