"""Deterministic staged factorial arithmetic, isolated from live app calculations."""

from dataclasses import replace
from decimal import Decimal, localcontext

from .models import (
    CapexInputs,
    CapexResult,
    CostLine,
    EquipmentCost,
    UnitCapitalCost,
    Override,
    WorkingCapital,
    number,
)
from .breakdown import breakdown as _breakdown
from .breakdown import double_count_checks as _double_count_checks
from .scope import ELIGIBLE, FACTOR_CATEGORIES, eligibility, inclusion_record


def _sum(values):
    values = list(values)
    return None if any(v is None for v in values) else sum(values, Decimal(0))


def _basis(inputs, require_delivered, issues):
    if not inputs.equipment:
        issues.append("No canonical purchased-equipment costs supplied")
        return None, None
    basis = None
    tags = set()
    amounts = []
    for e in inputs.equipment:
        if not isinstance(e, EquipmentCost):
            raise TypeError("equipment must contain EquipmentCost records")
        if (
            not isinstance(e.tag, str)
            or not e.tag.strip()
            or e.tag.strip().casefold() in tags
        ):
            issues.append("Missing or duplicate equipment tag: " + str(e.tag))
            continue
        tags.add(e.tag.strip().casefold())
        if not isinstance(e.cost_scope, str) or not e.cost_scope.strip():
            issues.append(
                e.tag
                + ": no recorded cost scope; rejected rather than defaulted to purchased_equipment"
            )
            continue
        if e.cost_scope != "purchased_equipment":
            issues.append(
                e.tag
                + ": CAPEX factors require purchased cost, not installed, bare-module or unit-price cost"
            )
            continue
        if require_delivered and e.delivery_basis != "delivered":
            issues.append(
                e.tag + ": Nottingham requires confirmed delivered-equipment cost"
            )
            continue
        if not all(
            isinstance(v, str) and v.strip()
            for v in [e.currency, e.period, e.index_series]
        ):
            issues.append(e.tag + ": currency, period and index series are required")
            continue
        try:
            cost = number(e.purchased_cost, "purchased cost")
            quantity = number(e.quantity, "quantity")
            index = number(e.index_value, "index value")
            if quantity <= 0 or quantity != quantity.to_integral_value() or index <= 0:
                raise ValueError(
                    "quantity must be a positive integer and index must be positive"
                )
        except (ValueError, TypeError) as exc:
            issues.append(e.tag + ": " + str(exc))
            continue
        key = (e.currency, e.period, e.index_series, index)
        if basis is not None and basis != key:
            issues.append(
                "Equipment currency, date or cost-index bases differ; reconcile upstream"
            )
            continue
        basis = key
        amounts.append(cost * quantity)
    if issues:
        return None, basis
    total = _sum(amounts)
    if total is None or total <= 0:
        issues.append("Purchased-equipment total must be positive")
        return None, basis
    return total, basis


def _selection(factor, inputs, issues, assumptions):
    if factor.id in inputs.overrides:
        override = inputs.overrides[factor.id]
        if not isinstance(override, Override):
            raise TypeError("Overrides must be Override records")
        if not override.rationale.strip() or not override.source.strip():
            issues.append(factor.id + ": override requires rationale and source")
            return None, None, "missing_override_evidence"
        if (override.fraction is None) == (override.amount is None):
            issues.append(
                factor.id + ": override must supply exactly one of fraction or amount"
            )
            return None, None, "invalid_override"
        try:
            if override.amount is not None:
                return None, number(override.amount), "user_override"
            fraction = number(override.fraction)
        except (ValueError, TypeError) as exc:
            issues.append(factor.id + ": " + str(exc))
            return None, None, "invalid_override"
        assumptions.append(
            factor.id + ": explicit user override; " + override.rationale
        )
        return fraction, None, "user_override"
    try:
        if factor.id in inputs.selected_factors:
            fraction = number(inputs.selected_factors[factor.id], factor.id)
        elif (
            factor.minimum is not None
            and factor.minimum == factor.maximum
            or inputs.factor_selection == "minimum"
        ):
            fraction = number(factor.minimum)
        elif inputs.factor_selection == "maximum":
            fraction = number(factor.maximum)
        elif inputs.factor_selection == "midpoint":
            fraction = (number(factor.minimum) + number(factor.maximum)) / 2
            assumptions.append(
                factor.id
                + ": range midpoint selected by user mode; not a published typical value"
            )
        else:
            issues.append(factor.id + ": factor selection missing")
            return None, None, "missing_factor"
    except (ValueError, TypeError) as exc:
        issues.append(factor.id + ": " + str(exc))
        return None, None, "invalid_factor"
    if factor.minimum is not None and not number(factor.minimum) <= fraction <= number(
        factor.maximum
    ):
        issues.append(
            factor.id
            + ": selected fraction outside source range; use an explicit evidenced override"
        )
        return None, None, "out_of_range"
    return fraction, None, "source_factor"


