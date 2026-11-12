"""M3.7 coverage tiers and the significance of unpriced equipment.

Roadmap rev 1.1, R1: missing inputs become labelled assumptions, reported as a
separate tier with a stated confidence. Gate G3, A4: every unpriced item is
visible and its potential significance is assessed.

Every priced line falls into exactly one tier, decided from evidence already
saved on the line. Nothing is recalculated and no AI is called.

- ``source_supported``: a catalogue correlation used inside its published
  range, with every sizing input taken or derived from the study's own data.
- ``user_evidence``: priced from the user's own price, quote or reviewed
  comparable.
- ``assumption_based``: the price depends on an assumption: the minimum-size
  floor, extrapolation beyond the published range, an engineering analogy, or
  a sizing input estimated by AI or assumed without a source.
- ``unpriced``: no price. Excluded from every total, never zero.

Confidence is stated in words with its basis. No numeric confidence or
probability is given, because none has a calibrated basis.

Correlation caveats that are about the source itself (not yet checked against
the printed source, provisional scope, CPI-proxy escalation) do not change the
tier. They are counted separately as source caveats.

The significance band for an unpriced item is the range of prices of
comparable priced items in the same study (same classification, otherwise all
priced items). It is an indication of scale, not a price and not a bound, and
it is never added to any total.
"""

from decimal import Decimal, InvalidOperation

VERSION = "coverage-tiers-1"
TIERS = ("source_supported", "user_evidence", "assumption_based", "unpriced")
COVERAGE_TARGET = Decimal("0.95")  # G3: 95% of verified scope

CONFIDENCE = {
    "source_supported": {
        "level": "stated_source",
        "statement": (
            "Correlation used within its published range, with inputs from the study's "
            "own data. Accuracy is that of the source correlation and the estimate class."
        ),
    },
    "user_evidence": {
        "level": "user_evidence",
        "statement": (
            "Rests on a price, quote or comparable the user supplied and reviewed. "
            "Confidence is that of the user's evidence."
        ),
    },
    "assumption_based": {
        "level": "assumption",
        "statement": (
            "Lower: the price depends on the assumptions listed for each item. "
            "Replace them with measured inputs or vendor prices to move the item up a tier."
        ),
    },
    "unpriced": {
        "level": "none",
        "statement": "No value. Excluded from every total, not zero.",
    },
}

# Sizing-input provenance statuses that mean "not from the study's data".
ASSUMED_INPUT_STATUSES = {
    "llm_estimate": "estimated by AI",
    "assumed": "assumed",
    "ASSUMED": "assumed",
    "derived_from_sources_and_assumptions": "derived partly from assumptions",
}


