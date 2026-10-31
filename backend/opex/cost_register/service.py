"""Compile canonical references into the existing engine; never add alternatives."""

import json
from dataclasses import asdict, dataclass, replace
from datetime import date
from decimal import Decimal, localcontext

from ..engine import BASES, overlaps
from ..models import MoneyBase, OpexInputs, OpexResult
from ..registry import calculate_opex, get_factor_ranges
from .models import CostRegister, Evidence

EVIDENCE_KINDS = {
    "garrett_allowance",
    "user_assumption",
    "supplier_quotation",
    "engineering_calculation",
    "researched_estimate",
}
ANNUAL_UNITS = {
    "kW": "kWh/year",
    "kg/h": "kg/year",
    "t/h": "t/year",
    "m3/h": "m3/year",
    "L/h": "L/year",
    "MJ/h": "MJ/year",
    "GJ/h": "GJ/year",
}
MONEY_KINDS = {"unit_price", "salary", "annual_amount", "capital_amount"}


@dataclass(frozen=True)
class RegisterCalculation:
    register_snapshot_id: str
    issues: tuple[str, ...]
    inputs: OpexInputs | None
    result: OpexResult | None
    input_lineage_json: str

    @property
    def status(self):
        return "needs_review" if self.issues else "calculated_preliminary"


@dataclass(frozen=True)
class MethodComparison:
    expense_id: str
    option_id: str
    status: str  # preview only; never changes a baseline or review status
    expense_annual_cost: Decimal | None
    scenario_cash_opex: Decimal | None
    cash_opex_difference: Decimal | None
    issues: tuple[str, ...]
    evidence: tuple[Evidence, ...]


def evidence_issues(evidence):
    issues = []
    if evidence.kind not in EVIDENCE_KINDS:
        issues.append("Unsupported evidence kind: " + evidence.kind)
    if not all(
        (
            evidence.reference.strip(),
            evidence.rationale.strip(),
            evidence.uncertainty.strip(),
            evidence.applicability.strip(),
        )
    ):
        issues.append(
            "Evidence requires reference, rationale, uncertainty and applicability"
        )
    try:
        date.fromisoformat(evidence.as_of)
    except ValueError:
        issues.append("Evidence requires an ISO source/assumption date")
    return issues