def _line(factor, inputs, bases, issues, assumptions):
    if not factor.additive:
        if factor.id in inputs.overrides or factor.id in inputs.selected_factors:
            issues.append(
                factor.id
                + ": non-additive/source-embedded category cannot receive an extra factor"
            )
        return CostLine(
            factor.id,
            None,
            None,
            factor.base,
            None,
            factor.formula,
            "not_separately_published" if factor.stage == "information" else "embedded",
            factor.applicability,
            factor.source,
        )
    if factor.id in inputs.exclusions:
        reason = inputs.exclusions[factor.id]
        if not isinstance(reason, str) or not reason.strip():
            issues.append(factor.id + ": exclusion requires a reason")
            return CostLine(
                factor.id,
                None,
                None,
                factor.base,
                bases.get(factor.base),
                factor.formula,
                "missing_exclusion_reason",
                "",
                factor.source,
            )
        return CostLine(
            factor.id,
            Decimal(0),
            None,
            factor.base,
            bases.get(factor.base),
            "explicit exclusion",
            "excluded",
            reason,
            factor.source,
        )
    fraction, amount, status = _selection(factor, inputs, issues, assumptions)
    base = bases.get(factor.base)
    if amount is None and fraction is not None:
        amount = base * fraction if base is not None else None
        if base is None:
            issues.append(factor.id + ": calculation base unavailable: " + factor.base)
    rationale = (
        inputs.overrides[factor.id].rationale
        if factor.id in inputs.overrides
        else factor.applicability
    )
    return CostLine(
        factor.id,
        amount,
        fraction,
        (
            "absolute_user_amount"
            if factor.id in inputs.overrides
            and inputs.overrides[factor.id].amount is not None
            else factor.base
        ),
        base,
        factor.formula if status != "user_override" else "explicit user override",
        status,
        rationale,
        factor.source,
    )


