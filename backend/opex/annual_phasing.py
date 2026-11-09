"""Explicit fixed-cost mobilization after annual OPEX estimation.

Variable consumption already follows throughput upstream. Never apply production
utilization a second time here. Fixed costs default to 100% once operations start;
any reduction is a user-owned timing scenario, not a Garrett utilization rule.
"""

import hashlib
from dataclasses import replace
from decimal import Decimal

from backend.opex.consumption import decimal


def phase_fixed_costs(result, config, operating_year):
    policy = config.get("cashflow_schedule") or {}
    year = operating_year + int(
        config.get("financial", {}).get("construction_years", 0)
    )
    factor = decimal(policy.get("fixed_opex_factors", {}).get(str(year), 1), maximum=1)
    if factor == 1:
        return result
    reason = str(policy.get("rationale", "")).strip()
    if not reason:
        raise ValueError("Fixed OPEX mobilization requires a recorded schedule basis")
    lines = tuple(
        (
            replace(
                line,
                amount=line.amount * factor,
                rationale=line.rationale
                + f"; project year {year}: annual fixed-cost estimate {line.amount} × mobilization {factor}. {reason}",
                engineering_formula=(
                    line.engineering_formula
                    + f"; annual timing: unphased amount × {factor}"
                ).strip("; "),
            )
            if line.scope == "recurring"
            and line.accounting == "cash"
            and line.behavior == "fixed"
            else line
        )
        for line in result.lines
    )
    fixed = None if result.cash_fixed is None else result.cash_fixed * factor
    variable = result.cash_variable
    cash = None if fixed is None or variable is None else fixed + variable
    delta = sum(
        (old.amount - new.amount for old, new in zip(result.lines, lines)), Decimal(0)
    )
    return replace(
        result,
        snapshot_id=hashlib.sha256(
            (
                result.snapshot_id + f":fixed-mobilization:{year}:{factor}:{reason}"
            ).encode()
        ).hexdigest(),
        lines=lines,
        cash_fixed=fixed,
        annual_cash_opex=cash,
        resolved_cash_subtotal=result.resolved_cash_subtotal - delta,
        annual_expense_including_depreciation_and_financing=(
            None
            if result.annual_expense_including_depreciation_and_financing is None
            else result.annual_expense_including_depreciation_and_financing - delta
        ),
        warnings=(
            *result.warnings,
            f"Fixed cash OPEX mobilization {factor} in project year {year}; user schedule scenario, not a production multiplier.",
        ),
    )