def _evaluate(register, *, require_review):
    from .snapshots import register_snapshot_id

    if not isinstance(register, CostRegister):
        raise TypeError("register must be CostRegister")
    categories = {row["id"] for row in get_factor_ranges(register.model_id)}
    issues, lineage = [], {}
    try:
        engineering_context = json.loads(register.engineering_context_json)
        json.dumps(engineering_context, allow_nan=False)
    except (ValueError, TypeError):
        engineering_context = None
        issues.append("Malformed engineering-context JSON")
    if (
        not register.id.strip()
        or not register.actor.strip()
        or not register.change_reason.strip()
    ):
        issues.append("Register ID, actor and change reason required")
    shared, derived, expenses = {}, {}, {}
    for item in (*register.inputs, *register.annual_consumption):
        if not item.id.strip() or item.id in shared or item.id in derived:
            issues.append("Missing or duplicate shared input ID: " + item.id)
        if hasattr(item, "value"):
            shared[item.id] = item
        else:
            derived[item.id] = item
    owners = []
    for expense in register.expenses:
        if not expense.id.strip() or expense.id in expenses:
            issues.append("Missing or duplicate expense ID: " + expense.id)
        expenses[expense.id] = expense
        if expense.category not in categories:
            issues.append(expense.id + ": unknown expense category")
        if not expense.required_scopes or len(set(expense.required_scopes)) != len(
            expense.required_scopes
        ):
            issues.append(expense.id + ": unique required coverage scopes needed")
        for scope in expense.required_scopes:
            if (
                scope.split(":")[0] not in categories
                or not scope.strip()
                or scope.endswith(":")
            ):
                issues.append(expense.id + ": unknown coverage scope " + scope)
            for owner, claimed in owners:
                if overlaps(scope, claimed):
                    issues.append(
                        expense.id
                        + ": expense ownership overlaps "
                        + owner
                        + " at "
                        + scope
                    )
            owners.append((expense.id, scope))
        option_ids = [o.id for o in expense.options]
        if any(not key.strip() for key in option_ids) or len(set(option_ids)) != len(
            option_ids
        ):
            issues.append(expense.id + ": option IDs must be distinct and nonblank")

    cache, visiting = {}, set()

    def resolve(key):
        if key in cache:
            return cache[key]
        if key in visiting:
            raise ValueError("Circular shared-input dependency: " + key)
        visiting.add(key)
        try:
            if key in shared:
                item = shared[key]
                errors = evidence_issues(item.evidence)
                if errors:
                    raise ValueError(key + ": " + "; ".join(errors))
                if item.value is None:
                    raise ValueError("Missing shared input value: " + key)
                if item.kind not in MONEY_KINDS | {
                    "annual_quantity",
                    "demand",
                    "hours",
                    "headcount",
                    "fraction",
                }:
                    raise ValueError("Unsupported shared input kind: " + item.kind)
                if (item.kind in MONEY_KINDS and item.basis != register.basis) or (
                    item.kind not in MONEY_KINDS and item.basis is not None
                ):
                    raise ValueError(
                        key + ": incompatible currency/period or nonmonetary basis"
                    )
                value = (item.value, item.kind, item.unit)
                lineage[key] = asdict(item)
            elif key in derived:
                item = derived[key]
                errors = evidence_issues(item.evidence)
                if errors:
                    raise ValueError(key + ": " + "; ".join(errors))
                demand, demand_kind, demand_unit = resolve(item.demand_id)
                hours, hours_kind, hours_unit = resolve(item.hours_id)
                if (
                    demand_kind != "demand"
                    or hours_kind != "hours"
                    or hours_unit != "h/year"
                    or ANNUAL_UNITS.get(demand_unit) != item.unit
                ):
                    raise ValueError(key + ": incompatible demand/annual-hours units")
                if hours > 8784:
                    raise ValueError(key + ": annual hours exceed a leap year")
                value = (demand * hours, "annual_quantity", item.unit)
                lineage[key] = dict(
                    asdict(item),
                    value=str(value[0]),
                    kind="annual_quantity",
                    derivation="demand × annual operating hours",
                )
            else:
                raise ValueError("Unresolved shared input reference: " + key)
            cache[key] = value
            return value
        finally:
            visiting.remove(key)

    assumptions = []
    for expense in register.expenses:
        selected = next(
            (o for o in expense.options if o.id == expense.active_option_id), None
        )
        if selected is None:
            issues.append(expense.id + ": select exactly one available method")
            continue
        if require_review and (
            not expense.reviewed or not expense.selection_reason.strip()
        ):
            issues.append(
                expense.id + ": active method and coverage require review with a reason"
            )
        if not selected.lines or not selected.evidence:
            issues.append(expense.id + ": active estimate needs lines and evidence")
        for evidence in selected.evidence:
            issues.extend(
                expense.id + ": " + error for error in evidence_issues(evidence)
            )
        provided_scopes = [
            scope for line in selected.lines for scope in line.template.scopes
        ]
        for required in expense.required_scopes:
            if not any(
                scope == required or required.startswith(scope + ":")
                for scope in provided_scopes
            ):
                issues.append(
                    expense.id + ": replacement leaves uncovered scope " + required
                )
        for scope in provided_scopes:
            if not any(
                overlaps(scope, expected) for expected in expense.required_scopes
            ):
                issues.append(expense.id + ": method charges an unowned scope " + scope)
        for line in selected.lines:
            template = line.template
            if template.scope != "recurring":
                issues.append(
                    expense.id
                    + ": an annual OPEX method cannot substitute CAPEX or working capital for recurring coverage"
                )
            if template.category not in {
                s.split(":")[0] for s in expense.required_scopes
            }:
                issues.append(
                    expense.id + ": line category lies outside expense ownership"
                )
            fields, updates, refs = set(), {}, []
            if any(
                getattr(template, field) is not None
                for field in ("amount", "quantity", "rate")
            ):
                issues.append(
                    expense.id
                    + ": numerical values must reference shared inputs, not template copies"
                )
            for binding in line.bindings:
                if (
                    binding.field not in {"amount", "quantity", "rate"}
                    or binding.field in fields
                ):
                    issues.append(expense.id + ": unknown or duplicate field binding")
                    continue
                fields.add(binding.field)
                try:
                    amount, kind, unit = resolve(binding.input_id)
                    expected = {
                        "amount": ("annual_amount", register.basis.currency + "/year"),
                        "quantity": (
                            "headcount"
                            if template.method == "headcount_salary"
                            else "annual_quantity",
                            template.quantity_unit,
                        ),
                        "rate": ("fraction", "fraction")
                        if template.method == "percentage"
                        else (
                            "salary"
                            if template.method == "headcount_salary"
                            else "unit_price",
                            template.rate_unit,
                        ),
                    }[binding.field]
                    if (kind, unit) != expected:
                        raise ValueError(
                            binding.input_id
                            + ": incompatible input kind or units for "
                            + binding.field
                        )
                    updates[binding.field] = amount
                    refs.append(binding.input_id)
                except ValueError as exc:
                    issues.append(expense.id + ": " + str(exc))
            source = (
                template.source
                + "; "
                + "; ".join(e.reference for e in selected.evidence)
            )
            assumptions.append(
                replace(
                    template,
                    **updates,
                    source=source,
                    evidence=template.evidence
                    + tuple(
                        json.dumps(lineage[key], default=str, sort_keys=True)
                        for key in refs
                    )
                    + tuple(
                        json.dumps(asdict(e), sort_keys=True) for e in selected.evidence
                    ),
                )
            )

    bases = []
    needed_bases = {
        row.base
        for row in assumptions
        if row.method == "percentage" and row.base in BASES
    }
    seen_bases = set()
    for binding in register.bases:
        try:
            if binding.base_id not in BASES:
                raise ValueError("Unsupported canonical base: " + binding.base_id)
            if binding.base_id in seen_bases:
                raise ValueError("Duplicate canonical base binding: " + binding.base_id)
            seen_bases.add(binding.base_id)
            if binding.base_id not in needed_bases:
                continue
            amount, kind, unit = resolve(binding.input_id)
            expected = (
                ("annual_amount", register.basis.currency + "/year")
                if binding.base_id == "annual_revenue"
                else ("capital_amount", register.basis.currency)
            )
            if (kind, unit) != expected:
                raise ValueError(
                    binding.base_id + ": incompatible monetary base kind or units"
                )
            bases.append(
                MoneyBase(
                    binding.base_id,
                    amount,
                    register.basis,
                    json.dumps(lineage[binding.input_id], default=str, sort_keys=True),
                )
            )
        except ValueError as exc:
            issues.append(str(exc))
    result, compiled = None, None
    if not issues:
        compiled = OpexInputs(
            register.basis,
            assumptions=tuple(assumptions),
            bases=tuple(bases),
            exclusions=register.exclusions,
            reviewed_categories=register.reviewed_categories,
            process_description=register.process_description,
            location=register.location,
            engineering_context_json=json.dumps(
                {
                    "provided_context": engineering_context,
                    "opex_register": {
                        "snapshot_id": register_snapshot_id(register),
                        "shared_input_lineage": lineage,
                        "active_methods": {
                            e.id: e.active_option_id for e in register.expenses
                        },
                    },
                },
                default=str,
                sort_keys=True,
                allow_nan=False,
            ),
        )
        result = calculate_opex(register.model_id, compiled)
        issues.extend(result.issues)
    return RegisterCalculation(
        register_snapshot_id(register),
        tuple(dict.fromkeys(issues)),
        compiled,
        result,
        json.dumps(lineage, default=str, sort_keys=True),
    )