def _working_capital(spec, wc_factor, inputs, bases, issues, assumptions):
    wc = inputs.working_capital
    if wc_factor is None and spec.id == "garrett":
        issues.append(
            "Garrett working-capital profile unavailable until process type is selected"
        )
        return None
    if not isinstance(wc, WorkingCapital):
        raise TypeError("working_capital must be WorkingCapital")
    if type(wc.excluded) is not bool:
        raise ValueError("working_capital.excluded must be boolean")
    if wc.excluded or "working_capital" in inputs.exclusions:
        reason = inputs.exclusions.get("working_capital", wc.rationale)
        if not isinstance(reason, str) or not reason.strip():
            issues.append("working_capital: exclusion requires rationale")
            return None
        return CostLine(
            "working_capital",
            Decimal(0),
            None,
            "excluded",
            None,
            "explicit exclusion",
            "excluded",
            reason,
            spec.source,
        )
    method = wc.method
    if method == "model_default":
        if spec.id == "garrett":
            method = "plant_fraction"
        elif spec.id == "nottingham":
            method = (
                "published_table"
                if inputs.factor_basis_mode == "published_table"
                else "total_investment_fraction"
            )
        else:
            method = "months_opex"
    if (
        method != "published_table"
        and spec.id != "garrett"
        and (
            "working_capital" in inputs.selected_factors
            or "working_capital" in inputs.overrides
        )
    ):
        issues.append(
            "Use WorkingCapital assumptions for this working-capital basis, not the published-table factor selector"
        )
        return None
    if (
        "working_capital" in inputs.selected_factors
        or "working_capital" in inputs.overrides
    ) and (
        method not in ["published_table", "plant_fraction"]
        or wc.fraction is not None
        or wc.amount is not None
    ):
        issues.append(
            "Choose one working-capital selection path; use WorkingCapital for custom bases/amounts"
        )
        return None
    if method == "published_table":
        if wc.fraction is not None or wc.amount is not None:
            issues.append(
                "Select an explicit working-capital basis instead of overriding the published-table method with WorkingCapital fraction/amount"
            )
            return None
        if wc_factor is None:
            issues.append(
                "Working-capital profile unavailable until process type is selected"
            )
            return None
        if spec.id != "nottingham":
            issues.append(
                "Published working-capital table belongs only to Nottingham detailed model"
            )
            return None
        return _line(wc_factor, inputs, bases, issues, assumptions)
    if method == "absolute":
        if wc.amount is None or not wc.rationale.strip():
            issues.append("Absolute working capital requires an amount and rationale")
            return None
        amount = number(wc.amount, "working capital")
        fraction = None
        base = None
        name = "absolute_user_amount"
        formula = "user amount"
    elif method == "months_opex":
        if wc.annual_opex is None or wc.months is None:
            issues.append(
                "Working capital needs annual_opex and explicitly selected months"
            )
            return None
        months = number(wc.months, "working capital months")
        if (
            spec.id.startswith("nottingham")
            and not Decimal(3) <= months <= Decimal(6)
            and not wc.rationale.strip()
        ):
            issues.append(
                "Nottingham working capital outside documented 3–6 months requires rationale"
            )
            return None
        if spec.id == "garrett" and not wc.rationale.strip():
            issues.append(
                "Months-of-OPEX working capital is a user assumption for Garrett; rationale required"
            )
            return None
        base = number(wc.annual_opex, "annual OPEX")
        fraction = months / 12
        amount = base * fraction
        name = "annual_opex"
        formula = "annual_opex * months / 12"
    else:
        choices = {
            "plant_fraction": ("plant_cost", Decimal(".10"), Decimal(".20")),
            "annual_opex_fraction": ("annual_opex", Decimal(".10"), Decimal(".35")),
            "installed_equipment_fraction": (
                "installed_equipment",
                Decimal(".50"),
                Decimal(".50"),
            ),
            "total_investment_fraction": (
                "total_investment",
                Decimal(".15"),
                Decimal(".15"),
            ),
        }
        if method not in choices:
            issues.append("Unsupported working-capital method: " + method)
            return None
        name, low, high = choices[method]
        if (
            method == "total_investment_fraction"
            and spec.id != "nottingham"
            and not wc.rationale.strip()
        ):
            issues.append(
                "Total-investment working-capital fraction is a user assumption for this model; rationale required"
            )
            return None
        fraction = (
            number(wc.fraction, "working capital fraction")
            if wc.fraction is not None
            else None
        )
        if (
            fraction is None
            and method == "total_investment_fraction"
            and spec.id == "nottingham"
        ):
            fraction = Decimal(".15")
        if fraction is None and spec.id == "garrett":
            selection = type(wc_factor)(
                wc_factor.id,
                str(low),
                str(high),
                name,
                wc_factor.stage,
                wc_factor.formula,
                wc_factor.applicability,
                wc_factor.source,
            )
            fraction, absolute, _status = _selection(
                selection, inputs, issues, assumptions
            )
            if absolute is not None:
                return CostLine(
                    "working_capital",
                    absolute,
                    None,
                    "absolute_user_amount",
                    None,
                    "user amount",
                    "user_override",
                    inputs.overrides["working_capital"].rationale,
                    spec.source,
                )
        if fraction is None:
            issues.append("Working capital needs an explicitly selected fraction")
            return None
        if (
            not low <= fraction <= high
            and not wc.rationale.strip()
            and "working_capital" not in inputs.overrides
        ):
            issues.append(
                "Working-capital fraction outside source range requires explicit rationale"
            )
            return None
        if method == "total_investment_fraction":
            if fraction >= 1:
                issues.append(
                    "Working capital / total investment fraction must be below one"
                )
                return None
            base = bases.get("fixed_capital")
            amount = None if base is None else base * fraction / (1 - fraction)
            formula = "fixed_capital * fraction / (1 - fraction)"
        else:
            base = (
                number(wc.annual_opex, "annual OPEX")
                if name == "annual_opex" and wc.annual_opex is not None
                else bases.get(name)
            )
            if name == "installed_equipment":
                base = (
                    number(wc.installed_equipment_cost, "installed equipment cost")
                    if wc.installed_equipment_cost is not None
                    else None
                )
            amount = None if base is None else base * fraction
            formula = "fraction * " + name
        if base is None:
            issues.append("Working-capital calculation base is missing: " + name)
        if (
            spec.id != "garrett"
            and method
            in [
                "plant_fraction",
                "annual_opex_fraction",
                "installed_equipment_fraction",
            ]
            and not wc.rationale.strip()
        ):
            issues.append(
                "This working-capital basis is a user assumption for Nottingham; rationale required"
            )
            return None
    assumptions.append("Working-capital method: " + method + "; " + wc.rationale)
    source = (
        replace(
            spec.source,
            reference="Nottingham CEEDG501, section 5 working capital",
            printed_page=12,
            pdf_page=12,
            note="Section 5 working capital: 3–6 months of operating cost",
        )
        if method == "months_opex" and spec.id.startswith("nottingham")
        else spec.source
    )
    if method == "installed_equipment_fraction" and spec.id == "garrett":
        source = replace(
            spec.source,
            printed_page=41,
            pdf_page=53,
            note="Rough installed-equipment working-capital alternative; not an equipment-cost addition",
        )
    return CostLine(
        "working_capital",
        amount,
        fraction,
        name,
        base,
        formula,
        "user_assumption" if wc.rationale else "source_method",
        wc.rationale or "Published working-capital basis",
        source,
    )


