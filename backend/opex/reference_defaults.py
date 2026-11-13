"""Deterministic OPEX default proposals from the reference library (no AI, no network).

Fills only what is missing; never replaces a user-entered, user-selected or
AI-proposed value. Every proposed value records its owner ("reference_default")
and its source, page and range, and is marked for review.

* Factor categories with a base (Garrett Table 4-4): the library typical value,
  or the midpoint of the printed range when no typical value is given.
* Utilities: from values the study already holds — an equipment power reading,
  or a workbook specific energy (e.g. kWh per kg of a product) × that product
  stream's mass flow — × operating hours × an electricity tariff. A missing
  tariff stays an explicit question; the quantity is still shown.
* Raw materials: M&E feed streams × a price; a missing price stays a question
  with the quantity shown.
* Operating labour: only from a page-checked correlation row; otherwise nothing
  is proposed and labour stays a question.

All arithmetic stays in Python; this module only writes the inputs.
"""

import copy
import re
from datetime import date
from decimal import Decimal

from .reference_library import get_correlation, get_ranges
from .indexes.garrett.model import CATEGORIES

OWNER = "reference_default"
STATUS = "proposed — needs review"
UTILITY_WORDS = re.compile(r"cooling[- ]water|chilled water|steam|condensate|instrument air|plant air|nitrogen blanket", re.I)
FORMULA_NAMES = {"h2": "hydrogen", "o2": "oxygen", "co2": "carbon dioxide", "nh3": "ammonia", "h2o": "water", "ch4": "methane"}


def _text(entity, props=("name", "description", "type")):
    return " ".join(str(v.get("original_value") or "") for v in entity.get("values", []) if v.get("property") in props)


def _ends(report):
    """{stream_key: {"source": equipment_key|None, "destination": equipment_key|None}}."""
    ends = {}
    for c in report.get("connections", []):
        if c.get("role") in ("source", "destination"):
            slot = ends.setdefault(c["stream_key"], {"source": None, "destination": None})
            slot[c["role"]] = slot[c["role"]] or c.get("equipment_key")
    return ends


def _has(entity, prop):
    return any(v.get("property") == prop and v.get("normalized_value") is not None and not v.get("component")
               for v in entity.get("values", []))


def factor_defaults(config):
    """Missing garrett_factors choices -> library typical or range midpoint."""
    factors = copy.deepcopy(config.get("garrett_factors") or {})
    proposals = []
    for c in CATEGORIES:
        if not c.base or c.id in factors:
            continue
        rows = get_ranges(c.id, "garrett")
        if not rows:
            continue
        row = rows[0]
        low, high = Decimal(str(row["low"])), Decimal(str(row["high"]))
        if row.get("typical") is not None:
            value, rule = Decimal(str(row["typical"])), "typical"
        else:
            value, rule = (low + high) / 2, "midpoint"
        value = min(max(value, low), high)  # never outside the printed range
        factors[c.id] = {
            "fraction": float(value),
            "rationale": f"Reference default: {row['source']} {row['page']}, {rule} of {low}–{high}",
            "origin": OWNER, "status": STATUS, "tier": "assumption",
            "source": row["source"], "page": row["page"], "low": str(low), "high": str(high), "value_basis": rule,
        }
        proposals.append({"kind": "factor", "id": c.id, "value": float(value), "rule": rule,
                          "range": [str(low), str(high)], "source": row["source"], "page": row["page"]})
    return factors, proposals


def _tariff(workbook_params):
    """An electricity tariff the workbook states, as (value per kWh, cell) or None."""
    for hit in workbook_params or []:
        label = str(hit.get("label") or "")
        unit = str(hit.get("unit") or "").lower().replace(" ", "")
        if re.search(r"electric|power", label, re.I) and re.search(r"price|tariff|cost", label, re.I) \
                and isinstance(hit.get("value"), (int, float)) and hit["value"] > 0:
            if "/mwh" in unit:
                return hit["value"] / 1000, hit["id"]
            if "/kwh" in unit:
                return hit["value"], hit["id"]
    return None


