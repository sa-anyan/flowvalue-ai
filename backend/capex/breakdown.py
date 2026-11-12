"""M3.3 capital-cost breakdown and M3.4 double-count checks.

Reads CAPEX cost lines already calculated by the registered methods; adds no
factor and does no estimating of its own. A category with no registered
source is an explicit gap with no amount, never zero.
"""

from decimal import Decimal

from .models import BreakdownLine
from .scope import CATEGORIES, CATEGORY_LABELS, FACTOR_CATEGORIES

_AI_SOURCES = ("ai", "llm", "model suggestion", "ai suggestion", "ai-suggested")


def _ai(inputs, factor_id):
    override = inputs.overrides.get(factor_id)
    if override is None:
        return False
    text = str(getattr(override, "source", "")).strip().casefold()
    return text.startswith(_AI_SOURCES) or "ai suggest" in text or "ai-suggest" in text


def _source(line):
    s = line.source
    return s.reference + ", printed p." + str(s.printed_page)


def _factor_row(line):
    return {
        "id": line.id,
        "fraction": line.fraction,
        "base": line.base,
        "base_amount": line.base_amount,
        "amount": line.amount,
        "status": line.status,
        "formula": line.formula,
    }


def _by_scope(lines):
    out = {}
    for line in lines:
        for scope, entry in line.scope_contributions.items():
            amount = entry.get("amount")
            if amount is None or (entry.get("base") in (None, Decimal(0))):
                continue
            out[scope] = out.get(scope, Decimal(0)) + amount
    return out


def breakdown(spec, lines, inputs, purchase, records):
    """Return (breakdown lines, gap category ids)."""
    rows = []
    lang = spec.method == "lang"
    lang_categories = set(FACTOR_CATEGORIES["lang_factor"]) if lang else set()
    combined = {}
    for line in lines:
        cats = FACTOR_CATEGORIES.get(line.id, ())
        if line.id != "lang_factor" and len(cats) > 1 and line.status != "not_separately_published":
            for c in cats[1:]:
                combined[c] = cats[0]
    provisional_equipment = any(e.provisional for e in inputs.equipment)
    ai_equipment = any(
        (e.provenance or {}).get("ai_suggested") for e in inputs.equipment
    )
    for category in CATEGORIES:
        label = CATEGORY_LABELS[category]
        if category == "purchased_equipment":
            rows.append(
                BreakdownLine(
                    category,
                    label,
                    purchase,
                    "calculated" if purchase is not None else "unavailable",
                    purchase is not None,
                    "Σ quantity-extended purchased cost of "
                    + str(len(inputs.equipment))
                    + " purchased_equipment lines (equipment_cost component only)",
                    "Equipment costing; per-line sources in inclusion_records",
                    True,
                    bool(ai_equipment),
                    by_scope={"purchased_equipment": purchase},
                    note="Provisional equipment prices present"
                    if provisional_equipment
                    else "",
                )
            )
            continue
        if category in lang_categories:
            rows.append(
                BreakdownLine(
                    category,
                    label,
                    None,
                    "combined",
                    False,
                    "Included in the Lang overall installed-plant factor on purchased equipment",
                    spec.source.reference,
                    True,
                    _ai(inputs, "lang_factor"),
                    combined_into="lang_overall",
                )
            )
            continue
        mapped = [
            l
            for l in lines
            if FACTOR_CATEGORIES.get(l.id, (None,))[0] == category
            and l.id != "lang_factor"
        ]
        additive = [l for l in mapped if l.status not in ("embedded", "not_separately_published")]
        unpublished = [l for l in mapped if l.status == "not_separately_published"]
        factors = tuple(_factor_row(l) for l in mapped)
        source = "; ".join(sorted({_source(l) for l in mapped})) or "none"
        ai = any(_ai(inputs, l.id) for l in mapped)
        if category in combined and not additive:
            rows.append(
                BreakdownLine(
                    category,
                    label,
                    None,
                    "combined",
                    False,
                    "Published together with " + CATEGORY_LABELS[combined[category]],
                    source if mapped else spec.source.reference,
                    True,
                    ai,
                    factors,
                    combined_into=combined[category],
                )
            )
            continue
        if not additive:
            embedded = [l for l in mapped if l.status == "embedded"]
            if embedded:
                rows.append(
                    BreakdownLine(
                        category,
                        label,
                        None,
                        "embedded",
                        False,
                        "Embedded in the method's other direct categories; not charged separately",
                        source,
                        True,
                        ai,
                        factors,
                        note=embedded[0].rationale,
                    )
                )
                continue
            rows.append(
                BreakdownLine(
                    category,
                    label,
                    None,
                    "gap",
                    False,
                    "No registered source factor for this category in " + spec.id
                    if not unpublished
                    else "Not separately published by " + spec.id + "; no factor substituted",
                    source,
                    True,
                    False,
                    factors,
                    note="Explicit gap: amount unknown, not zero",
                )
            )
            continue
        excluded = [l for l in additive if l.status == "excluded"]
        live = [l for l in additive if l.status != "excluded"]
        if not live:
            rows.append(
                BreakdownLine(
                    category,
                    label,
                    None,
                    "excluded",
                    False,
                    "Explicitly excluded: " + "; ".join(l.rationale for l in excluded),
                    source,
                    True,
                    ai,
                    factors,
                )
            )
            continue
        amounts = [l.amount for l in live]
        amount = None if any(a is None for a in amounts) else sum(amounts, Decimal(0))
        basis = "; ".join(
            (
                l.id
                + " = "
                + (str(l.fraction) + " × " + l.base if l.fraction is not None else l.formula)
            )
            for l in live
        )
        note = []
        if excluded:
            note.append("excluded: " + ", ".join(l.id for l in excluded))
        embedded = [l for l in mapped if l.status == "embedded"]
        if embedded:
            note.append(
                ", ".join(l.id for l in embedded)
                + " is embedded in the other direct categories and not charged again"
            )
        if unpublished:
            note.append(
                "not separately published: " + ", ".join(l.id for l in unpublished)
            )
        rows.append(
            BreakdownLine(
                category,
                label,
                amount,
                "calculated" if amount is not None else "unavailable",
                amount is not None,
                basis,
                source,
                True,
                ai,
                factors,
                by_scope=_by_scope(live),
                note="; ".join(note),
            )
        )
    if lang:
        line = next((l for l in lines if l.id == "lang_factor"), None)
        amount = (
            line.amount - purchase
            if line is not None and line.amount is not None and purchase is not None
            else None
        )
        rows.append(
            BreakdownLine(
                "lang_overall",
                "Lang overall installation, indirects and contingency",
                amount,
                "calculated" if amount is not None else "unavailable",
                amount is not None,
                "(lang_factor − 1) × purchased_equipment"
                + (" = (" + str(line.fraction) + " − 1) × purchased" if line and line.fraction is not None else ""),
                _source(line) if line else spec.source.reference,
                True,
                _ai(inputs, "lang_factor"),
                (_factor_row(line),) if line else (),
            )
        )
    for scope in ("installed_equipment", "unit_capital"):
        members = [(r, a) for r, a in records if r["scope"] == scope]
        if not members:
            continue
        amount = sum((a for _, a in members), Decimal(0))
        rows.append(
            BreakdownLine(
                scope + "_scope",
                "Pre-costed " + scope.replace("_", " ") + " (source-defined scope)",
                amount,
                "calculated",
                True,
                "Source price × quantity; no plant or installation factor applied. Lines: "
                + ", ".join(r["tag"] + " (" + r["source"] + ")" for r, _ in members),
                "; ".join(sorted({r["basis"] for r, _ in members})),
                True,
                False,
                by_scope={scope: amount},
                note="Inclusions per inclusion_records",
            )
        )
    gaps = tuple(r.category for r in rows if r.status in ("gap", "unavailable"))
    return tuple(rows), gaps


