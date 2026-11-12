"""Deterministic first-pass equipment-to-model matching (prototype).

Runs in milliseconds and needs no AI call, so matches can be shown as soon as
the equipment register is extracted. The same register always gives the same
result. It proposes; it never confirms. Every outcome is one of:

* ``auto``       one model clearly fits the named function and configuration;
                 preselected, the user can change it.
* ``choose``     the function is clear but several models fit equally well;
                 the user picks from a short list (the UI pop-up).
* ``prefix_only`` only the tag prefix suggests a function (a P- tag is not
                 necessarily a pump), so the user must confirm.
* ``unmatched``  no function could be established; the AI matcher (or the
                 user) takes over.

All rules are generic engineering vocabulary held in this table and in the
catalogue's own names and aliases. No project, tag or workbook appears here
(enforced by ``test_prompts_contain_no_project_equipment_tags``).
"""

import math
import re
from functools import lru_cache

from backend.equipment_matching.sizing_paths import available as sizing_available
from backend.equipment_matching.sizing_paths import link_design_basis
from backend.equipment_matching.sizing_paths import path as sizing_path
from backend.equipment_matching.service import (
    catalogue,
    contextual_descriptions,
    equipment_register,
    source_name_hints,
    words,
)

VERSION = "deterministic-matcher-0.3-design-basis"

# Family -> (label, pattern on equipment wording). Order does not matter: the
# longest match nearest the end of a phrase (its head noun) wins.
FAMILIES = {
    "ph_adjustment": ("pH adjustment / neutralisation", r"\bph[- ]?adjust\w*|neutrali[sz]\w*|acid dosing"),
    "electrolyser": ("Electrolyser", r"electroly[sz]\w*|electrochemical"),
    "ion_exchange": ("Ion exchange", r"\b(?:cation|anion|ion)[- ]?exchang\w*|\bdeminerali[sz]\w*"),
    "reverse_osmosis": ("Reverse osmosis", r"reverse[- ]osmosis|packaged ro\b|\bro\b(?= (?:unit|system|plant|skid|purification|membrane|pretreatment|package))"),
    "membrane": ("Membrane separation", r"\bmembranes?\b|ultrafiltration|nanofiltration|pervaporation|gas permeation"),
    "pump": ("Pump", r"\bpumps?\b"),
    "compressor": ("Compressor, fan or blower", r"\b(?:compressors?|blowers?|fans?)\b"),
    "heat_exchanger": ("Heat exchanger, heater or cooler",
                       r"heat[- ]?exchangers?|\bexchangers?\b|(?:pre[- ]?)?heaters?\b|\bcoolers?\b|condensers?|reboilers?|chillers?|vapori[sz]ers?"),
    "boiler": ("Boiler or furnace", r"\bboilers?\b|steam generators?|furnaces?|fired heaters?"),
    "reactor": ("Reactor or fermenter", r"(?:bio)?reactors?\b|fermenters?|digesters?|kettles?"),
    "column": ("Column or tower", r"\b(?:columns?|towers?|strippers?|absorbers?|scrubbers?)\b"),
    "tank": ("Tank", r"\btanks?\b|\bsilos?\b|\bbins?\b|\bhoppers?\b"),
    "vessel": ("Pressure vessel or drum", r"\b(?:pressure )?vessels?\b|\bdrums?\b|\breceivers?\b|flash"),
    "mixer": ("Mixer or agitator", r"\bmixers?\b|agitators?|blenders?|kneaders?"),
    "centrifuge": ("Centrifuge", r"centrifug\w*|decanter centrifuge"),
    "filter": ("Filter", r"\bfilters?\b|filtration"),
    "settler": ("Settler, clarifier or thickener", r"\bsettlers?\b|clarifiers?|thickeners?|sedimentation"),
    "cyclone": ("Cyclone or dust collector", r"cyclones?|dust collectors?|baghouses?|electrostatic precipitators?"),
    "dryer": ("Dryer", r"\bdryers?\b|\bdriers?\b"),
    "evaporator": ("Evaporator", r"evaporators?"),
    "crystalliser": ("Crystalliser", r"crystalli[sz]ers?"),
    "conveyor": ("Conveyor", r"conveyors?|elevators?"),
    "crusher": ("Crusher or mill", r"crushers?|\bmills?\b|grinders?"),
    "screen": ("Screen", r"\bscreens?\b|sieves?"),
    "turbine": ("Turbine or generator", r"turbines?|generators?"),
    "ejector": ("Ejector", r"ejectors?"),
    "direct_contact": ("Direct-contact cooler or quencher",
                       r"quench\w*|spray chambers?|barometric condensers?|direct[- ]contact (?:cooler|condenser)s?"),
    "utility": ("Utility package", r"cooling towers?|refrigeration|air conditioning"),
}
_FAMILY_RE = {k: re.compile(p, re.IGNORECASE) for k, (_, p) in FAMILIES.items()}

