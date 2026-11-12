"""Can FlowValue size this model from the study's own data? (deterministic, no AI)

For each candidate model this finds the cheapest route from the measurements on
the equipment and its linked streams to the model's size input, using only the
allowlisted bridge recipes in ``unit_conversion/bridges/service.py`` and the
allowlisted source derivations in ``bridges/derivations.py``. It does not size
anything: it reports which route exists and which parameters would still be
assumptions. The matcher uses this to rank equally plausible models, so models
the study can actually size come first.

Tiers (lower is better):
  0 direct       the source already holds the required quantity
  1 derived      an allowlisted recipe reaches it; remaining parameters listed
  2 needs_input  no route from the available data; a dimension or user input is needed
  3 unsizeable   the model's size coordinate is unresolved in the catalogue
"""

import re

from backend.equipment_costing.unit_conversion.bridges.service import RECIPES

# Measurement property -> physical quantity it provides directly.
PROPERTY_QUANTITY = {
    "mass_flow": "mass_flow",
    "volume_flow": "volume_flow",
    "power": "power",
    "electrical_power": "power",
    "heat_duty": "heat_duty",
    "duty": "heat_duty",
    "volume": "volume",
    "area": "area",
}

# Recipe -> (observation it starts from, equipment families it applies to).
# ``None`` families means any function (pure physics such as mass -> volume flow).
RECIPE_USE = {
    "liquid_flow": ("mass_flow", None),
    "gas_flow": ("mass_flow", None),
    "standard_gas_flow": ("mass_flow", None),
    "electrical_to_shaft_power": ("power", None),
    "shaft_to_electrical_power": ("power", None),
    "vessel_volume": ("mass_flow", {"tank", "vessel", "reactor", "mixer", "settler", "ion_exchange"}),
    "vessel_productivity": (None, {"reactor"}),
    "mixing_power": ("mass_flow", {"mixer", "reactor"}),
    "filter_area": ("mass_flow", {"filter"}),
    "clarifier_area": ("mass_flow", {"settler"}),
    "pump_power": ("mass_flow", {"pump"}),
    "pump_hydraulic_power": ("mass_flow", {"pump"}),
    "pump_coordinate": ("mass_flow", {"pump"}),
    "pump_flow_head": ("mass_flow", {"pump"}),
    "gas_compression": ("mass_flow", {"compressor"}),
    "dryer_volume": ("mass_flow", {"dryer"}),
    "dryer_evaporation": ("component_mass_flow", {"dryer", "evaporator"}),
    "exchanger_area": ("heat_duty", {"heat_exchanger", "evaporator", "boiler"}),
}
UNSIZEABLE = {"unresolved", "source_coordinate", None, ""}
TIER = {"direct": 0, "derived": 1, "needs_input": 2, "unsizeable": 3}


# --- Design-basis values ----------------------------------------------------
# Workbook parameter tables (``ingestion/design_basis.py``) state values such as
# "Thermal duty to cooling water: 500 kW" without naming an equipment tag.
# A row is linked to an item only by these deterministic rules, in order:
#   1. the row names the item's tag;
#   2. the row names the item's function (e.g. "Electrolyser pressure");
#   3. the row states a role that only one function can hold (heat duty,
#      coolant temperatures -> heat exchange) and exactly one registered item
#      has that function.
# Anything else stays unlinked and is reported, never guessed. Residual and
# closure checks and zero values are ignored.
_ROLE_WORDS = {"heat_exchanger": re.compile(
    r"\bduty\b|heat (?:removed|rejected|load|transfer)|coolant|cooling[- ]water|cooling stream", re.I)}
_IGNORE = re.compile(r"residual|closure|\bcheck\b|\berror\b|balance difference", re.I)
_UNIT_KIND = (
    (re.compile(r"^(?:k|m|g)?w$", re.I), "power"),
    (re.compile(r"^(?:kg|t|tonne|lb)/(?:h|hr|d|day|s)$", re.I), "mass_flow"),
    (re.compile(r"^(?:m3|m³|l|gal)/(?:h|hr|d|day|s|min)$", re.I), "volume_flow"),
    (re.compile(r"^(?:m3|m³)$", re.I), "volume"),
    (re.compile(r"^(?:m2|m²|ft2)$", re.I), "area"),
    (re.compile(r"^(?:°c|degc|c|k|°f)$", re.I), "temperature"),
    (re.compile(r"^(?:bar|barg|bara|kpa|mpa|pa|psi|psig|psia|atm)$", re.I), "pressure"),
)
_DUTY_WORDS = re.compile(r"duty|heat|thermal|cooling|heating|absorbed|enthalpy", re.I)


_DELTA = re.compile(r"\brise\b|\bdifference\b|\bdelta\b|\bapproach\b|\bΔ|\bdrop\b", re.I)


def _names_tag(text, tag):
    """Whole-word tag match, tolerant of separators (``E-12`` = ``E 12`` = ``E12``)."""
    chars = [c for c in str(tag or "").casefold() if c.isalnum()]
    if len(chars) < 2:
        return False
    pattern = r"(?<![a-z0-9])" + r"[\s/\-]*".join(re.escape(c) for c in chars) + r"(?![a-z0-9])"
    return re.search(pattern, str(text).casefold()) is not None


def design_basis_quantity(row):
    """Physical quantity a design-basis row states, from its unit and wording."""
    unit = re.sub(r"\s+", "", str(row.get("unit") or ""))
    for pattern, kind in _UNIT_KIND:
        if pattern.match(unit):
            text = str(row.get("parameter") or "")
            if kind == "power" and _DUTY_WORDS.search(text):
                return "heat_duty"
            if kind in {"temperature", "pressure"} and _DELTA.search(text):
                return None  # a difference, not a state; not used for sizing here
            return kind
    return None