def calculate_register(register):
    """Only the reviewed active alternatives feed the existing deterministic engine."""
    with localcontext() as context:
        context.prec = 40
        return _evaluate(register, require_review=True)


def compare_methods(register, expense_id):
    """Isolated, labelled draft previews; inactive costs never enter baseline totals."""
    expense = next((e for e in register.expenses if e.id == expense_id), None)
    if expense is None:
        raise ValueError("Unknown expense: " + expense_id)
    with localcontext() as context:
        context.prec = 40
        baseline = _evaluate(register, require_review=False)
        baseline_total = (
            baseline.result.annual_cash_opex
            if baseline.result and not baseline.issues
            else None
        )
        comparisons = []
        for option in expense.options:
            candidate = replace(
                register,
                expenses=tuple(
                    replace(e, active_option_id=option.id) if e.id == expense_id else e
                    for e in register.expenses
                ),
            )
            calculation = _evaluate(candidate, require_review=False)
            result = calculation.result
            total = (
                result.annual_cash_opex if result and not calculation.issues else None
            )
            ids = {line.template.id for line in option.lines}
            amount = (
                sum(
                    (line.amount for line in result.lines if line.id in ids), Decimal(0)
                )
                if total is not None
                else None
            )
            comparisons.append(
                MethodComparison(
                    expense_id,
                    option.id,
                    "needs_review" if calculation.issues else "preview",
                    amount,
                    total,
                    total - baseline_total
                    if total is not None and baseline_total is not None
                    else None,
                    calculation.issues,
                    option.evidence,
                )
            )
        return tuple(comparisons)
