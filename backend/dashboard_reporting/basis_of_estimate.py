"""M3.6 Basis of Estimate, generated only from one saved study.

Reads the saved equipment and CAPEX stage results. Nothing is recalculated
except one independent reconciliation sum; no engine, web or AI call runs.
Missing information is reported as an open item, never filled in.
"""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from html import escape

from backend.capex.coverage_tiers import classify_line, coverage_tiers, unpriced_significance

VERSION = "basis-of-estimate-2"


def _dec(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return number if number.is_finite() else None


def _stage(state, name):
    stages = (state.get("results") or {}).get("stages", {})
    return stages.get(name) or {}


def _flags(line):
    calc = line.get("calculation") or {}
    evidence = calc.get("evidence") or {}
    estimate = calc.get("estimate") or {}
    flags = []
    floor = evidence.get("below_range_floor")
    if floor:
        ratio = floor.get("size_ratio")
        flags.append("minimum-size floor" + (f" ({_dec(ratio):.0f}x below)" if _dec(ratio) else ""))
    if estimate.get("extrapolated"):
        flags.append("extrapolated beyond range")
    if any("UNVERIFIED" in str(i) for i in line.get("issues") or ()):
        flags.append("unverified correlation")
    if evidence.get("method") == "reviewed_comparable":
        flags.append("user comparable")
    return flags


def _equipment_rows(lines):
    rows = []
    for line in lines:
        calc = line.get("calculation") or {}
        estimate = calc.get("estimate") or {}
        translation = (calc.get("evidence") or {}).get("cost_translation") or {}
        parsed = line.get("parsed_source") or {}
        rows.append({
            "tag": line.get("equipment_tag"),
            "description": parsed.get("classification") if isinstance(parsed, dict) else None,
            "model": line.get("curve_id"),
            "source": estimate.get("source_title") or estimate.get("reference"),
            "source_price_period": translation.get("source_period") or estimate.get("period"),
            "scope": line.get("cost_scope"),
            "amount": line.get("amount"),
            "escalation": translation.get("status") or "none recorded",
            "escalation_series": translation.get("applied_series"),
            "flags": _flags(line),
            "coverage_tier": classify_line(line)["tier"],
        })
    return rows


def _sources(lines, capex):
    refs = {}

    def add(kind, title, detail=""):
        if title:
            refs.setdefault((kind, str(title)), set()).add(str(detail) if detail else "")

    for line in lines:
        estimate = (line.get("calculation") or {}).get("estimate") or {}
        add("equipment cost", estimate.get("source_title") or estimate.get("reference"),
            estimate.get("source_sha256", ""))
        translation = ((line.get("calculation") or {}).get("evidence") or {}).get("cost_translation") or {}
        for point in (translation.get("base_observation"), translation.get("target_observation")):
            if point and point.get("source"):
                add("price index", translation.get("applied_series"), point["source"])
    for factor in capex.get("lines") or []:
        source = factor.get("source") or {}
        if isinstance(source, dict):
            add("capital factor", source.get("reference"), source.get("sha256", ""))
    estimate_class = capex.get("estimate_class") or {}
    add("estimate class", estimate_class.get("reference"))
    return [
        {"kind": kind, "reference": title, "details": sorted(d for d in details if d)}
        for (kind, title), details in sorted(refs.items())
    ]


def _reconcile(capex):
    counted = [b for b in capex.get("breakdown") or [] if b.get("counted")]
    amounts = [_dec(b.get("amount")) for b in counted]
    total = _dec(capex.get("total_capex"))
    if total is None or any(a is None for a in amounts):
        return {"status": "not_reconcilable", "detail": "Total or a counted category has no amount"}
    difference = sum(amounts, Decimal(0)) - total
    ok = abs(difference) <= max(Decimal("1e-6"), abs(total) * Decimal("1e-12"))
    return {
        "status": "reconciled" if ok else "mismatch",
        "sum_of_counted_categories": str(sum(amounts, Decimal(0))),
        "total_capex": str(total),
        "difference": str(difference),
    }


def build_basis_of_estimate(state):
    """Return the Basis of Estimate as a dict, or a not-available record."""
    capex_view = _stage(state, "capex")
    capex = capex_view.get("result") or {}
    run = (state.get("stage_runs") or {}).get("capex") or {}
    if not capex or capex_view.get("status") in {None, "data_required"}:
        return {"status": "not_available", "version": VERSION,
                "reason": "Run CAPEX first; a Basis of Estimate is written only from a saved CAPEX result."}

    equipment_view = _stage(state, "equipment").get("result") or {}
    lines = list(equipment_view.get("equipment") or [])
    if not lines:
        lines = list(((state.get("stage_outputs") or {}).get("equipment") or {}).get("total", {}).get("equipment") or [])
    review = {r.get("equipment_tag"): r for r in (equipment_view.get("pricing_coverage") or {}).get("review_queue") or []}
    unpriced = [
        {"tag": tag, "reason": (review.get(tag) or {}).get("reason"),
         "issues": (review.get(tag) or {}).get("issues", []),
         "value": "unknown; excluded from every total, not zero"}
        for tag in capex.get("unpriced_equipment") or []
    ]
    rows = _equipment_rows([l for l in lines if l.get("amount") is not None])
    estimate_class = capex.get("estimate_class") or {}
    breakdown = capex.get("breakdown") or []
    checks = capex.get("double_count_checks") or []
    stale = capex_view.get("status") == "stale" or bool(capex_view.get("result_is_stale"))
    escalation = {}
    for row in rows:
        escalation[row["escalation"]] = escalation.get(row["escalation"], 0) + 1

    open_items = []
    if stale:
        open_items.append("CAPEX inputs changed after this result; run CAPEX again before relying on it")
    open_items += [f"Unpriced equipment: {u['tag']}" for u in unpriced]
    open_items += [f"No source for capital category: {g}" for g in capex.get("breakdown_gaps") or []]
    open_items += [f"Scope gap: {g}" for g in capex.get("scope_gaps") or []]
    open_items += [f"Double-count check failed: {c.get('id')}" for c in checks if c.get("passed") is False]
    if estimate_class.get("requires_review"):
        open_items.append("Estimate class is a proposal; a reviewer has not confirmed it")
    if escalation.get("general_inflation_proxy"):
        open_items.append(f"{escalation['general_inflation_proxy']} equipment prices escalated with a CPI proxy, not an equipment cost index")
    if escalation.get("none recorded"):
        open_items.append(f"{escalation['none recorded']} equipment prices kept at their source price period; no escalation to a study period recorded")
    unverified = sum(1 for r in rows if "unverified correlation" in r["flags"])
    if unverified:
        open_items.append(f"{unverified} equipment prices from correlations not yet verified against their printed source")
    floored = sum(1 for r in rows if any(f.startswith("minimum-size floor") for f in r["flags"]))
    if floored:
        open_items.append(f"{floored} items priced at a correlation's minimum size; vendor prices would replace the floor")
    extrapolated = sum(1 for r in rows if "extrapolated beyond range" in r["flags"])
    if extrapolated:
        open_items.append(f"{extrapolated} items extrapolated beyond a correlation's published range")
    if any(b.get("ai_suggested") for b in breakdown):
        open_items.append("Some capital factors were suggested by AI; confirm or replace them")
    unpriced_tags = [u["tag"] for u in unpriced]
    # Confirmed aliases reference a priced asset; they are neither priced nor unpriced.
    canonical = [l for l in lines if not (l.get("parsed_source") or {}).get("confirmed_alias")]
    tiers = coverage_tiers(canonical, unpriced_tags)
    significance = unpriced_significance(
        canonical, unpriced_tags,
        (estimate_class.get("class_characteristics") if estimate_class.get("status") != "invalid_input" else None),
    )
    completeness = (equipment_view.get("pricing_coverage") or {}).get("register_completeness") or {}
    if completeness.get("possibly_missing"):
        tiers["meets_coverage_target_without_assumptions"] = False
        tiers["register_completeness"] = "unconfirmed"
        for item in completeness["possibly_missing"]:
            open_items.append(
                f"Possibly missing equipment: {item['label']} is named in the source "
                f"({len(item['evidence'])} mentions) but is not in the register, so it is neither priced nor "
                "counted as unpriced. Add it, or record why it is not separate equipment")
    assumed = tiers["tiers"]["assumption_based"]
    if assumed["items"]:
        share = assumed["fraction_of_priced_value"]
        open_items.append(
            f"{assumed['items']} of {tiers['items']} items are assumption based"
            + (f" ({float(share):.0%} of priced equipment value)" if share is not None else "")
            + "; see the coverage tiers")
    if significance.get("significance") == "significant":
        open_items.append("Unpriced items could exceed the estimate class's typical high range: "
                          + significance["against_estimate_class"]["statement"])
    elif significance.get("status") == "not_assessable":
        open_items.append("Significance of unpriced items could not be assessed: " + significance["reason"])
    reconciliation = _reconcile(capex)
    if reconciliation["status"] != "reconciled":
        open_items.append("Capital breakdown does not reconcile to total CAPEX")

    return {
        "status": "stale" if stale else "current",
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "identification": {
            "assessment": state.get("id"),
            "revision": state.get("revision"),
            "source_file": state.get("filename"),
            "source_sha256": state.get("source_sha256"),
            "description": state.get("description"),
            "capex_run": {k: run.get(k) for k in ("completed_at", "input_hash", "output_hash", "producer")},
        },
        "price_basis": {
            "currency": capex.get("currency"),
            "period": capex.get("period"),
            "index_series": capex.get("index_series"),
            "escalation_by_status": escalation,
        },
        "estimate_class": estimate_class,
        "scope": {
            "priced_equipment": rows,
            "unpriced_equipment": unpriced,
            "scope_subtotals": capex.get("scope_subtotals"),
        },
        "coverage": {"tiers": tiers, "unpriced_significance": significance,
                     "register_completeness": completeness or None},
        "methodology": {
            "capex_method": capex.get("model_id"),
            "process_type": capex.get("process_type"),
            "breakdown": [
                {k: b.get(k) for k in ("category", "label", "status", "amount", "basis", "source", "provisional", "ai_suggested", "counted")}
                for b in breakdown
            ],
            "method_assumptions": list(capex.get("assumptions") or []),
        },
        "totals": {k: capex.get(k) for k in (
            "purchased_equipment", "direct_costs", "indirect_costs", "plant_cost",
            "fixed_capital", "startup_expenses", "working_capital", "total_capex")},
        "exclusions_and_gaps": {
            "categories_without_source": list(capex.get("breakdown_gaps") or []),
            "scope_gaps": list(capex.get("scope_gaps") or []),
            "combined_categories": [b.get("category") for b in breakdown if b.get("status") == "combined"],
        },
        "checks": {"double_count": checks, "reconciliation": reconciliation},
        "user_assumptions": {
            k: v for k, v in (state.get("assumptions") or {}).items()
            if k in {"equipment", "capex", "cost_translation", "estimate_class"}
        },
        "sources": _sources(lines, capex),
        "open_items": open_items,
        "notice": (
            "Generated from the saved study; no figure here is recalculated except the "
            "reconciliation check. A preliminary estimate for review, not a validated design."
        ),
    }


def _money(value):
    number = _dec(value)
    return "—" if number is None else f"{number:,.0f}"


def render_markdown(boe):
    if boe.get("status") == "not_available":
        return "# Basis of Estimate\n\n" + boe["reason"] + "\n"
    ident, basis, cls = boe["identification"], boe["price_basis"], boe["estimate_class"]
    cur = basis.get("currency") or ""
    out = ["# Basis of Estimate", ""]
    if boe["status"] == "stale":
        out += ["> **Stale:** CAPEX inputs changed after this result. Run CAPEX again.", ""]
    out += [
        f"Assessment {ident['assessment']} · revision {ident['revision']} · source `{ident['source_file']}`",
        f"Generated {boe['generated_at']} · {boe['version']}", "", boe["notice"], "",
        "## 1. Price basis", "",
        f"{cur}, {basis.get('period')} ({basis.get('index_series')}).",
        "Equipment escalation: " + (", ".join(f"{k} {v}" for k, v in basis["escalation_by_status"].items()) or "none"), "",
        "## 2. Estimate class", "",
    ]
    if cls.get("status") == "invalid_input":
        out += ["Invalid declarations: " + str(cls.get("error")), ""]
    elif cls:
        ch = cls.get("class_characteristics") or {}
        low, high = ch.get("accuracy_low_percent"), ch.get("accuracy_high_percent")
        out += [
            f"**Class {cls.get('effective_class')}** ({ch.get('end_usage')}), status `{cls.get('status')}`."
            + (f" Typical range: low {low[0]}% to {low[1]}%, high +{high[0]}% to +{high[1]}%." if low and high else ""),
            "",
        ]
        out += [f"- {r}" for r in cls.get("reasons", []) + cls.get("wide_end_reasons", []) + cls.get("issues", [])]
        out += ["", f"_{cls.get('checklist_status')}. Source: {cls.get('reference')}._", ""]
    t = boe["totals"]
    out += ["## 3. Capital summary", "", f"| Item | {cur} |", "|---|---:|"]
    out += [f"| {k.replace('_', ' ').capitalize()} | {_money(t.get(k))} |" for k in t]
    rec = boe["checks"]["reconciliation"]
    out += ["", f"Reconciliation: **{rec['status']}**.", "",
            "## 4. Scope: priced equipment", "",
            f"| Tag | Description | Model | Source period | Scope | {cur} | Escalation | Tier | Flags |",
            "|---|---|---|---|---|---:|---|---|---|"]
    for r in boe["scope"]["priced_equipment"]:
        out.append(f"| {r['tag']} | {r['description'] or ''} | {r['model'] or ''} | {r['source_price_period'] or ''} | "
                   f"{r['scope'] or ''} | {_money(r['amount'])} | {r['escalation']} | {(r.get('coverage_tier') or '').replace('_', ' ')} | {'; '.join(r['flags'])} |")
    out += ["", "### Unpriced equipment", ""]
    unpriced = boe["scope"]["unpriced_equipment"]
    out += [f"- **{u['tag']}**: {u['value']}. {u['reason'] or ''}" for u in unpriced] or ["None."]
    cov = boe.get("coverage") or {}
    tiers = cov.get("tiers") or {}
    if tiers:
        out += ["", "### Coverage tiers", "",
                "| Tier | Items | Share of items | Share of priced value | Confidence |", "|---|---:|---:|---:|---|"]
        for name, t in tiers["tiers"].items():
            frac = lambda v: "—" if v is None else f"{float(v):.0%}"  # noqa: E731
            out.append(f"| {name.replace('_', ' ')} | {t['items']} | {frac(t['fraction_of_items'])} | "
                       f"{frac(t['fraction_of_priced_value'])} | {t['confidence']['statement']} |")
        kinds = tiers.get("assumption_kinds") or {}
        if any(kinds.values()):
            out += ["", "Assumption-based items by reason (an item can have several): "
                    + ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in kinds.items() if v) + "."]
        caveats = tiers.get("source_caveats") or {}
        if caveats:
            out += ["Source caveats (do not change the tier): " + ", ".join(f"{k} {v}" for k, v in caveats.items()) + "."]
        out += ["", f"Source-supported or user-evidence items: {float(tiers['supported_fraction'] or 0):.0%} "
                f"(target {float(tiers['coverage_target']):.0%}). {tiers['notice']}"]
    completeness = cov.get("register_completeness") or {}
    if completeness.get("possibly_missing"):
        out += ["", "### Possibly missing equipment", "",
                "Named in the source but not in the register, so not priced and not counted as unpriced:"]
        out += [f"- **{m['label']}**: " + "; ".join(e['text'] for e in m["evidence"][:3]) for m in completeness["possibly_missing"]]
    sig = cov.get("unpriced_significance") or {}
    if sig.get("status") == "assessed":
        share = sig["share_of_priced_equipment"]
        out += ["", "### Significance of unpriced items", "",
                f"Indicative scale {sig['currency']} {_money(sig['total_band']['low'])} to {_money(sig['total_band']['high'])}, "
                f"{float(share['low']):.0%} to {float(share['high']):.0%} of priced equipment. {sig['notice']}"]
        if sig.get("against_estimate_class"):
            out.append(sig["against_estimate_class"]["statement"])
        out += [f"- {i['tag']}: {_money(i['band']['low'])} to {_money(i['band']['high'])} ({i['basis']})" for i in sig["items"]]
    elif sig.get("status") == "not_assessable":
        out += ["", "### Significance of unpriced items", "", "Not assessable: " + sig["reason"]]
    out += ["", "## 5. Capital breakdown and method", "",
            f"Method: `{boe['methodology']['capex_method']}` · process type: {boe['methodology']['process_type']}", "",
            f"| Category | Status | {cur} | Basis | Provisional | AI-suggested |", "|---|---|---:|---|---|---|"]
    for b in boe["methodology"]["breakdown"]:
        out.append(f"| {b.get('label') or b.get('category')} | {b.get('status')} | {_money(b.get('amount'))} | "
                   f"{(b.get('basis') or '').replace('|', '/')} | {'yes' if b.get('provisional') else ''} | {'yes' if b.get('ai_suggested') else ''} |")
    out += [""] + [f"- {a}" for a in boe["methodology"]["method_assumptions"]]
    gaps = boe["exclusions_and_gaps"]
    out += ["", "## 6. Exclusions and gaps", "",
            "- Categories with no source: " + (", ".join(gaps["categories_without_source"]) or "none"),
            "- Combined into another category: " + (", ".join(gaps["combined_categories"]) or "none"),
            "- Scope gaps: " + (", ".join(map(str, gaps["scope_gaps"])) or "none"), "",
            "## 7. Checks", ""]
    out += [f"- {'Pass' if c.get('passed') else 'FAIL'}: {c.get('id')}" for c in boe["checks"]["double_count"]] or ["- None recorded"]
    out += ["", "## 8. User assumptions", ""]
    out += [f"- {k}: {v.get('rationale', '')} ({v.get('status', '')})" for k, v in boe["user_assumptions"].items()] or ["None recorded."]
    out += ["", "## 9. Sources", ""]
    out += [f"- {s['kind']}: {s['reference']}" + (f" ({'; '.join(s['details'][:3])})" if s["details"] else "") for s in boe["sources"]]
    out += ["", "## 10. Open items", ""]
    out += [f"- {i}" for i in boe["open_items"]] or ["None."]
    return "\n".join(out) + "\n"


def render_html(boe):
    """Simple escaped HTML wrapper around the Markdown text for printing."""
    body = escape(render_markdown(boe))
    return ("<!doctype html><html><head><meta charset='utf-8'><title>Basis of Estimate</title>"
            "<style>body{font:14px/1.5 system-ui;margin:2rem;max-width:72rem}pre{white-space:pre-wrap}</style>"
            "</head><body><pre>" + body + "</pre></body></html>")