def link_design_basis(rows, items, head_family):
    """Map design-basis rows to registered items. ``items`` = [{key, tag, family}]."""
    by_family = {}
    for item in items:
        by_family.setdefault(item.get("family"), []).append(item)
    linked, unlinked = {}, []
    for row in rows or []:
        quantity = design_basis_quantity(row)
        value = row.get("value")
        text = str(row.get("parameter") or "")
        if (quantity is None or _IGNORE.search(text) or isinstance(value, bool)
                or not isinstance(value, (int, float)) or value == 0):
            continue
        target, rule = None, None
        tagged = [i for i in items if _names_tag(text, i.get("tag"))]
        if len(tagged) == 1:
            target, rule = tagged, "names the tag"
        else:
            family = head_family(text)
            if family and len(by_family.get(family, [])) == 1:
                target, rule = by_family[family], "names the function"
            else:
                for role, pattern in _ROLE_WORDS.items():
                    if pattern.search(text) and len(by_family.get(role, [])) == 1:
                        target, rule = by_family[role], "only item with this role"
                        break
        entry = {"id": row.get("id"), "parameter": text, "value": value, "unit": row.get("unit"),
                 "quantity": quantity}
        if target:
            linked.setdefault(target[0]["key"], []).append({**entry, "link": rule})
        else:
            unlinked.append(entry)
    return {"linked": linked, "unlinked": unlinked}


def available(report, equipment_key, design_basis=()):
    """What the source offers for this item: quantities and derivable parameters.

    ``design_basis`` holds the workbook parameter rows linked to this item.
    """
    entities = {e.get("key"): e for e in report.get("entities", [])}
    item = entities.get(equipment_key) or {}
    linked = [item] + [entities[k] for k in item.get("stream_keys", []) if k in entities]
    props, pressures, temperatures, enthalpy_streams = set(), set(), set(), 0
    for entity in linked:
        has_enthalpy = False
        for v in entity.get("values", []):
            if v.get("status") == "unresolved":
                continue
            value = v.get("normalized_value", v.get("original_value"))
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            prop = v.get("property")
            if v.get("component"):
                props.add("component_" + str(prop) if not str(prop).startswith("component_") else prop)
                continue
            props.add(prop)
            if prop == "pressure":
                pressures.add(round(float(value), 6))
            elif prop == "temperature":
                temperatures.add(round(float(value), 6))
            elif prop in {"enthalpy_flow", "enthalpy"}:
                has_enthalpy = True
        enthalpy_streams += has_enthalpy
    evidence = {}
    for row in design_basis or ():
        q = row["quantity"]
        if q == "temperature":
            temperatures.add(round(float(row["value"]), 6))
        elif q == "pressure":
            pressures.add(round(float(row["value"]), 6))
        else:
            props.add({"heat_duty": "heat_duty", "power": "power"}.get(q, q))
        evidence.setdefault(q, []).append(row["id"])
    quantities = {PROPERTY_QUANTITY[p] for p in props if p in PROPERTY_QUANTITY}
    if enthalpy_streams >= 2:
        quantities.add("heat_duty")  # duty as a source enthalpy difference
    if "component_mass_flow" in props:
        quantities.add("component_mass_flow")
    supported = set()  # parameters an allowlisted derivation can take from the source
    if {"mass_flow", "volume_flow"} <= props:
        supported.add("density_kg_m3")
    if {"mass_flow", "molar_flow"} <= props or "mole_fraction" in props:
        supported.add("molecular_weight_kg_kmol")
    if temperatures:
        supported |= {"temperature_k"}
    if pressures:
        supported |= {"absolute_pressure_bar"}
    if len(pressures) >= 2:
        supported |= {"differential_pressure_bar", "discharge_pressure_bar"}
    if len(temperatures) >= 4:
        supported.add("lmtd_k")
    return {"quantities": quantities, "supported_parameters": supported, "design_basis_evidence": evidence}


def path(model, family, offer):
    """Best sizing route for one model given what the source offers."""
    size = (model.get("size_inputs") or [{}])[0]
    quantity = size.get("quantity")
    if quantity in UNSIZEABLE:
        return {"status": "unsizeable", "tier": 3, "quantity": quantity,
                "note": "The catalogue does not resolve this model's size coordinate."}
    cited = offer.get("design_basis_evidence") or {}
    if quantity in offer["quantities"]:
        return {"status": "direct", "tier": 0, "quantity": quantity, "recipe": "direct", "assumptions": [],
                "design_basis_cells": cited.get(quantity, [])}
    best = None
    for recipe, (start, families) in RECIPE_USE.items():
        label, output, parameters, _ = RECIPES[recipe]
        if output != quantity or (families is not None and family not in families):
            continue
        if start is not None and start not in offer["quantities"]:
            continue
        assumptions = [p for p in parameters if p not in offer["supported_parameters"]]
        candidate = {"status": "derived", "tier": 1, "quantity": quantity, "recipe": recipe,
                     "recipe_label": label, "from": start, "assumptions": assumptions,
                     "source_supported": [p for p in parameters if p in offer["supported_parameters"]],
                     "design_basis_cells": cited.get(start, [])}
        if best is None or len(assumptions) < len(best["assumptions"]):
            best = candidate
    if best:
        return best
    return {"status": "needs_input", "tier": 2, "quantity": quantity,
            "note": f"No route from the linked data to {quantity}; a dimension or user input is needed."}