def _dec(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return number if number.is_finite() else None


def _priced(line):
    return _dec(line.get("amount")) is not None


def _assumed_inputs(line):
    """Names and labels of sizing inputs that did not come from the study."""
    sizing = (line.get("parsed_source") or {}).get("sizing") or {}
    found = {}
    provenance = sizing.get("input_provenance") or {}
    if isinstance(provenance, dict):
        for name, record in provenance.items():
            status = record.get("status") if isinstance(record, dict) else None
            if status in ASSUMED_INPUT_STATUSES:
                found[name] = ASSUMED_INPUT_STATUSES[status]
    evidence = (line.get("calculation") or {}).get("evidence") or {}
    if evidence.get("input_classification") == "ASSUMED":
        found.setdefault("model_input", "assumed")
    # OpenPyTEA second coordinate: the trace keeps the provenance under "source"
    # ({"status": "ASSUMED"|"EXTRACTED"}), or "status" for a manual coordinate.
    second = evidence.get("second_input_conversion") or {}
    source = second.get("source") if isinstance(second.get("source"), dict) else {}
    if "ASSUMED" in (source.get("status"), second.get("status")):
        found.setdefault("second_model_input", "assumed")
    return found


def classify_line(line):
    """Return {"tier", "reasons", "source_caveats"} for one equipment line."""
    if not _priced(line):
        return {"tier": "unpriced", "reasons": ["no price"], "source_caveats": []}
    calc = line.get("calculation") or {}
    evidence = calc.get("evidence") or {}
    estimate = calc.get("estimate") or {}
    label = str(line.get("pricing_status") or "")

    caveats = []
    if any("UNVERIFIED" in str(i) for i in line.get("issues") or ()):
        caveats.append("correlation not yet checked against its printed source")
    if evidence.get("applicability_status") == "provisional":
        caveats.append("provisional model scope")
    if (evidence.get("cost_translation") or {}).get("status") == "general_inflation_proxy":
        caveats.append("escalated with the CPI proxy")

    if (evidence.get("method") == "reviewed_comparable"
            or str(line.get("curve_id") or "").startswith("manual:")
            or label == "USER-PRICED"):
        return {"tier": "user_evidence", "reasons": ["user price, quote or reviewed comparable"],
                "source_caveats": caveats}

    reasons = []
    floor = evidence.get("below_range_floor")
    if floor:
        ratio = _dec((floor or {}).get("size_ratio")) if isinstance(floor, dict) else None
        reasons.append("priced at the correlation's minimum size"
                       + (f" (item {ratio:.0f}x smaller)" if ratio else ""))
    if estimate.get("extrapolated"):
        reasons.append("extrapolated beyond the correlation's published range")
    if label == "ESTIMATED — INDEPENDENT ANALOGY":
        reasons.append("priced by engineering analogy")
    assumed = _assumed_inputs(line)
    if assumed:
        reasons.append(
            f"{len(assumed)} sizing input(s) not from the study: "
            + ", ".join(f"{k} ({v})" for k, v in sorted(assumed.items()))
        )
    tier = "assumption_based" if reasons else "source_supported"
    return {"tier": tier, "reasons": reasons or ["in range; inputs from the study"],
            "source_caveats": caveats}


def _currency(line):
    return ((line.get("calculation") or {}).get("estimate") or {}).get("currency")


def _share(part, whole):
    if part is None or not whole:
        return None
    return str((part / whole).quantize(Decimal("0.001")))


def coverage_tiers(lines, unpriced_tags=()):
    """Tier every line and summarise by count and by priced value.

    lines: plain dict equipment lines (priced and unpriced). unpriced_tags:
    tags known to be unpriced but absent from ``lines``.
    """
    lines = [l for l in lines if isinstance(l, dict)]
    rows = []
    for line in lines:
        rows.append({"tag": line.get("equipment_tag"), "amount": line.get("amount"), **classify_line(line)})
    seen = {r["tag"] for r in rows}
    for tag in unpriced_tags:
        if tag not in seen:
            rows.append({"tag": tag, "amount": None, "tier": "unpriced",
                         "reasons": ["no price"], "source_caveats": []})

    currencies = {_currency(l) for l in lines if _priced(l)}
    same_basis = len(currencies) == 1
    priced_total = sum((_dec(r["amount"]) for r in rows if r["tier"] != "unpriced"), Decimal(0))
    items = len(rows)
    summary = {}
    for tier in TIERS:
        members = [r for r in rows if r["tier"] == tier]
        value = (sum((_dec(r["amount"]) for r in members), Decimal(0))
                 if tier != "unpriced" and same_basis else None)
        summary[tier] = {
            "items": len(members),
            "fraction_of_items": str((Decimal(len(members)) / items).quantize(Decimal("0.001"))) if items else None,
            "value": str(value) if value is not None else None,
            "fraction_of_priced_value": _share(value, priced_total) if same_basis else None,
            "confidence": CONFIDENCE[tier],
            "tags": [r["tag"] for r in members],
        }
    supported = summary["source_supported"]["items"] + summary["user_evidence"]["items"]
    supported_fraction = (Decimal(supported) / items) if items else None
    caveats = {}
    for r in rows:
        for c in r["source_caveats"]:
            caveats[c] = caveats.get(c, 0) + 1
    # Why items are assumption based; an item can count under several kinds.
    kinds = {"minimum_size_floor": "minimum size", "extrapolated": "extrapolated",
             "engineering_analogy": "analogy", "sizing_inputs_not_from_study": "sizing input"}
    assumption_kinds = {
        k: sum(1 for r in rows if r["tier"] == "assumption_based" and any(m in x for x in r["reasons"]))
        for k, m in kinds.items()
    }
    assumption_kinds["only_sizing_inputs_not_from_study"] = sum(
        1 for r in rows if r["tier"] == "assumption_based" and all("sizing input" in x for x in r["reasons"]))
    return {
        "version": VERSION,
        "items": items,
        "tiers": summary,
        "assumption_kinds": assumption_kinds,
        "lines": rows,
        "source_caveats": caveats,
        "value_basis": (f"priced amounts in {currencies.pop()}" if same_basis
                        else "not summed: priced lines are in more than one currency or none"),
        "supported_fraction": str(supported_fraction.quantize(Decimal("0.001"))) if supported_fraction is not None else None,
        "meets_coverage_target_without_assumptions": (supported_fraction >= COVERAGE_TARGET) if supported_fraction is not None else False,
        "coverage_target": str(COVERAGE_TARGET),
        "notice": (
            "Tiers come from evidence saved on each line. Confidence is stated in words "
            "with its basis; no numeric confidence is given because none has a calibrated basis."
        ),
    }


def _classification(line):
    parsed = line.get("parsed_source") or {}
    value = parsed.get("classification") if isinstance(parsed, dict) else None
    if not value:
        value = ((line.get("calculation") or {}).get("estimate") or {}).get("equipment")
    return str(value).strip().lower() if value else None


def unpriced_significance(lines, unpriced_tags=(), class_characteristics=None):
    """Indicative scale of each unpriced item from comparable priced items.

    Never a price and never added to a total. class_characteristics: the
    estimate class's Table 1 row, used to say whether the missing items could
    move the estimate past the class's narrowest typical high range.
    """
    lines = [l for l in lines if isinstance(l, dict)]
    priced = [l for l in lines if _priced(l)]
    by_tag = {l.get("equipment_tag"): l for l in lines}
    tags = list(dict.fromkeys([*unpriced_tags, *(l.get("equipment_tag") for l in lines if not _priced(l))]))
    base = {
        "version": VERSION,
        "unpriced_items": len(tags),
        "notice": (
            "Indicative scale from comparable priced items in this study: not a price, "
            "not a bound, and never added to any total."
        ),
    }
    if not tags:
        return {**base, "status": "none_unpriced", "items": []}
    if len({_currency(l) for l in priced}) != 1:
        return {**base, "status": "not_assessable",
                "reason": "No priced items, or priced items are in more than one currency",
                "items": [{"tag": t, "band": None} for t in tags]}

    priced_total = sum((_dec(l["amount"]) for l in priced), Decimal(0))
    items, low_sum, high_sum = [], Decimal(0), Decimal(0)
    for tag in tags:
        family = _classification(by_tag.get(tag) or {})
        same = [l for l in priced if family and _classification(l) == family]
        pool, basis = (same, f"{len(same)} priced item(s) of the same classification") if same else (
            priced, f"all {len(priced)} priced items in the study (no same-classification item)")
        amounts = sorted(_dec(l["amount"]) for l in pool)
        low, high = amounts[0], amounts[-1]
        low_sum += low
        high_sum += high
        items.append({
            "tag": tag,
            "classification": family,
            "band": {"low": str(low), "high": str(high)},
            "basis": basis,
            "share_of_priced_equipment": {"low": _share(low, priced_total), "high": _share(high, priced_total)},
        })
    high_share = high_sum / priced_total if priced_total else None
    result = {
        **base,
        "status": "assessed",
        "currency": _currency(priced[0]),
        "items": items,
        "total_band": {"low": str(low_sum), "high": str(high_sum)},
        "share_of_priced_equipment": {"low": _share(low_sum, priced_total), "high": _share(high_sum, priced_total)},
        "factored_capex_note": (
            "Under an equipment-factored CAPEX method, fixed capital scales with purchased "
            "equipment, so these shares also indicate the share of fixed capital."
        ),
    }
    high_range = (class_characteristics or {}).get("accuracy_high_percent")
    if high_range and high_share is not None:
        narrowest = Decimal(str(min(high_range)))
        exceeds = high_share * 100 >= narrowest
        result["against_estimate_class"] = {
            "class": class_characteristics.get("class"),
            "narrowest_typical_high_percent": str(narrowest),
            "could_exceed": exceeds,
            "statement": (
                f"The missing items could add up to {high_share * 100:.0f}% of priced equipment, "
                + ("at or above" if exceeds else "below")
                + f" the +{narrowest}% narrowest typical high range of Class {class_characteristics.get('class')}."
            ),
        }
        result["significance"] = "significant" if exceeds else "within_class_range"
    else:
        result["significance"] = "not_compared"
    return result