# Weak hints only: a prefix never establishes function on its own.
TAG_PREFIXES = {
    "P": "pump", "PD": "pump", "HE": "heat_exchanger", "E": "heat_exchanger", "HX": "heat_exchanger",
    "T": "tank", "TK": "tank", "MT": "tank", "V": "vessel", "D": "vessel", "R": "reactor",
    "EL": "electrolyser", "FT": "filter", "F": "filter", "BL": "compressor", "K": "compressor",
    "CF": "centrifuge", "S": "settler", "DR": "dryer", "IX": "ion_exchange", "RO": "reverse_osmosis",
}

# Catalogue categories whose name alone would be mis-read by the regexes.
CATEGORY_FAMILY = {
    "Packings & adsorbents": "column",
    "Trays": "column",
    "Towers": "column",
    "Dust collectors": "cyclone",
    "Solid-liquid separators": "settler",
    "Mechanically equipped clarifier": "settler",
    "Thickeners / clarifiers": "settler",
    "Water treatment package": None,  # decided by configuration (RO etc.)
    "Wastewater pH adjustment system": "ph_adjustment",
    "Fermenter / fungal bioreactor": "reactor",
    "Electrolysis": "electrolyser",
    "Vaporizers": "heat_exchanger",
    "Fabricated steel / vessel": "vessel",
    "Agitated tanks": "mixer",
    "Motors & generators": "turbine",
    "Utilities": "utility",
}

LIBRARY_RANK = {"openpytea": 0, "garrett": 1, "additional_models": 1, "nottingham": 2}
UNSIZEABLE = {"unresolved", "source_coordinate"}
MATERIAL_WORDS = {"cast", "iron", "carbon", "stainless", "ss", "316", "304", "api610", "monel", "nickel",
                  "hastelloy", "titanium", "glass", "lined", "fiberglass", "concrete", "cs", "alloy", "copper"}
GENERIC_WORDS = {"unit", "system", "equipment", "package", "process", "the", "and", "of", "for", "with",
                 "a", "to", "from", "in", "type", "general", "mild", "steel", "material"}


_SPELLING = ((r"lys(er|ers|is|ed|ing)\b", r"lyz\1"), (r"is(er|ers|ation|ed)\b", r"iz\1"),
             (r"\bcentre\b", "center"), (r"our\b", "or"))


def _norm(token):
    for pattern, repl in _SPELLING:
        token = re.sub(pattern, repl, token)
    return token


def tokens(text):
    """Catalogue-comparable words: plural-stripped and US/UK spelling folded."""
    return {_norm(t) for t in words(text) if t not in GENERIC_WORDS}


def _primary_phrase(text):
    """The naming part of a cell: commentary after ';' or '(' is not the name."""
    return re.split(r"[;(]", str(text or ""), maxsplit=1)[0]


def _configuration_words(text):
    """Words that describe configuration: the function words themselves
    ("pump", "heat exchanger") are dropped because every model in the family
    shares them in substance, if not always in wording."""
    phrase = _primary_phrase(text)
    head = head_family(phrase)
    for _, start, end in sorted((s for s in _spans(phrase) if s[0] == head), key=lambda s: -s[1]):
        phrase = phrase[:start] + " " + phrase[end:]
    return tokens(phrase)


def _spans(text):
    """All (family, start, end) matches in ``text``."""
    out = []
    for family, pattern in _FAMILY_RE.items():
        for m in pattern.finditer(text or ""):
            out.append((family, m.start(), m.end()))
    return out


def head_family(text):
    """The family of a phrase's head noun: the match ending last; longer wins ties."""
    spans = _spans(_primary_phrase(text))
    if not spans:
        return None
    return max(spans, key=lambda s: (s[2], s[2] - s[1]))[0]


def model_family(model):
    raw_category = model.get("category") or ""
    if raw_category in CATEGORY_FAMILY and CATEGORY_FAMILY[raw_category]:
        return CATEGORY_FAMILY[raw_category]
    name = model.get("equipment_name") or ""
    category = name.split(" / ")[0] if " / " in name else name
    if category in CATEGORY_FAMILY and CATEGORY_FAMILY[category]:
        return CATEGORY_FAMILY[category]
    text = " ".join(str(x) for x in (category, raw_category, name, model.get("configuration") or "",
                                     *(_aliases(model))))
    # Category wording first (it names the function); configuration as fallback.
    return head_family(category) or head_family(raw_category) or head_family(text)


def _aliases(model):
    a = model.get("aliases") or []
    if isinstance(a, str):
        a = re.findall(r"'([^']+)'", a) or [a]
    return a