def utility_defaults(report, design_basis_rows, workbook_params):
    """Electricity items from equipment power readings or workbook specific energy."""
    items, questions = [], []
    tariff = _tariff(workbook_params)
    entities = {e["key"]: e for e in report.get("entities", [])}
    ends = _ends(report)

    def item(ident, equipment_key, name, method, extra, basis):
        price = tariff[0] if tariff else None
        row = {"id": ident, "equipment_key": equipment_key, "name": name, "utility": "electricity",
               "method": method, "behavior": "variable", "load_fraction": 1, "efficiency": 1,
               "tariff_per_kwh": price, "power_kw": None, "power_density_w_m3": None, "pressure_difference_bar": None,
               "volume_m3": None, "rationale": basis + (f"; tariff from {tariff[1]}" if tariff else "; electricity tariff needed"),
               "uncertainty": "Reference default from study data; tariff and load to be confirmed.",
               "origin": OWNER, "status": STATUS, **extra}
        items.append(row)
        if price is None:
            questions.append({"id": ident, "question": f"Electricity tariff ({name}): enter a price per kWh."})

    # 1. Equipment with its own power reading in the workbook.
    for e in report.get("entities", []):
        if e.get("kind") == "equipment" and _has(e, "power"):
            item("ref-power-" + str(e["identifier"]).lower(), e["key"], f"{e['identifier']} electricity",
                 "measured_electrical", {"source_key": e["key"]}, f"Workbook power reading for {e['identifier']}")
    # 2. Workbook specific energy (kWh per kg of a named product) × that product's stream.
    for row in design_basis_rows or []:
        unit = str(row.get("unit") or "")
        m = re.match(r"\s*kWh\s*/\s*kg\s*(\S+)?", unit, re.I)
        if not m or not isinstance(row.get("value"), (int, float)) or row["value"] <= 0:
            continue
        species = (m.group(1) or "").strip()
        pattern = re.compile(r"\b" + re.escape(species) + r"\b" + (f"|{FORMULA_NAMES[species.lower()]}" if species.lower() in FORMULA_NAMES else ""), re.I) if species else None
        candidates = [e for e in report.get("entities", []) if e.get("kind") == "material" and pattern and pattern.search(_text(e))
                      and (ends.get(e["key"]) or {}).get("source") and _has(e, "mass_flow")]
        if len(candidates) != 1:
            questions.append({"id": "ref-specific-energy", "question":
                              f"{row['parameter']} ({row['id']}): choose the product stream it applies to."})
            continue
        stream = candidates[0]
        equipment = entities.get(ends[stream["key"]]["source"]) or {}
        item("ref-specific-energy-" + str(equipment.get("identifier", "unit")).lower(), equipment.get("key"),
             f"{equipment.get('identifier', 'Unit')} electricity", "specific_energy",
             {"source_key": stream["key"], "specific_kwh_per_kg": row["value"]},
             f"Workbook {row['parameter']} {row['value']} {unit} ({row['id']}) × stream {stream['identifier']} mass flow")
    return items, questions


def material_defaults(report):
    """Feed streams (destination equipment, no source equipment) as quantity-only items."""
    items, questions = [], []
    ends = _ends(report)
    for e in report.get("entities", []):
        if e.get("kind") != "material" or not _has(e, "mass_flow"):
            continue
        end = ends.get(e["key"]) or {}
        name = _text(e, ("name", "description")) or e.get("identifier")
        if end.get("source") or not end.get("destination") or UTILITY_WORDS.search(name):
            continue
        ident = "ref-feed-" + str(e["identifier"]).lower()
        items.append({"id": ident, "name": name[:80], "category": "raw_materials", "stream_key": e["key"],
                      "property": "mass_flow", "component": None, "quantity_unit": "kg", "unit_price": None,
                      "annual_quantity_assumption": None,
                      "rationale": f"Feed stream {e['identifier']} enters the plant (no source equipment in the M&E); price needed",
                      "uncertainty": "Quantity from the M&E balance; price to be entered.",
                      "origin": OWNER, "status": STATUS})
        questions.append({"id": ident, "question": f"Price per kg for feed {e['identifier']} ({name[:60]})."})
    return items, questions


def propose(config, report, *, design_basis_rows=(), workbook_params=(), price_basis=None):
    """Return (config with missing OPEX inputs proposed, summary). Never overwrites."""
    config = copy.deepcopy(config or {})
    owners = dict(config.get("value_owners") or {})
    summary = {"factors": [], "utilities": [], "materials": [], "questions": [], "labour": None}
    if not config.get("price_basis") and price_basis:
        config["price_basis"] = dict(price_basis)
        owners["price_basis"] = OWNER
    config.setdefault("assumption_date", date.today().isoformat())
    config.setdefault("methodology", "garrett")
    factors, proposals = factor_defaults(config)
    config["garrett_factors"] = factors
    summary["factors"] = proposals
    owners.update({f"garrett_factors.{p['id']}": OWNER for p in proposals})
    if not config.get("energy"):
        items, questions = utility_defaults(report, design_basis_rows, workbook_params)
        if items:
            config["energy"] = items
            owners.update({f"energy.{i['id']}": OWNER for i in items})
        summary["utilities"], summary["questions"] = items, summary["questions"] + questions
    if not config.get("materials"):
        items, questions = material_defaults(report)
        if items:
            config["materials"] = items
            owners.update({f"materials.{i['id']}": OWNER for i in items})
        summary["materials"], summary["questions"] = items, summary["questions"] + questions
    if not config.get("labour"):
        correlation = get_correlation("operating_labor", "turton")
        summary["labour"] = ("correlation available but not yet implemented" if correlation else
                             "No page-checked staffing correlation in the reference library; enter operators and salary.")
        if not correlation:
            summary["questions"].append({"id": "operating_labor", "question":
                                         "Operating labour: enter operators (FTE) and salary. No page-checked staffing rule is loaded."})
    config["value_owners"] = owners
    config["reference_defaults"] = {"version": "opex-reference-defaults-1", "status": STATUS,
                                    "questions": summary["questions"]}
    return config, summary


def for_study(config, report, source_cells, capex_result=None, cost_translation=None):
    """propose() with the study's own design basis, workbook values and cost basis."""
    from backend.equipment_costing.unit_conversion.bridges.workbook_parameters import scan
    from backend.ingestion.design_basis import extract

    capex_result = capex_result or {}
    price_basis = None
    if capex_result.get("currency") and capex_result.get("period"):
        price_basis = {"currency": capex_result["currency"], "price_period": capex_result["period"]}
    elif (cost_translation or {}).get("target_period"):
        price_basis = {"currency": "USD", "price_period": cost_translation["target_period"]}
    return propose(config, report, design_basis_rows=extract(source_cells or []),
                   workbook_params=scan(source_cells or []), price_basis=price_basis)