def _scoped_line(factor, inputs, bases, records, scoped, gaps, issues, assumptions):
    """Indirect/fee factor charged on each eligible scope's own base.

    Purchased equipment uses the model's stage base. An installed or unit
    capital record joins the base only when the factor is expressed on a
    direct-cost subtotal and its source is recorded as excluding every
    category the factor covers. Bases are kept per scope; nothing is summed
    across scopes before the factor is chosen.
    """
    purchased_base = bases.get(factor.base)
    extra = Decimal(0)
    contributions = {
        "purchased_equipment": {"base": purchased_base},
        "installed_equipment": {"base": Decimal(0), "tags": []},
        "unit_capital": {"base": Decimal(0), "tags": []},
    }
    for record, amount in records:
        applies, status, reason = eligibility(record, factor.id)
        categories = FACTOR_CATEGORIES.get(factor.id, ())
        if applies and factor.base not in ("direct_costs", "direct_and_indirect"):
            applies, status = False, "basis_purchased_only"
            reason = (
                "factor is expressed on "
                + factor.base
                + "; the method gives no basis to apply it to "
                + record["scope"]
            )
        if not applies:
            partly = status == "already_included" and any(
                c in record["excluded"] for c in categories
            )
            if status in ("unknown", "basis_purchased_only") or partly:
                for c in categories:
                    if c in record["included"]:
                        continue
                    gaps.append(
                        {
                            "tag": record["tag"],
                            "scope": record["scope"],
                            "factor": factor.id,
                            "category": c,
                            "status": "combined_factor_partly_included"
                            if partly
                            else status,
                            "reason": reason,
                        }
                    )
            continue
        base = amount
        if factor.base == "direct_and_indirect":
            base += scoped.get(record["tag"], Decimal(0))
        extra += base
        contributions[record["scope"]]["base"] += base
        contributions[record["scope"]]["tags"].append(record["tag"])
    scoped_bases = dict(bases)
    if purchased_base is not None and factor.base in scoped_bases:
        scoped_bases[factor.base] = purchased_base + extra
    line = _line(factor, inputs, scoped_bases, issues, assumptions)
    fraction = line.fraction
    for name, entry in contributions.items():
        entry["amount"] = (
            entry["base"] * fraction
            if fraction is not None and entry["base"] is not None
            else None
        )
    if fraction is not None and factor.stage == "indirect":
        # Remember indirects charged per record, for direct_and_indirect bases.
        for record, amount in records:
            if record["tag"] in contributions[record["scope"]]["tags"]:
                scoped[record["tag"]] = (
                    scoped.get(record["tag"], Decimal(0)) + amount * fraction
                )
    return replace(line, scope_contributions=contributions)