def double_count_checks(spec, lines, records, purchase, plant, capital, rows, totals):
    """Independent, explainable checks that installation is counted once."""
    checks = []
    plant_lines = [
        l
        for l in lines
        if l.scope_contributions
        and set(l.scope_contributions) == {"purchased_equipment"}
    ]
    ok = all(
        l.base_amount is None or l.base == "absolute_user_amount" or l.base_amount == purchase
        for l in plant_lines
    )
    checks.append(
        {
            "id": "plant_factors_on_purchased_only",
            "passed": ok,
            "detail": str(len(plant_lines))
            + " plant/direct/Lang lines; each base equals the purchased-equipment subtotal "
            + str(purchase),
        }
    )
    bad = []
    for l in lines:
        cats = set(FACTOR_CATEGORIES.get(l.id, ()))
        for scope in ("installed_equipment", "unit_capital"):
            entry = l.scope_contributions.get(scope)
            if not entry:
                continue
            for tag in entry.get("tags", ()):
                record = next(r for r, _ in records if r["tag"] == tag)
                if cats & set(record["included"]):
                    bad.append(l.id + " on " + tag)
    checks.append(
        {
            "id": "no_factor_on_source_included_category",
            "passed": not bad,
            "detail": "; ".join(bad) or "no factor charged on a category its source includes",
        }
    )
    recorded = sum((a for _, a in records), Decimal(0))
    checks.append(
        {
            "id": "pre_costed_capital_counted_once",
            "passed": recorded == capital
            and len({r["tag"] for r, _ in records}) == len(records),
            "detail": "installed + unit capital "
            + str(recorded)
            + " added once to plant cost; tags unique",
        }
    )
    counted = [r.amount for r in rows if r.counted]
    total = totals["total_capex"]
    target = total
    if target is None and None not in (totals["fixed_capital"], totals["startup"]):
        target = totals["fixed_capital"] + totals["startup"] + (totals["wc"] or Decimal(0))
    checks.append(
        {
            "id": "breakdown_reconciles",
            "passed": target is not None and sum(counted, Decimal(0)) == target,
            "detail": "Σ counted breakdown "
            + str(sum(counted, Decimal(0)))
            + " vs "
            + ("total_capex " if total is not None else "fixed + startup + wc ")
            + str(target),
        }
    )
    return tuple(checks)