@lru_cache(maxsize=1)
def index():
    """Catalogue grouped by family, plus token document frequencies (built once)."""
    from backend.equipment_costing.registry import list_equipment_models

    categories = {m["id"]: m.get("category") for m in list_equipment_models("all")}
    models = [dict(m, category=categories.get(m["model_id"])) for m in catalogue()
              if m.get("availability") != "disabled"]
    by_family, df = {}, {}
    for m in models:
        m["family"] = model_family(m)
        # Score on the model's own configuration and aliases. Library family
        # labels such as "shell/tube, double-pipe, air" name several types at
        # once and would match every member; the family is matched separately.
        m["tokens"] = frozenset(tokens(" ".join(
            [m.get("configuration") or _own_name(m), *_aliases(m)])))
        m["subtype"] = _subtype(m)
        by_family.setdefault(m["family"], []).append(m)
        for t in m["tokens"]:
            df[t] = df.get(t, 0) + 1
    idf = {t: math.log(1 + len(models) / n) for t, n in df.items()}
    # Tie-break prior: a configuration offered by many sources and variants is a
    # common design choice (e.g. shell-and-tube among exchangers). Data-driven,
    # from the catalogue itself, not an engineering rule.
    prevalence = {}
    for family, members in by_family.items():
        for m in members:
            lead = m["subtype"][1].split(" ")[0]
            prevalence[(family, lead)] = prevalence.get((family, lead), 0) + 1
    return {"models": models, "by_family": by_family, "idf": idf, "prevalence": prevalence}


def _own_name(model):
    name = model.get("equipment_name") or ""
    return name.split(" / ", 1)[1] if " / " in name else name


def _subtype(model):
    """Configuration without material or size qualifiers, e.g. 'centrifugal', 'motor power'."""
    text = (model.get("configuration") or model.get("equipment_name") or "").split("/")[0]
    toks = [_norm(t) for t in words(text)
            if t not in GENERIC_WORDS and t not in MATERIAL_WORDS and not re.match(r"^\d", t)]
    return (model["source"], " ".join(toks[:2]) or model["model_id"])


def _tag_prefix_family(tag):
    letters = re.match(r"[A-Za-z]+", tag or "")
    return TAG_PREFIXES.get(letters.group(0).upper()) if letters else None


def classify(row):
    """Establish an equipment function from the item's own names, then its tag."""
    names = row.get("names") or []
    if names and head_family(names[0]):
        # The item's own (first) name is the most specific statement of function.
        return {"family": head_family(names[0]), "basis": "name", "evidence": names[:1]}
    for source, texts in (("name", names[1:]), ("source_phrase", row.get("source_name_hints") or [])):
        votes = {}
        for text in texts:
            family = head_family(text)
            if family:
                votes[family] = votes.get(family, 0) + 1
        if votes:
            ranked = sorted(votes.items(), key=lambda kv: -kv[1])
            if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
                return {"family": None, "basis": source, "conflict": [k for k, _ in ranked]}
            return {"family": ranked[0][0], "basis": source, "evidence": texts}
    prefix = _tag_prefix_family(row.get("tag"))
    if prefix:
        return {"family": prefix, "basis": "tag_prefix", "evidence": [row.get("tag")]}
    return {"family": None, "basis": None}


def _score(model, query_tokens, idf):
    overlap = model["tokens"] & query_tokens
    return round(sum(idf.get(t, 0) for t in overlap), 3), sorted(overlap)


