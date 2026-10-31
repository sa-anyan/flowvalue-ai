"""Explicit savings reduce one matching OPEX item once; never become sales."""

from dataclasses import replace


def validate_savings(savings, schedule, currency):
    from ..engine import read

    ids, targets = set(), set()
    for saving in savings:
        if (
            not saving.id
            or saving.id in ids
            or not saving.target_opex_id
            or saving.target_opex_id in targets
        ):
            raise ValueError("Savings need unique IDs and unique existing OPEX targets")
        ids.add(saving.id)
        targets.add(saving.target_opex_id)
        if type(saving.already_applied) is not bool or saving.already_applied:
            raise ValueError("Savings already applied to costs cannot be applied twice")
        if not saving.rationale.strip():
            raise ValueError("Savings rationale required")
        if len(saving.years) != len(schedule) or {y for y, _ in saving.years} != set(
            schedule
        ):
            raise ValueError("Savings years must match operating schedule")
        for _, assumption in saving.years:
            read(assumption, currency + "/year")


def apply_savings(result, savings, year):
    """Recalculate existing OPEX input assumptions before percentage dependencies."""
    from ..engine import read

    values = list(result)
    for saving in savings:
        matches = [i for i, c in enumerate(values) if c.id == saving.target_opex_id]
        if len(matches) != 1:
            raise ValueError(
                "Savings target must identify one existing OPEX input: "
                + saving.target_opex_id
            )
        i = matches[0]
        cost = values[i]
        amount = read(dict(saving.years)[year], cost.basis.currency + "/year")
        if cost.method == "fixed_annual":
            original = cost.amount
        elif cost.method in {"quantity_price", "headcount_salary"}:
            original = cost.quantity * cost.rate
        else:
            raise ValueError(
                "Savings need explicit annual/itemized cost, not a circular percentage base"
            )
        if amount > original:
            raise ValueError("Avoided cost exceeds existing expense")
        values[i] = replace(
            cost,
            method="fixed_annual",
            amount=original - amount,
            quantity=None,
            rate=None,
            quantity_unit="",
            rate_unit="",
            rationale=cost.rationale
            + "; avoided cost "
            + saving.id
            + ": "
            + saving.rationale,
        )
    return tuple(values)
