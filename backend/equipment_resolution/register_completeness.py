"""Possibly missing equipment: units the source names but the register lacks.

Held-out finding 3: an untagged unit (an RO system) appeared in three stream
descriptions but never entered the equipment register. CAPEX then reported
full coverage with nothing unpriced, which hid the missing unit.

This check is deterministic. It reads only source text (stream names and
descriptions, and the user's process description), never AI notes. An
equipment family named there is flagged when no registered item belongs to
that family. A flag is cleared when such a unit is registered, or when the
user records a decision with a basis in ``plan["register_review"]``:

    {"reverse_osmosis": {"decision": "not_equipment" | "out_of_scope" | "included_in",
                         "basis": "..."}}

Limit: the check works per family. A second, unregistered unit of a family
that already has a registered member is not detected.
"""

import re

FAMILIES = {
    "reverse_osmosis": ("RO / reverse osmosis unit", r"\bRO\b|reverse[- ]osmosis"),
    "electrolyser": ("Electrolyser", r"electroly[sz]er"),
    "pump": ("Pump", r"\bpumps?\b"),
    "compressor": ("Compressor or blower", r"\b(compressors?|blowers?)\b"),
    "tank": ("Tank or vessel", r"\b(tanks?|vessels?|drums?|silos?|receivers?)\b"),
    "reactor": ("Reactor or fermenter", r"(reactors?|fermenters?|digesters?)\b"),
    "column": ("Column or tower", r"\b(columns?|towers?|strippers?|absorbers?|scrubbers?)\b"),
    "heat_exchanger": ("Heat exchanger, heater or cooler",
                       r"(heat[- ]?exchangers?|\bexchangers?\b|\bcoolers?\b|\bheaters?\b|condensers?|reboilers?|chillers?)"),
    "boiler": ("Boiler or steam generator", r"\b(boilers?|steam generators?)\b"),
    "dryer": ("Dryer", r"\b(dryers?|driers?)\b"),
    "centrifuge": ("Centrifuge", r"\bcentrifuges?\b"),
    "filter": ("Filter", r"\bfilters?\b"),
    "separator": ("Separator, settler or clarifier", r"\b(separators?|settlers?|clarifiers?|cyclones?|decanters?|thickeners?)\b"),
    "evaporator": ("Evaporator or crystalliser", r"\b(evaporators?|crystalli[sz]ers?)\b"),
    "mixer": ("Mixer", r"\b(mixers?|agitators?)\b"),
    "ion_exchange": ("Ion-exchange unit", r"ion[- ]exchange"),
    "membrane": ("Membrane unit", r"\bmembranes?\b"),
}
_COMPILED = {k: re.compile(p, re.IGNORECASE if k != "reverse_osmosis" else 0) for k, (_, p) in FAMILIES.items()}
# "reverse osmosis" spelled out is matched case-insensitively; the "RO" acronym only in capitals.
_RO_WORDS = re.compile(r"reverse[- ]osmosis", re.IGNORECASE)
TEXT_PROPERTIES = {"name", "description", "type"}


def _families(text):
    found = set()
    for key, pattern in _COMPILED.items():
        if pattern.search(text) or (key == "reverse_osmosis" and _RO_WORDS.search(text)):
            found.add(key)
    return found


def _equipment_text(entity):
    parts = [str(entity.get("identifier") or "")]
    parts += [str(v.get("normalized_value") or v.get("original_value") or "")
              for v in entity.get("values") or [] if v.get("property") in TEXT_PROPERTIES]
    return " ".join(parts)


def check(report, description="", plan=None, extra_equipment_text=()):
    """Return {"status", "possibly_missing": [...], "resolved": [...], "notice"}."""
    entities = report.get("entities") or []
    registered = set()
    for e in entities:
        if e.get("kind") == "equipment":
            registered |= _families(_equipment_text(e))
    for text in extra_equipment_text:
        registered |= _families(str(text or ""))
    evidence = {}
    for e in entities:
        if e.get("kind") != "material":
            continue
        for v in e.get("values") or []:
            if v.get("property") not in TEXT_PROPERTIES:
                continue
            text = str(v.get("normalized_value") or v.get("original_value") or "")
            for family in _families(text) - registered:
                evidence.setdefault(family, []).append(
                    {"stream": e.get("identifier"), "text": text[:200],
                     "source": f"{v.get('sheet')}!{v.get('cell')}" if v.get("sheet") else None})
    if description:
        for family in _families(description) - registered:
            evidence.setdefault(family, []).append({"stream": None, "text": "process description", "source": None})
    review = (plan or {}).get("register_review") or {}
    flagged, resolved = [], []
    for family, items in sorted(evidence.items()):
        entry = {"family": family, "label": FAMILIES[family][0], "evidence": items[:10]}
        decision = review.get(family) or {}
        if decision.get("decision") and str(decision.get("basis") or "").strip():
            resolved.append({**entry, "decision": decision["decision"], "basis": decision["basis"]})
        else:
            flagged.append(entry)
    return {
        "status": "unconfirmed" if flagged else "no_unregistered_units_named",
        "possibly_missing": flagged,
        "resolved": resolved,
        "notice": ("Units named in the source but absent from the equipment register. They are not priced "
                   "and are not counted as unpriced, so coverage cannot be confirmed until each is added "
                   "or resolved with a basis. Checked per equipment family."),
    }


def carry_over(store, state):
    """Copy equipment-scope decisions from the latest earlier study of the same file.

    Founder decision (12 Nov 2026): register decisions follow a re-uploaded
    workbook. Matching is by the exact source SHA-256, so an edited workbook
    starts without them. Each copied decision records where it came from and
    remains editable. Returns the number of decisions copied.
    """
    sha = state.get("source_sha256")
    if not sha or (state.get("plan") or {}).get("register_review"):
        return 0
    finder = getattr(store, "states_by_source", None)
    if finder is None:
        return 0
    earlier = [s for s in finder(sha) if s.get("id") != state.get("id")
               and ((s.get("plan") or {}).get("register_review"))]
    if not earlier:
        return 0
    source = earlier[-1]
    copied = {}
    for family, decision in source["plan"]["register_review"].items():
        if family in FAMILIES and isinstance(decision, dict) and decision.get("decision"):
            copied[family] = {
                **{k: v for k, v in decision.items() if k != "carried_over_from"},
                "carried_over_from": {"assessment": source.get("id"), "revision": source.get("revision"),
                                      "source_sha256": sha},
            }
    if copied:
        state.setdefault("plan", {})["register_review"] = copied
        state.setdefault("assumptions", {})["register_review"] = {
            "rationale": f"{len(copied)} equipment-scope decision(s) carried over from study "
                         f"{source.get('id')} (same source file)",
            "status": "carried_over",
        }
    return len(copied)
