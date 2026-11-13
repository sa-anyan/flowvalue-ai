"""Find sizing parameters the workbook already states, before the AI assumes them.

Deterministic, no AI. Scans the parsed workbook cells for labelled values such
as "Residence time | 2 | h", "Pump efficiency 0.75" or "U = 850 W/m2K": a text
label naming a sizing parameter, followed on the same row by a number and,
where present, a unit. Each hit keeps its worksheet!cell so it can be cited.

Hits are scoped to equipment by the same deterministic rules as design-basis
linking: the label (or its row) names the tag; or names the equipment
function; or the value is workbook-wide. They are handed to the sizing AI as
workbook statements to use and cite before proposing an assumption; Python
still validates units and performs all arithmetic. A hit is a candidate, not a
verified design value: a label match can be wrong, which is why it is cited.
"""

import re

# Sizing parameter -> label pattern. Parameter names are the bridge contract
# names in ``bridges/service.py`` PARAMETERS.
PATTERNS = {
    "residence_time_h": r"residence time|retention time|hold[- ]?up time|hydraulic retention|\bHRT\b|detention time|storage time|days? of storage|(?:fermentation|reaction|batch|cycle|liquefaction) time|time for (?:fermentation|reaction|liquefaction|digestion)|total cycle time",
    "equipment_volume_m3": r"volume of (?:1|one|each|a single)?\s*(?:tank|vessel|reactor|fermenter|bioreactor)|(?:tank|vessel|reactor|fermenter) volume",
    "gas_residence_time_s": r"gas residence time|residence time",
    "working_fraction": r"working (?:volume|fraction|capacity)|fill(?:ing)? (?:fraction|level|ratio)|liquid level|freeboard",
    "efficiency": r"(?<!motor )efficiency|\beta\b",
    "motor_efficiency": r"motor efficiency",
    "differential_pressure_bar": r"differential pressure|pressure (?:rise|increase|drop|difference)|delta[- ]?p\b|Δ ?p\b|discharge pressure|pump head|total head",
    "head_m": r"\bhead\b",
    "density_kg_m3": r"density",
    "overall_u_w_m2_k": r"overall (?:heat[- ]transfer )?coefficient|heat[- ]transfer coefficient|\bU[- ]?value\b|^\s*U\s*(?:\(|=|$)",
    "lmtd_k": r"\bLMTD\b|log[- ]?mean temperature",
    "hydraulic_loading_m_h": r"hydraulic loading|surface (?:overflow|loading) rate|overflow rate|filtration rate|filter loading",
    "molecular_weight_kg_kmol": r"molecular weight|molar mass|\bMW\b",
    "heat_capacity_ratio": r"heat capacity ratio|cp\s*/\s*cv|\bgamma\b|isentropic exponent",
    "latent_heat_kj_kg": r"latent heat|heat of vapou?ri[sz]ation|enthalpy of vapou?ri[sz]ation",
    "specific_heat_kj_kg_k": r"specific heat|heat capacity|\bcp\b",
    "power_density_kw_m3": r"power (?:input|density) per (?:unit )?volume|power per volume|\bP\s*/\s*V\b|specific power input",
    "product_rate_kg_h": r"production rate|product(?:ion)? capacity|output rate",
    "volumetric_productivity_kg_m3_h": r"volumetric productivity|space[- ]time yield",
}
_COMPILED = {k: re.compile(p, re.IGNORECASE) for k, p in PATTERNS.items()}
_CELL = re.compile(r"^([A-Z]{1,3})(\d+)$")
_UNIT_IN_LABEL = re.compile(r"[\(\[]\s*([^()\[\]]{1,20})\s*[\)\]]\s*$")
MAX_HITS = 400


def _col(letters):
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n