def _purchased_parts(lines, stage, factors):
    ids = {f.id for f in factors if f.stage == stage and f.additive}
    parts = []
    for line in lines:
        if line.id not in ids:
            continue
        part = line.scope_contributions.get("purchased_equipment", {})
        # Absolute overrides are not split by scope; they stay whole.
        parts.append(
            part.get("amount") if line.fraction is not None else line.amount
        )
    return parts


def _uncovered_gaps(factors, records, gaps):
    """Categories a non-purchased record could receive but the method lacks."""
    covered = set()
    for f in factors:
        if f.stage in ("indirect", "fees") and f.additive:
            covered.update(FACTOR_CATEGORIES.get(f.id, ()))
    seen = {(g["tag"], g["category"]) for g in gaps}
    out = []
    for record, _ in records:
        for c in sorted(ELIGIBLE[record["scope"]]):
            if c == "owners_costs" or c in record["included"]:
                continue
            if c in covered or (record["tag"], c) in seen:
                continue
            out.append(
                {
                    "tag": record["tag"],
                    "scope": record["scope"],
                    "factor": None,
                    "category": c,
                    "status": "no_factor_in_method",
                    "reason": "selected CAPEX method has no factor for this category on "
                    + record["scope"],
                }
            )
    return out


def calculate(spec, factors, inputs):
    if not isinstance(inputs, CapexInputs):
        raise TypeError("inputs must be CapexInputs")
    issues = []
    assumptions = list(spec.notes)
    lines = []
    if inputs.process_type not in spec.process_types:
        issues.append("Missing or unsupported process_type for " + spec.id)
    if inputs.factor_selection not in ["selected", "minimum", "maximum", "midpoint"]:
        issues.append("Unsupported factor_selection")
    if inputs.indirect_basis not in ["purchased_equipment", "direct_costs"]:
        issues.append("Unsupported indirect_basis")
    if inputs.factor_basis_mode not in ["published_table", "relationships"]:
        issues.append("Unsupported factor_basis_mode")
    ids = {f.id for f in factors}
    for name in (
        set(inputs.selected_factors) | set(inputs.overrides) | set(inputs.exclusions)
    ):
        if name not in ids:
            issues.append("Unknown factor for selected model: " + name)
    if set(inputs.selected_factors) & set(inputs.overrides) or set(
        inputs.exclusions
    ) & (set(inputs.selected_factors) | set(inputs.overrides)):
        issues.append("Factor cannot be both selected, overridden or excluded")
    purchase, basis = (
        _basis(inputs, spec.requires_delivered_equipment, issues)
        if inputs.equipment or not inputs.pre_costed_capital
        else (Decimal(0), None)
    )
    capital_amount = Decimal(0)
    records = []  # (inclusion record, quantity-extended amount)
    capital_tags = {e.tag.strip().casefold() for e in inputs.equipment}
    for e in inputs.pre_costed_capital:
        if not isinstance(e, UnitCapitalCost):
            raise TypeError("pre_costed_capital must contain UnitCapitalCost records")
        if not isinstance(e.cost_scope, str) or not e.cost_scope.strip():
            issues.append(
                str(e.tag)
                + ": no recorded cost scope; rejected rather than defaulted to unit_capital or purchased_equipment"
            )
            continue
        if e.cost_scope not in {
            "unit_capital",
            "installed_equipment",
            "module_estimate",
        }:
            issues.append(
                e.tag
                + ": only scoped unit/installed/module capital supported here; whole-project TOTAL_CAPITAL cannot be combined without a decomposition"
            )
            continue
        if not e.tag.strip() or e.tag.strip().casefold() in capital_tags:
            issues.append("Duplicate purchased/capital equipment tag: " + e.tag)
            continue
        capital_tags.add(e.tag.strip().casefold())
        try:
            key = (e.currency, e.period, e.index_series, number(e.index_value))
            quantity = number(e.quantity)
            if (
                not all(isinstance(x, str) and x.strip() for x in key[:3])
                or key[3] <= 0
                or quantity <= 0
                or quantity != quantity.to_integral_value()
            ):
                raise ValueError(
                    "Capital records require currency, date, index and integer quantity"
                )
            if basis is not None and key != basis:
                raise ValueError(
                    "Capital/purchased date, currency or index bases differ; reconcile upstream"
                )
            basis = key
            amount = number(e.amount) * quantity
            capital_amount += amount
            records.append(
                (
                    inclusion_record(
                        e.tag,
                        e.cost_scope,
                        e.provenance,
                        e.included_categories,
                    ),
                    amount,
                )
            )
            lines.append(
                CostLine(
                    "unit_capital:" + e.tag,
                    amount,
                    None,
                    "pre_costed_unit_capital",
                    amount,
                    "source capital amount × quantity; no plant or installation factors",
                    "provisional",
                    "Source-defined "
                    + e.cost_scope
                    + " scope; only factors its source excludes are applied, on separate bases",
                    spec.source,
                    {records[-1][0]["scope"]: {"base": amount, "amount": amount}},
                )
            )
        except (ValueError, TypeError) as exc:
            issues.append(e.tag + ": " + str(exc))
    if inputs.pre_costed_capital:
        assumptions.append(
            "Pre-costed installed/unit capital is excluded from all purchased-equipment plant-factor bases and added once to plant cost. It receives only indirect, contingency or owner's-cost factors its source is recorded as excluding (B08 decision C)."
        )
    for e in inputs.equipment:
        for category in e.included_categories:
            if category in ids and category not in inputs.exclusions:
                issues.append(
                    e.tag
                    + ": "
                    + category
                    + " already included in equipment cost; exclude overlapping factor or revise input scope"
                )
    if any(e.provisional for e in inputs.equipment):
        assumptions.append("Canonical equipment prices include provisional estimates")
    bases = {"purchased_equipment": purchase}
    scoped = {}  # tag -> indirect amount already charged on that record
    gaps = []
    for factor in factors:
        if factor.stage == "information":
            lines.append(_line(factor, inputs, bases, issues, assumptions))
    # Invalid/mixed equipment bases must never feed arithmetic.
    if issues:
        purchase = None
        bases["purchased_equipment"] = None
    with localcontext() as context:
        context.prec = 28
        direct = []
        indirect = []
        fees = []
        for stage, amounts in [
            ("direct", direct),
            ("indirect", indirect),
            ("fees", fees),
            ("lang", direct),
        ]:
            for factor in factors:
                if factor.stage != stage:
                    continue
                if stage in ("indirect", "fees"):
                    line = _scoped_line(
                        factor, inputs, bases, records, scoped, gaps, issues, assumptions
                    )
                else:
                    line = _line(factor, inputs, bases, issues, assumptions)
                    if factor.additive and factor.base == "purchased_equipment":
                        line = replace(
                            line,
                            scope_contributions={
                                "purchased_equipment": {
                                    "base": line.base_amount,
                                    "amount": line.amount,
                                }
                            },
                        )
                lines.append(line)
                if factor.additive:
                    amounts.append(line.amount)
            if stage == "direct":
                bases["direct_costs"] = _sum(
                    ([purchase] if spec.method != "lang" else []) + direct
                )
            if stage == "indirect":
                # Purchased path only; installed/unit records add their own
                # amount and indirects in _scoped_line, never twice.
                bases["direct_and_indirect"] = _sum(
                    [bases["direct_costs"], _sum(_purchased_parts(lines, "indirect", factors))]
                )
        if spec.method == "lang":
            direct_total = _sum(direct)
            indirect_total = Decimal(0)
            plant = direct_total
        else:
            direct_total = bases["direct_costs"]
            indirect_total = _sum(indirect + fees)
            plant = _sum([direct_total, indirect_total])
        direct_total = _sum([direct_total, capital_amount])
        plant = _sum([plant, capital_amount])
        bases["plant_cost"] = plant
        offsite = Decimal(0)
        startup = Decimal(0)
        for factor in factors:
            if factor.stage not in ["offsite", "startup"]:
                continue
            line = _line(factor, inputs, bases, issues, assumptions)
            if (
                factor.id == "offsite_facilities"
                and line.amount is not None
                and line.amount > 0
                and not (
                    isinstance(inputs.offsite_scope_confirmation, str)
                    and inputs.offsite_scope_confirmation.strip()
                )
            ):
                issues.append(
                    "Offsite allowance requires confirmation that utilities/buildings/environmental and other facilities are not counted twice"
                )
                line = CostLine(
                    line.id,
                    None,
                    line.fraction,
                    line.base,
                    line.base_amount,
                    line.formula,
                    "scope_review_required",
                    line.rationale,
                    line.source,
                )
            lines.append(line)
            if factor.stage == "offsite":
                offsite = line.amount
            else:
                startup = line.amount
        fixed = _sum([plant, offsite])
        bases["fixed_capital"] = fixed
        wc_factor = next((f for f in factors if f.stage == "working_capital"), None)
        try:
            wc_line = _working_capital(
                spec, wc_factor, inputs, bases, issues, assumptions
            )
        except (ValueError, TypeError) as exc:
            issues.append(str(exc))
            wc_line = None
        if wc_line:
            lines.append(wc_line)
        wc = wc_line.amount if wc_line else None
        total = _sum([fixed, startup, wc])
    if issues:
        total = None
    gaps.extend(_uncovered_gaps(factors, records, gaps))
    installed_total = sum(
        (a for r, a in records if r["scope"] == "installed_equipment"), Decimal(0)
    )
    unit_total = sum(
        (a for r, a in records if r["scope"] == "unit_capital"), Decimal(0)
    )
    scope_subtotals = {
        "purchased_equipment": purchase,
        "installed_equipment": installed_total,
        "unit_capital": unit_total,
    }
    inclusion_records = tuple(
        inclusion_record(
            e.tag, e.cost_scope, e.provenance, e.included_categories
        )
        for e in inputs.equipment
        if isinstance(e, EquipmentCost) and e.cost_scope
    ) + tuple(r for r, _ in records)
    breakdown_lines, breakdown_gaps = _breakdown(
        spec, tuple(lines), inputs, purchase, records
    )
    checks = _double_count_checks(
        spec,
        tuple(lines),
        records,
        purchase,
        plant,
        capital_amount,
        breakdown_lines,
        {"total_capex": total, "fixed_capital": fixed, "startup": startup, "wc": wc},
    )
    evidence = {
        "model_source": spec.source,
        "method": spec.method,
        "process_description": inputs.process_description,
        "equipment_information": inputs.equipment_information,
        "equipment": inputs.equipment,
        "pre_costed_capital": inputs.pre_costed_capital,
        "pre_costed_capital_total": capital_amount,
        "fixed_capital_definition": "core plant plus offsite facilities; excludes startup and working capital",
        "total_capex_definition": "fixed_capital + startup_expenses + working_capital",
        "inactive": True,
    }
    return CapexResult(
        spec.id,
        inputs.process_type,
        "needs_review" if issues else "provisional",
        purchase,
        direct_total,
        indirect_total,
        plant,
        fixed,
        startup,
        wc,
        total,
        basis[0] if basis else None,
        basis[1] if basis else None,
        basis[2] if basis else None,
        basis[3] if basis else None,
        tuple(lines),
        tuple(issues),
        tuple(assumptions),
        evidence,
        scope_subtotals,
        inclusion_records,
        tuple(gaps),
        checks,
        breakdown_lines,
        breakdown_gaps,
    )
