"""Founder rule (11 Nov 2026): prefer OpenPyTEA over Garrett for the same equipment.

When the matcher selects a Garrett model but also lists a usable OpenPyTEA model
of the same equipment family, the OpenPyTEA model is selected and the Garrett
model stays as an alternative. Python enforces this so it does not depend on the
language model following the instruction. A user-confirmed selection is never
changed here: confirmed rows are protected later by retain_approved.
"""

# Garrett equipment family -> OpenPyTEA categories describing the same function.
# Families with no OpenPyTEA equivalent (buildings, insulation, flares, ducts,
# chimneys, incinerators, ...) are absent, so Garrett remains the only choice.
FAMILY_TO_OPENPYTEA = {
    "Activated carbon adsorbers": {"Adsorption & membrane separation", "Packings & adsorbents"},
    "Agitators": {"Agitators, blenders, & mixers"},
    "Agitated tanks": {"Reactors", "Agitators, blenders, & mixers"},
    "Blenders": {"Agitators, blenders, & mixers"},
    "Blowers": {"Compressors, fans, & blowers"},
    "Fans": {"Compressors, fans, & blowers"},
    "Compressors, medium/low pressure": {"Compressors, fans, & blowers"},
    "Compressors, high-capacity/pressure": {"Compressors, fans, & blowers"},
    "Boilers": {"Boilers, heaters, & furnaces"},
    "Waste-heat boilers": {"Boilers, heaters, & furnaces"},
    "Furnaces": {"Boilers, heaters, & furnaces"},
    "Centrifuges": {"Centrifuges"},
    "Classifier, rake or spiral": {"Solid-liquid separators", "Screens"},
    "Columns, distillation/absorption": {"Towers", "Pressure vessels"},
    "Column trays": {"Trays"},
    "Column packing": {"Packings & adsorbents"},
    "Conveyors": {"Conveyors", "Solids-handling systems"},
    "Coolers / quenchers": {"Heat exchangers"},
    "Cooling tower": {"Utilities"},
    "Crystallizers": {"Crystallizers"},
    "Dryers": {"Dryers"},
    "Dust collectors": {"Dust collectors"},
    "Evaporators": {"Evaporators"},
    "Filters": {"Filters"},
    "Electric power generators": {"Motors & generators", "Turbines"},
    "Heat exchangers — shell/tube, double-pipe, air": {"Heat exchangers"},
    "Heat exchangers — spiral / plate frame": {"Heat exchangers"},
    "Crushers / mills": {"Crushers"},
    "Mills — grinding / jet / rubbish": {"Crushers"},
    "Motor drives": {"Motors & generators"},
    "Pipe and pipelines": {"Piping"},
    "Presses, roll / screw": {"Expression", "Size enlargement"},
    "Centrifugal pumps": {"Pumps"},
    "Miscellaneous pumps": {"Pumps"},
    "Pressure vessels": {"Pressure vessels"},
    "Reactors": {"Reactors"},
    "Refrigeration": {"Utilities"},
    "Vibrating screens": {"Screens"},
    "Size enlargement equipment": {"Size enlargement"},
    "Tanks": {"Tanks", "Pressure vessels"},
    "Small tanks — stainless steel": {"Tanks"},
    "Thickeners / clarifiers": {"Solid-liquid separators"},
    "Vacuum equipment": {"Ejectors", "Compressors, fans, & blowers"},
}


def user_selected_model(row):
    """The model a person chose for this row, or None.

    The equipment editor records {"origin": "user", "curve_id": ...} when a user
    picks a model. It counts only while the row still uses that model, so a later
    user change or clear is respected.
    """
    selection = (row or {}).get("model_selection") or {}
    if selection.get("origin") == "user" and selection.get("curve_id") and selection.get("curve_id") == row.get("curve_id"):
        return selection["curve_id"]
    return None


def is_garrett(model):
    return model.get("source") in (None, "garrett")


def openpytea_category(model):
    return str(model.get("equipment_name", "")).split(" / ")[0].strip()


def usable(model):
    # OpenPyTEA rows are "available_provisional" (computable; some published
    # bounds still need acceptance). Only disabled models or unresolved size
    # coordinates are excluded.
    return model.get("availability", "available") in {"available", "available_provisional"} and not model.get("coordinate_issues")


def _words(model):
    import re

    # Configuration only: Garrett family names list several types at once
    # (for example "shell/tube, double-pipe, air"), which would blur the ranking.
    text = str(model.get("configuration", "")).replace("and", " ")
    return {w for w in re.findall(r"[a-z]{4,}", text.lower())}


def catalogue_family(garrett_model, model_by_id, limit=8):
    """Computable OpenPyTEA models of the Garrett model's family, closest first."""
    families = FAMILY_TO_OPENPYTEA.get(garrett_model.get("equipment_name"), set())
    words = _words(garrett_model)
    found = [
        m for m in model_by_id.values()
        if m.get("source") == "openpytea" and openpytea_category(m) in families and usable(m)
    ]
    found.sort(key=lambda m: (-len(words & _words(m)), m["model_id"]))
    return [m["model_id"] for m in found[:limit]]


def openpytea_first(ids, model_by_id):
    """Stable reorder: OpenPyTEA candidates first, so sizing tries them first."""
    return sorted(ids, key=lambda i: model_by_id[i].get("source") != "openpytea")


def apply_preference(decision, model_by_id):
    """Return (decision, audit). audit is None when the rule did not apply.

    Order: a usable OpenPyTEA model the AI listed; otherwise usable OpenPyTEA
    models of the same family from the catalogue; otherwise keep Garrett.
    """
    decision = dict(decision)
    decision["candidate_model_ids"] = openpytea_first(decision.get("candidate_model_ids", []), model_by_id)
    selected = model_by_id.get(decision.get("selected_model_id"))
    if not selected or not is_garrett(selected):
        return decision, None
    families = FAMILY_TO_OPENPYTEA.get(selected.get("equipment_name"), set())
    listed = [
        i for i in decision["candidate_model_ids"]
        if model_by_id[i].get("source") == "openpytea" and openpytea_category(model_by_id[i]) in families
    ]
    computable = [i for i in listed if usable(model_by_id[i])]
    if computable:
        decision["selected_model_id"] = computable[0]
        return decision, {
            "rule": "prefer_openpytea_over_garrett",
            "applied": True,
            "replaced": selected["model_id"],
            "selected": computable[0],
            "reason": "Founder rule: OpenPyTEA is preferred when it covers the same equipment family; the Garrett model stays as an alternative.",
        }
    # The AI listed no usable OpenPyTEA option. Look in the catalogue itself, so
    # "OpenPyTEA first" does not depend on what the AI happened to list.
    found = catalogue_family(selected, model_by_id)
    if not found:
        if listed:
            return decision, {
                "rule": "prefer_openpytea_over_garrett",
                "applied": False,
                "kept": selected["model_id"],
                "reason": "Same-family OpenPyTEA models exist but none can be sized: " + ", ".join(listed),
            }
        return decision, None
    decision["candidate_model_ids"] = found + [i for i in decision["candidate_model_ids"] if i not in found]
    decision["selected_model_id"] = None
    return decision, {
        "rule": "prefer_openpytea_over_garrett",
        "applied": True,
        "replaced": selected["model_id"],
        "selected": None,
        "added_from_catalogue": found,
        "reason": "Founder rule: OpenPyTEA models of the same family exist in the catalogue; the configuration is chosen at sizing, OpenPyTEA first, with the Garrett model kept as the fallback.",
    }
