"""Deterministic annual costing; no inferred prices, factors or process quantities."""

from decimal import Decimal, localcontext

from .models import CostLine, OpexResult, number, snapshot_id

ZERO = Decimal(0)
METHODS = {
    "quantity_price",
    "headcount_salary",
    "percentage",
    "fixed_annual",
    "engineering",
    "market_price",
}
BASES = {
    "purchased_equipment",
    "installed_equipment",
    "bare_module",
    "fixed_capital",
    "plant_including_startup_excluding_working_capital",
    "annual_revenue",
}
UNITS = {
    "kg",
    "t",
    "g",
    "lb",
    "m3",
    "L",
    "kWh",
    "MWh",
    "MJ",
    "GJ",
    "MMBtu",
    "unit",
    "h",
}


def overlaps(left, right):
    return left == right or left.startswith(right + ":") or right.startswith(left + ":")


def calculate(model_id, definitions, group_checks, inputs):
    # Independent of caller's Decimal precision; only final display should round.
    with localcontext() as context:
        context.prec = 40
        return _calculate(model_id, definitions, group_checks, inputs)


def _calculate(model_id, definitions, group_checks, inputs):
    categories = {c.id: c for c in definitions}
    issues, warnings = (
        [],
        [
            "Historical preliminary methodology; assumptions and engineering completeness are not independently verified."
        ],
    )
    items, money_bases, exclusions = {}, {}, {}
    for base in inputs.bases:
        if base.id not in BASES:
            issues.append("Unsupported money base: " + base.id)
        if base.id in money_bases:
            issues.append("Duplicate money base: " + base.id)
        if base.basis != inputs.basis:
            issues.append("Mixed currency or price period: " + base.id)
        money_bases[base.id] = base.amount
    for item in inputs.assumptions:
        if not item.id or item.id in items:
            issues.append("Missing or duplicate assumption ID: " + item.id)
        items[item.id] = item
    for exclusion in inputs.exclusions:
        if (
            exclusion.category not in categories
            or exclusion.category in exclusions
            or not exclusion.rationale.strip()
        ):
            issues.append("Invalid or duplicate exclusion: " + exclusion.category)
        exclusions[exclusion.category] = exclusion.rationale
    for key in inputs.reviewed_categories:
        if key not in categories:
            issues.append("Unknown reviewed category: " + key)

    claims = []
    invalid = set()
    for item in items.values():
        errors = []
        definition = categories.get(item.category)
        if definition is None:
            errors.append("Unknown cost category")
        if item.method not in METHODS:
            errors.append("Unsupported calculation method")
        if item.behavior not in {"fixed", "variable"}:
            errors.append("Select fixed or variable; split mixed expenses explicitly")
        if item.basis != inputs.basis:
            errors.append("Mixed currency or price period")
        if item.scope not in {"recurring", "capex", "working_capital"}:
            errors.append("Invalid expenditure scope")
        if not all(
            isinstance(x, str) and x.strip()
            for x in (item.rationale, item.source, item.uncertainty)
        ):
            errors.append("Rationale, source and uncertainty are required")
        if not item.scopes or len(set(item.scopes)) != len(item.scopes):
            errors.append("Distinct cost scopes are required")
        if not any(
            s == item.category or s.startswith(item.category + ":") for s in item.scopes
        ):
            errors.append("Scope must identify this cost category")
        for scope in item.scopes:
            if scope.split(":")[0] not in categories or scope.endswith(":"):
                errors.append("Unknown cost scope: " + scope)
        if item.scope == "recurring":
            for scope in item.scopes:
                if scope.split(":")[0] in exclusions:
                    errors.append("Cost scope conflicts with exclusion: " + scope)
                for owner, existing in claims:
                    if overlaps(scope, existing):
                        errors.append(
                            "Overlapping cost scope with " + owner + ": " + scope
                        )
            claims.extend((item.id, s) for s in item.scopes)
        if item.method in {"quantity_price", "headcount_salary"}:
            if (
                item.quantity is None
                or item.rate is None
                or item.amount is not None
                or item.base
            ):
                errors.append("Quantity and rate only are required")
            if item.method == "quantity_price" and (
                not item.quantity_unit.endswith("/year")
                or item.quantity_unit[:-5] != item.rate_unit
                or item.rate_unit not in UNITS
            ):
                errors.append(
                    "Annual quantity unit must match the unit-price denominator; normalize units first"
                )
            if item.method == "headcount_salary" and (
                item.quantity_unit != "FTE" or item.rate_unit != "FTE/year"
            ):
                errors.append("Use FTE headcount and annual salary per FTE (FTE/year)")
        elif item.method == "percentage":
            if (
                item.rate is None
                or not item.base
                or item.quantity is not None
                or item.amount is not None
            ):
                errors.append(
                    "Percentage requires a fraction and one explicit calculation base only"
                )
            if item.scope != "recurring":
                errors.append(
                    "Capital/WC amounts must be explicit, not dependent on annual OPEX"
                )
            if item.category not in item.scopes:
                errors.append("A percentage allowance must cover the complete category")
            if definition and definition.minimum is not None:
                mismatch = (
                    item.base != definition.base
                    or item.rate is not None
                    and not number(definition.minimum)
                    <= item.rate
                    <= number(definition.maximum)
                )
                if mismatch and not (item.override and item.override_reason.strip()):
                    errors.append(
                        "Outside Garrett range or incompatible published calculation base; documented override required"
                    )
                if mismatch:
                    warnings.append(
                        item.id + ": user override differs from Garrett range/base"
                    )
            elif not (item.override and item.override_reason.strip()):
                errors.append(
                    "No Garrett factor for this category; documented assumption override required"
                )
        else:
            if (
                item.amount is None
                or item.quantity is not None
                or item.rate is not None
                or item.base
            ):
                errors.append("Annual allowance requires an amount only")
            if item.method in {"engineering", "market_price"} and not item.evidence:
                errors.append("Engineering/market estimate requires evidence")
            if item.method == "engineering" and not item.engineering_formula.strip():
                errors.append(
                    "Engineering estimate needs a documented calculation, never executable code"
                )
        if item.method != "percentage" and item.override:
            errors.append("Factor override applies only to percentage assumptions")
        if errors:
            invalid.add(item.id)
            issues.extend(item.id + ": " + error for error in errors)

    # A loaded operating salary is not an operating-labor-only factoring base.
    for item in items.values():
        if (
            item.method == "percentage"
            and item.base == "category:operating_labor"
            and any(
                s.split(":")[0] != "operating_labor"
                for row in items.values()
                if row.category == "operating_labor" and row.scope == "recurring"
                for s in row.scopes
            )
        ):
            invalid.add(item.id)
            issues.append(
                item.id
                + ": bundled operating salaries do not provide a clean operating-labor-only base"
            )

    resolved, visiting = {}, set()

    def resolve(key):
        if key in resolved:
            return resolved[key]
        if key in invalid:
            raise ValueError("Invalid dependency: " + key)
        if key in visiting:
            raise ValueError("Circular percentage dependency: " + key)
        item = items[key]
        visiting.add(key)
        try:
            base_value = None
            if item.method in {"quantity_price", "headcount_salary"}:
                amount = item.quantity * item.rate
            elif item.method == "percentage":
                if item.base.startswith("item:"):
                    dependency = item.base[5:]
                    if (
                        dependency not in items
                        or items[dependency].scope != "recurring"
                    ):
                        raise ValueError(
                            "Missing or nonrecurring item base: " + dependency
                        )
                    base_value = resolve(dependency).amount
                elif item.base.startswith("category:"):
                    category = item.base[9:]
                    dependencies = [
                        r.id
                        for r in items.values()
                        if r.category == category and r.scope == "recurring"
                    ]
                    if category not in categories or not dependencies:
                        raise ValueError("Missing category base: " + category)
                    if category not in inputs.reviewed_categories:
                        raise ValueError("Unreviewed category base: " + category)
                    base_value = sum((resolve(d).amount for d in dependencies), ZERO)
                else:
                    if item.base not in money_bases:
                        raise ValueError("Missing named calculation base: " + item.base)
                    base_value = money_bases[item.base]
                amount = base_value * item.rate
            else:
                amount = item.amount
            row = CostLine(
                item.id,
                item.category,
                amount,
                item.behavior,
                categories[item.category].accounting,
                item.scope,
                item.method,
                item.base,
                base_value,
                item.source,
                item.rationale,
                item.uncertainty,
                item.evidence,
                item.scopes,
                item.quantity,
                item.rate,
                item.quantity_unit,
                item.rate_unit,
                item.override_reason,
                item.engineering_formula,
            )
            resolved[key] = row
            return row
        finally:
            visiting.remove(key)

    for key in sorted(items):
        if key not in invalid:
            try:
                resolve(key)
            except ValueError as exc:
                issues.append(key + ": " + str(exc))

    for category in definitions:
        rows = [
            r
            for r in resolved.values()
            if r.scope == "recurring"
            and any(s.split(":")[0] == category.id for s in r.scopes)
        ]
        if category.required and not rows and category.id not in exclusions:
            issues.append("Missing assumption or explicit exclusion: " + category.id)
        if rows and category.id not in inputs.reviewed_categories:
            issues.append("Category completeness not reviewed: " + category.id)

    for name, members, low, high, typical, base in group_checks:
        base_value = money_bases.get(base)
        if base == "category:operating_labor":
            base_value = sum(
                (
                    r.amount
                    for r in resolved.values()
                    if r.category == "operating_labor" and r.scope == "recurring"
                ),
                ZERO,
            )
        if base_value:
            amount = sum(
                (
                    r.amount
                    for r in resolved.values()
                    if r.category in members and r.scope == "recurring"
                ),
                ZERO,
            )
            if not number(low) <= amount / base_value <= number(high):
                warnings.append(
                    name
                    + ": group total outside published comparison range; typical fraction "
                    + typical
                    + " is guidance, not an additional charge"
                )

    lines = tuple(resolved[k] for k in sorted(resolved))
    cash = [r for r in lines if r.scope == "recurring" and r.accounting == "cash"]
    fixed = sum((r.amount for r in cash if r.behavior == "fixed"), ZERO)
    variable = sum((r.amount for r in cash if r.behavior == "variable"), ZERO)
    depreciation = sum(
        (
            r.amount
            for r in lines
            if r.scope == "recurring" and r.accounting == "noncash"
        ),
        ZERO,
    )
    financing = sum(
        (
            r.amount
            for r in lines
            if r.scope == "recurring" and r.accounting == "financing"
        ),
        ZERO,
    )
    # Suppress authoritative totals on incomplete/invalid inputs. Partial subtotal
    # is explicitly labelled and never used by the financial handoff.
    issues = tuple(dict.fromkeys(issues))
    return OpexResult(
        model_id,
        "needs_review" if issues else "calculated_preliminary",
        inputs.basis,
        snapshot_id(inputs),
        None if issues else fixed,
        None if issues else variable,
        None if issues else fixed + variable,
        None if issues else depreciation,
        None if issues else financing,
        None if issues else fixed + variable + depreciation + financing,
        fixed + variable,
        sum((r.amount for r in lines if r.scope == "capex"), ZERO),
        sum((r.amount for r in lines if r.scope == "working_capital"), ZERO),
        lines,
        issues,
        tuple(dict.fromkeys(warnings)),
        definitions[0].source,
    )