def match_row(row, max_options=6, margin=1.0, offer=None, current=None):
    idx = index()
    cls = classify(row)
    family = cls.get("family")
    base = {"equipment_key": row.get("equipment_key"), "tag": row.get("tag"), "family": family,
            "family_label": FAMILIES[family][0] if family else None, "family_basis": cls.get("basis"),
            "method": VERSION}
    if not family:
        return {**base, "status": "unmatched", "options": [], "selected_model_id": None,
                "reason": ("Names point to different functions: " + ", ".join(cls["conflict"])) if cls.get("conflict")
                else "No equipment function recognised in the item's names or tag."}
    query = set().union(*[_configuration_words(t) for t in
                           [*(row.get("names") or []), *(row.get("source_name_hints") or [])]] or [set()])
    offer = offer or {"quantities": set(), "supported_parameters": set()}
    scored = []
    for m in idx["by_family"].get(family, []):
        s, overlap = _score(m, query, idx["idf"])
        sizing = sizing_path(m, family, offer)
        scored.append({
            # Sizing is a gate, not a score: "can the study size it" ranks above
            # "cannot", but fewer assumptions does not mean a better fit (crude
            # throughput coordinates would otherwise beat proper design models).
            "key": (-s, min(sizing["tier"], 1) if sizing["tier"] <= 1 else sizing["tier"] - 1,
                    -idx["prevalence"].get((family, m["subtype"][1].split(" ")[0]), 0),
                    LIBRARY_RANK.get(m["source"], 3), str(m.get("availability", "")).endswith("provisional"),
                    m["model_id"]),
            "score": s, "overlap": overlap, "model": m, "sizing": sizing})
    scored.sort(key=lambda x: x["key"])
    seen, diverse = set(), []
    in_use = next((x for x in scored if x["model"]["model_id"] == current), None)
    for x in scored:  # one representative per configuration subtype, across libraries
        if x["model"]["subtype"][1] not in seen:
            seen.add(x["model"]["subtype"][1])
            # The model the study already uses represents its own group.
            same = in_use and in_use["model"]["subtype"][1] == x["model"]["subtype"][1]
            diverse.append(in_use if same else x)
    if in_use and in_use not in diverse[:max_options]:
        diverse = [in_use] + [x for x in diverse if x is not in_use]
    options = [{"model_id": x["model"]["model_id"], "equipment_name": x["model"].get("equipment_name"),
                "configuration": x["model"].get("configuration"), "source": x["model"]["source"],
                "score": x["score"], "matched_words": x["overlap"], "subtype": x["model"]["subtype"],
                "size_inputs": x["model"].get("size_inputs"), "sizing": x["sizing"],
                "variants": sum(1 for y in scored if y["model"]["subtype"][1] == x["model"]["subtype"][1]),
                "current": x is in_use}
               for x in diverse[:max_options]]
    if not options:
        return {**base, "status": "unmatched", "options": [], "selected_model_id": None,
                "reason": f"No catalogue model for {FAMILIES[family][0].lower()}."}
    top = diverse[0]["score"]
    runner = diverse[1]["score"] if len(diverse) > 1 else -math.inf
    clear = top > 0 and top - runner >= margin
    label = FAMILIES[family][0].lower()
    if cls["basis"] == "tag_prefix":
        status, reason = "prefix_only", f"Only the tag prefix suggests {label}; confirm."
    elif clear or len(diverse) == 1:
        status, reason = "auto", (f"Named as {label}; the only catalogue model for this function."
                                  if len(diverse) == 1 else
                                  f"Named as {label}; the words \"{' '.join(options[0]['matched_words'])}\" "
                                  "single out this configuration.")
    else:
        sizeable = sum(1 for o in options if o["sizing"]["tier"] <= 1)
        status, reason = "choose", (f"Named as {label}; {len(diverse)} configurations fit and the source does not "
                                    f"state which. {sizeable} of the {len(options)} shown can be sized from "
                                    "the linked stream data.")
    if current and status == "auto" and options[0]["model_id"] != current:
        # Never swap a model the study already uses by default; offer it as a choice.
        status = "choose"
        reason = (f"Named as {label}. The model already in use is kept preselected"
                  if in_use else f"Named as {label}, but the model in use is not a {label} model; check it")
        reason += f". The name points most closely to: {options[0]['configuration']}."
    return {**base, "status": status, "reason": reason, "options": options,
            "selected_model_id": options[0]["model_id"] if status == "auto" else None,
            "current_model_id": current, "current_in_family": bool(in_use),
            "suggested_model_id": options[0]["model_id"], "available_data": {
                "quantities": sorted(offer["quantities"]),
                "source_parameters": sorted(offer["supported_parameters"]),
                "design_basis_cells": offer.get("design_basis_evidence", {})}}


def match_register(report, design_basis=(), current_models=None):
    """Deterministic matches for every registered equipment item.

    ``design_basis`` is the output of ``ingestion.design_basis.extract`` on the
    workbook's source cells; linked rows count as source data for sizing.
    """
    rows = equipment_register(report)
    entities = {e.get("key"): e for e in report.get("entities", [])}
    contextual_descriptions(report)  # validates links; context not used for selection
    for row in rows:
        e = entities.get(row["equipment_key"], {})
        row["raw_names"] = list(dict.fromkeys(
            str(v["original_value"]) for v in e.get("values", [])
            if v.get("property") in {"name", "type", "description"} and v.get("original_value")))
        row["source_name_hints"] = source_name_hints(row)
        row["family"] = classify(row).get("family")
    links = link_design_basis(design_basis, [{"key": r["equipment_key"], "tag": r["tag"], "family": r["family"]}
                                             for r in rows], head_family)
    out = []
    for row in rows:
        linked = links["linked"].get(row["equipment_key"], [])
        result = match_row(row, offer=sizing_available(report, row["equipment_key"], linked),
                           current=(current_models or {}).get(row["equipment_key"]))
        result["design_basis"] = linked
        out.append(result)
    return {"version": VERSION, "matches": out, "design_basis_unlinked": links["unlinked"],
            "counts": {s: sum(1 for m in out if m["status"] == s)
                       for s in ("auto", "choose", "prefix_only", "unmatched")}}