def _numeric(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _grid(source_cells):
    grid = {}
    for c in source_cells or []:
        m = _CELL.match(str(c.get("cell") or ""))
        if m:
            grid[(c.get("sheet"), int(m.group(2)), _col(m.group(1)))] = c
    return grid


def parameters_in(label):
    """Sizing parameters a label names (most specific first)."""
    found = [k for k, p in _COMPILED.items() if p.search(label)]
    if "motor_efficiency" in found and "efficiency" in found:
        found.remove("efficiency")
    if "gas_residence_time_s" in found and "residence_time_h" in found and "gas" not in label.lower():
        found.remove("gas_residence_time_s")
    if "head_m" in found and "differential_pressure_bar" in found:
        found.remove("head_m")
    return found


def scan(source_cells):
    """Labelled numeric values in the workbook: [{id, sheet, label, row_text, parameters, value, unit}].

    Follows the label's row to the right (merged cells often put the value
    many columns away) up to the first number, stopping at another label.
    """
    grid = _grid(source_cells)
    rows = {}
    for (sheet, row, col), cell in grid.items():
        rows.setdefault((sheet, row), []).append((col, cell))
    hits = []
    for (sheet, row), cells in sorted(rows.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
        cells.sort(key=lambda x: x[0])
        for i, (col, cell) in enumerate(cells):
            label = cell.get("value")
            if not isinstance(label, str) or not (2 <= len(label.strip()) <= 120):
                continue
            params = parameters_in(label)
            if not params:
                continue
            value_cell, unit, j = None, None, i + 1
            while j < len(cells) and j <= i + 6:
                v = cells[j][1].get("value")
                if _numeric(v):
                    value_cell = cells[j][1]
                    break
                if isinstance(v, str) and v.strip() and parameters_in(v):
                    break  # the next label starts before any value
                j += 1
            if value_cell is None:
                continue
            nxt = cells[j + 1][1].get("value") if j + 1 < len(cells) else None
            if isinstance(nxt, str) and 0 < len(nxt.strip()) <= 20 and not parameters_in(nxt):
                unit = nxt.strip()
            if unit is None:
                m = _UNIT_IN_LABEL.search(label)
                unit = m.group(1).strip() if m else None
            row_text = " ".join(str(c.get("value")) for _, c in cells[: i + 1] if isinstance(c.get("value"), str))
            hits.append({"id": f"{sheet}!{value_cell['cell']}", "sheet": sheet, "label": label.strip(),
                         "row_text": row_text[:200], "parameters": params, "value": value_cell["value"],
                         "unit": unit, "formula": bool(value_cell.get("formula"))})
            if len(hits) >= MAX_HITS:
                return hits
    return hits


def _names_tag(text, tag):
    chars = [c for c in str(tag or "").casefold() if c.isalnum()]
    if len(chars) < 2:
        return False
    pattern = r"(?<![a-z0-9])" + r"[\s/\-]*".join(re.escape(c) for c in chars) + r"(?![a-z0-9])"
    return re.search(pattern, str(text).casefold()) is not None


def for_items(hits, items, family_of):
    """Scope hits to equipment. ``items`` = [{key, tag, names}]; ``family_of(text)`` -> family or None.

    Returns {equipment_key: [hit + scope]}. A hit naming a tag goes only to
    that item; one naming a function goes to items of that function; any
    other hit is offered to every item as workbook-wide.
    """
    families = {i["key"]: next((f for f in (family_of(n) for n in i.get("names") or []) if f), None) for i in items}
    out = {i["key"]: [] for i in items}
    for hit in hits:
        text = hit["row_text"] or hit["label"]
        tagged = [i for i in items if _names_tag(text, i.get("tag"))]
        if tagged:
            targets, scope = tagged, "names this item's tag"
        else:
            family = family_of(text)
            same = [i for i in items if family and families[i["key"]] == family]
            targets, scope = (same, "names this item's function") if family else (items, "workbook-wide")
        for item in targets:
            if len(out[item["key"]]) < 40:
                out[item["key"]].append({**{k: hit[k] for k in ("id", "label", "parameters", "value", "unit")},
                                         "scope": scope})
    return out
