"""Versioned portable register snapshots and explicit immutable review actions."""

import hashlib
import json
from dataclasses import asdict, replace

from ..models import Assumption, Basis, Exclusion
from .models import (
    AnnualConsumption,
    BaseBinding,
    Binding,
    CostRegister,
    EstimateLine,
    EstimateOption,
    Evidence,
    Expense,
    SharedInput,
)


def freeze_register(register):
    if not isinstance(register, CostRegister):
        raise TypeError("register must be CostRegister")
    return json.dumps(
        {"schema_version": 1, "register": asdict(register)},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
        allow_nan=False,
    )


def register_snapshot_id(register):
    return hashlib.sha256(freeze_register(register).encode()).hexdigest()


def restore_register(snapshot):
    payload = json.loads(snapshot)
    if (
        set(payload) != {"schema_version", "register"}
        or type(payload["schema_version"]) is not int
        or payload["schema_version"] != 1
    ):
        raise ValueError("Unsupported register snapshot schema")
    data = payload["register"]
    data["basis"] = Basis(**data["basis"])
    data["inputs"] = tuple(
        SharedInput(
            **dict(
                row,
                evidence=Evidence(**row["evidence"]),
                basis=Basis(**row["basis"]) if row["basis"] else None,
            )
        )
        for row in data["inputs"]
    )
    data["annual_consumption"] = tuple(
        AnnualConsumption(**dict(row, evidence=Evidence(**row["evidence"])))
        for row in data["annual_consumption"]
    )
    expenses = []
    for expense in data["expenses"]:
        options = []
        for option in expense["options"]:
            lines = []
            for line in option["lines"]:
                row = line["template"]
                template = Assumption(
                    **dict(
                        row,
                        basis=Basis(**row["basis"]),
                        scopes=tuple(row["scopes"]),
                        evidence=tuple(row["evidence"]),
                    )
                )
                lines.append(
                    EstimateLine(
                        template, tuple(Binding(**b) for b in line["bindings"])
                    )
                )
            options.append(
                EstimateOption(
                    **dict(
                        option,
                        lines=tuple(lines),
                        evidence=tuple(Evidence(**e) for e in option["evidence"]),
                    )
                )
            )
        expenses.append(
            Expense(
                **dict(
                    expense,
                    required_scopes=tuple(expense["required_scopes"]),
                    options=tuple(options),
                )
            )
        )
    data["expenses"] = tuple(expenses)
    data["bases"] = tuple(BaseBinding(**row) for row in data["bases"])
    data["exclusions"] = tuple(Exclusion(**row) for row in data["exclusions"])
    data["reviewed_categories"] = tuple(data["reviewed_categories"])
    return CostRegister(**data)


def _revision(register, *, actor, reason, expected_snapshot_id, **changes):
    current = register_snapshot_id(register)
    if expected_snapshot_id != current:
        raise ValueError("Stale register revision; reload before applying changes")
    if (
        not isinstance(actor, str)
        or not actor.strip()
        or not isinstance(reason, str)
        or not reason.strip()
    ):
        raise ValueError("Actor and change rationale required")
    return replace(
        register,
        **changes,
        revision=register.revision + 1,
        parent_snapshot_id=current,
        actor=actor,
        change_reason=reason,
    )


def select_method(
    register, expense_id, option_id, *, actor, reason, expected_snapshot_id
):
    expense = next((e for e in register.expenses if e.id == expense_id), None)
    if expense is None or option_id not in {o.id for o in expense.options}:
        raise ValueError("Unknown expense or estimate option")
    replacement = replace(
        expense, active_option_id=option_id, reviewed=False, selection_reason=reason
    )
    affected = _affected_expenses(register, None, {expense_id})
    return _revision(
        register,
        actor=actor,
        reason=reason,
        expected_snapshot_id=expected_snapshot_id,
        expenses=tuple(
            replacement
            if e.id == expense_id
            else replace(e, reviewed=False)
            if e.id in affected
            else e
            for e in register.expenses
        ),
    )


def review_expense(register, expense_id, *, actor, reason, expected_snapshot_id):
    expense = next((e for e in register.expenses if e.id == expense_id), None)
    if expense is None or expense.active_option_id not in {
        o.id for o in expense.options
    }:
        raise ValueError("Select an available estimate before reviewing")
    replacement = replace(expense, reviewed=True, selection_reason=reason)
    return _revision(
        register,
        actor=actor,
        reason=reason,
        expected_snapshot_id=expected_snapshot_id,
        expenses=tuple(
            replacement if e.id == expense_id else e for e in register.expenses
        ),
    )


def affected_expenses(register, input_id):
    """Active input lineage, including annualisation and OPEX component dependencies."""
    return _affected_expenses(register, input_id, set())


def _affected_expenses(register, input_id, initial):
    touched = {input_id}
    while True:
        extra = {
            row.id
            for row in register.annual_consumption
            if row.demand_id in touched or row.hours_id in touched
        }
        if extra <= touched:
            break
        touched |= extra
    changed_bases = {b.base_id for b in register.bases if b.input_id in touched}
    selected = {
        e.id: next((o for o in e.options if o.id == e.active_option_id), None)
        for e in register.expenses
    }
    affected = set(initial)
    while True:
        previous = set(affected)
        changed_items = {
            line.template.id
            for key in affected
            if selected[key]
            for line in selected[key].lines
        }
        changed_categories = {
            line.template.category
            for key in affected
            if selected[key]
            for line in selected[key].lines
        }
        for expense_id, option in selected.items():
            if option is None:
                continue
            for line in option.lines:
                base = line.template.base
                if (
                    any(b.input_id in touched for b in line.bindings)
                    or base in changed_bases
                    or base.startswith("item:")
                    and base[5:] in changed_items
                    or base.startswith("category:")
                    and base[9:] in changed_categories
                ):
                    affected.add(expense_id)
        if affected == previous:
            return tuple(sorted(affected))


def revise_input(register, updated, *, actor, reason, expected_snapshot_id):
    if not isinstance(updated, SharedInput) or updated.id not in {
        s.id for s in register.inputs
    }:
        raise ValueError("Replace an existing canonical SharedInput")
    affected = affected_expenses(register, updated.id)
    return _revision(
        register,
        actor=actor,
        reason=reason,
        expected_snapshot_id=expected_snapshot_id,
        inputs=tuple(
            updated if row.id == updated.id else row for row in register.inputs
        ),
        expenses=tuple(
            replace(e, reviewed=False) if e.id in affected else e
            for e in register.expenses
        ),
    )
