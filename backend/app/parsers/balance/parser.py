"""Evidence-first table recognizer. No equipment sizing, costing or thermodynamics."""

import re
from hashlib import sha256
from math import isfinite

from .models import BalanceReport, Entity, Evidence, Issue, Table
from .units import clean, convert, find_unit, number, unit_key
from .workbook import address, read_book, safe_filename

IDS = {
    "stream id": "material",
    "stream number": "material",
    "stream no": "material",
    "stream no.": "material",
    "stream": "material",
    "material stream": "material",
    "material stream id": "material",
    "energy stream id": "energy",
    "energy stream": "energy",
    "energy id": "energy",
    "equipment tag": "equipment",
    "equipment id": "equipment",
    "tag": "equipment",
    "unit tag": "equipment",
    "unit operation": "equipment",
}
TEXT = {
    "stream name": "name",
    "name": "name",
    "description": "name",
    "equipment name": "name",
    "source": "source",
    "from": "source",
    "source equipment": "source",
    "source unit": "source",
    "from node": "source",
    "destination": "destination",
    "to": "destination",
    "destination equipment": "destination",
    "destination unit": "destination",
    "to node": "destination",
    "phase": "phase",
    "fluid phase": "phase",
    "type": "type",
    "equipment type": "type",
    "unit type": "type",
    "inlet streams": "inlets",
    "inlet stream": "inlets",
    "outlet streams": "outlets",
    "outlet stream": "outlets",
    "boundary direction": "direction",
    "direction": "direction",
    "flow direction": "direction",
    "data quality": "provenance",
    "evidence": "provenance",
    "confidence": "provenance",
    "assumption / note": "provenance",
    "interpretation": "provenance",
    "case": "case",
    "scenario": "case",
    "operating case": "case",
    "balance group": "case",
}
DECLARATIONS = {
    "balance basis",
    "mass balance basis",
    "component balance basis",
    "energy balance basis",
    "energy sign convention",
}


# Header matching avoids single-letter abbreviations without an explicit unit.
def property_info(label):
    t = clean(label).replace("_", " ")
    u = find_unit(t)
    base = re.sub(r"\[[^\]]*\]|\([^)]*\)", "", t).strip(" :")
    if t in TEXT:
        return TEXT[t], None, None
    if base in TEXT:
        return TEXT[base], None, None
    if t in DECLARATIONS:
        return "declaration", None, None
    component = None
    match = re.match(
        r"(?:component\s+)?(.+?)\s+(mass fraction|mole fraction|mass flow|molar flow|concentration)",
        t,
    )
    reverse = re.match(
        r"(mass fraction|mole fraction|mass flow|molar flow|concentration)\s*[:\-]\s*([^\[(]+)",
        t,
    )
    if match:
        component = match.group(1).strip()
        t = match.group(2) + " " + (u or "")
    elif reverse:
        component = reverse.group(2).strip()
        t = reverse.group(1) + " " + (u or "")
    if "mass fraction" in t or "wt%" in t:
        return "mass_fraction", "fraction", component
    if "mole fraction" in t or "molar fraction" in t or "mol%" in t:
        return "mole_fraction", "fraction", component
    if "concentration" in t:
        return "concentration", "concentration", component
    if any(
        k in t
        for k in (
            "mass flow",
            "mass rate",
            "massflow",
            "total kg",
            "total mass",
            "kg/hour",
        )
    ) or base in ("mass", "flowrate mass"):
        return "mass_flow", "mass_flow", component
    if base == "flow" and unit_key(u) in (
        "kg/h",
        "kg/s",
        "kg/min",
        "g/s",
        "t/h",
        "lb/h",
    ):
        return "mass_flow", "mass_flow", None
    if base in ("full kw", "turn kw", "turndown kw"):
        return base.replace(" ", "_"), "power", None
    if "molar flow" in t or "mole flow" in t or base == "molar rate":
        return "molar_flow", "molar_flow", component
    if "volumetric flow" in t or "volume flow" in t:
        return "volume_flow", "volume_flow", None
    if "temperature" in t or base in ("temp", "temp.", "t") and u:
        return "temperature", "temperature", None
    if "pressure" in t or base == "p" and u:
        return "pressure", "pressure", None
    if "density" in t:
        return "density", "density", None
    if "vapour fraction" in t or "vapor fraction" in t:
        return "vapor_fraction", "fraction", None
    if (
        "enthalpy flow" in t
        or "enthalpy rate" in t
        or "total enthalpy" in t
        and unit_key(u) in ("kw", "kj/h", "w", "mw")
    ):
        return "enthalpy_flow", "power", None
    if "enthalpy" in t:
        return "specific_enthalpy", "enthalpy", None
    for phrase, prop in [
        ("heat added", "heat_added"),
        ("heat removed", "heat_removed"),
        ("work in", "work_in"),
        ("work out", "work_out"),
        ("heat duty", "heat_duty"),
        ("heat flow", "heat_duty"),
        ("heating duty", "heat_added"),
        ("cooling duty", "heat_removed"),
        ("electrical power", "electrical_power"),
        ("electric power", "electrical_power"),
        ("power consumption", "electrical_power"),
        ("power", "electrical_power"),
        ("duty", "heat_duty"),
    ]:
        if phrase in t:
            return prop, "power", None
    for phrase, dim in [
        ("volume", "volume"),
        ("diameter", "length"),
        ("height", "length"),
        ("length", "length"),
        ("area", "area"),
    ]:
        if base == phrase or base.startswith("design " + phrase):
            return base.replace(" ", "_"), dim, None
    if "efficiency" in t:
        return "efficiency", "fraction", None
    # Bare component labels are recognized only as unknown-basis composition, never assumed kg/h.
    if re.fullmatch(r"(?:[A-Z][a-z]?\d*){1,8}", str(label).strip()) or base in (
        "water",
        "hydrogen",
        "oxygen",
        "nitrogen",
        "biomass",
        "carbon dioxide",
        "ammonia",
    ):
        return "composition", "unknown", str(label).strip()
    return None, None, None


class Parser:
    def __init__(self, content, name):
        self.filename = safe_filename(name)
        self.sheets, self.warnings = read_book(content, name)
        self.report = BalanceReport(
            filename=self.filename, sha256=sha256(content).hexdigest(), sheets=[]
        )
        self.count = 0
        self.used = set()

    def issue(self, code, message, ids=()):
        if len(self.report.issues) >= 2000:
            raise ValueError(
                "More than 2,000 parsing issues; split the workbook for review."
            )
        self.report.issues.append(
            Issue(code=code, message=message, evidence_ids=list(ids))
        )

    def evidence(
        self,
        s,
        r,
        c,
        label,
        prop,
        dim=None,
        unit=None,
        component=None,
        headers=(),
        inferred=False,
    ):
        self.count += 1
        if self.count > 5000:
            raise ValueError(
                "More than 5,000 extracted values; split this workbook into smaller engineering scopes."
            )
        cell = s.cell(r, c)
        u = unit or find_unit(label)
        raw = cell.value
        if isinstance(raw, float) and not isfinite(raw):
            raw = str(raw)
        if prop == "composition" and u:
            if unit_key(u) in ("kg/h", "kg/s", "kg/min", "g/s", "t/h", "lb/h"):
                prop, dim = "mass_flow", "mass_flow"
            elif unit_key(u) in ("massfraction", "wt%"):
                prop, dim = "mass_fraction", "fraction"
            elif unit_key(u) in ("molefraction", "mol%"):
                prop, dim = "mole_fraction", "fraction"
        conversion_unit = u
        if dim == "pressure" and unit_key(u) in ("bar", "pa", "kpa", "mpa"):
            if "absolute" in clean(label) or " abs" in clean(label):
                conversion_unit = unit_key(u) + "a"
            elif "gauge" in clean(label):
                conversion_unit = unit_key(u) + "g"
        status = "verified"
        note = (
            "Direct workbook observation; engineering completeness is not established."
        )
        if dim:
            val, target, error = convert(raw, dim, conversion_unit)
            if (
                dim == "fraction"
                and u is None
                and any(
                    x in clean(label)
                    for x in (
                        "mass fraction",
                        "mole fraction",
                        "vapor fraction",
                        "vapour fraction",
                        "efficiency",
                    )
                )
            ):
                u = "fraction"
                val, target, error = convert(raw, dim, u)
            if (
                dim == "fraction"
                and cell.number_format.endswith("%")
                and number(raw) is not None
            ):
                # Excel percent cells store a fractional number. Do not divide it a second time.
                u = "fraction (Excel percent format)"
                val, target, error = convert(raw, dim, "fraction")
            status = "unresolved" if error else status
            note = error or note
        else:
            val, target = raw, None
            if raw is None or str(raw).strip() == "":
                status = "unresolved"
                note = "Blank source cell; no default applied."
        if (
            prop in ("heat_added", "heat_removed", "work_in", "work_out")
            and isinstance(val, (int, float))
            and val < 0
        ):
            val = None
            status = "unresolved"
            note = "Directed heat/work terms require non-negative magnitudes. Signed duty must be supplied with an unambiguous convention."
        if prop == "phase" and raw is not None:
            phases = {
                "liquid": "liquid",
                "vapor": "vapor",
                "vapour": "vapor",
                "gas": "gas",
                "solid": "solid",
                "mixed": "mixed",
                "two phase": "mixed",
                "two-phase": "mixed",
                "aqueous": "liquid",
            }
            val = phases.get(clean(raw))
            if val is None:
                status = "unresolved"
                note = "Unrecognized phase label; original text retained."
        if cell.error or (cell.formula and raw is None):
            status = "unresolved"
            val = None
            note = "Formula error or unavailable calculation cache. Open and recalculate in the originating application; no formula was executed."
        elif status != "unresolved" and (cell.cached or inferred):
            status = "inferred"
            note = (
                "Stored formula result may be stale; confirm in originating application."
                if cell.cached
                else "Source labels identify this as synthetic, inferred or unverified; engineering confirmation required."
            )
        e = Evidence(
            id=f"v{self.count}",
            workbook=self.filename,
            sheet=s.name,
            cell=address(r, c),
            header_cells=list(dict.fromkeys(headers)),
            original_value=raw,
            original_unit=u,
            formula=cell.formula,
            cached=cell.cached,
            property=prop,
            label=label,
            component=component,
            normalized_value=val,
            normalized_unit=target,
            status=status,
            note=note,
        )
        self.used.add((s.name, r, c))
        if status == "unresolved":
            self.issue("unresolved_value", f"{s.name}!{e.cell}: {note}", [e.id])
        return e

    def run(self):
        for s in self.sheets:
            start = len(self.report.tables)
            # Sheet titles/headings are retained as context and can downgrade, never upgrade, evidence.
            heading = " ".join(
                s.text(r, c)
                for r in range(1, min(s.rows, 4) + 1)
                for c in range(1, min(s.cols, 8) + 1)
            )
            inferred = bool(
                re.search(
                    r"synthetic|illustrative|inferred|not original|not verified|unverified",
                    s.name + " " + heading,
                    re.IGNORECASE,
                )
            )
            for (r, c), cell in s.cells.items():
                if clean(cell.value) in DECLARATIONS and c < s.cols:
                    self.report.declarations.append(
                        self.evidence(
                            s,
                            r,
                            c + 1,
                            str(cell.value),
                            "declaration",
                            headers=[address(r, c)],
                            inferred=inferred,
                        )
                    )
            self.tables(s, inferred)
            recognized = sum(1 for name, _, _ in self.used if name == s.name)
            self.report.sheets.append(
                {
                    "name": s.name,
                    "rows": s.rows,
                    "columns": s.cols,
                    "hidden": s.hidden,
                    "tables": len(self.report.tables) - start,
                    "nonempty_cells": len(s.cells),
                    "extracted_cells": recognized,
                }
            )
            if len(self.report.tables) == start:
                self.issue(
                    "unclassified_sheet",
                    f"{s.name}: no supported engineering table identified. Sheet content was not interpreted as streams.",
                )
            # All workbook error/missing cache cells must be visible, including unrecognized regions.
            for (r, c), cell in s.cells.items():
                if (cell.error or cell.formula and cell.value is None) and (
                    s.name,
                    r,
                    c,
                ) not in self.used:
                    self.issue(
                        "unresolved_formula",
                        f"{s.name}!{address(r, c)}: formula error or missing cache outside recognized tables.",
                    )
        for w in self.warnings:
            self.issue("workbook_warning", w)
        if not self.report.tables:
            self.issue(
                "no_tables",
                "No supported engineering tables found; this is not a successful process reconstruction.",
            )
        from .validation import validate

        validate(self.report)
        for entity in self.report.entities:
            if len(entity.values) > 256:
                raise ValueError(
                    "More than 256 observations for one record; split the table."
                )
            statuses = [entity.id_evidence.status] + [v.status for v in entity.values]
            entity.status = (
                "unresolved"
                if "unresolved" in statuses
                else "inferred"
                if "inferred" in statuses
                else "verified"
            )
        if (
            len(self.report.declarations) > 100
            or len(self.report.entities) > 1500
            or len(self.report.issues) > 2000
            or len(self.report.checks) > 2000
        ):
            raise ValueError(
                "Engineering extraction exceeds safe record/issue limits; split the workbook."
            )
        return self.report

    def tables(self, s, inferred):
        for r in range(1, s.rows + 1):
            anchors = [c for c in range(1, s.cols + 1) if clean(s.text(r, c)) in IDS]
            for i, c in enumerate(anchors):
                if (s.name, r, c) in self.used:
                    continue
                kind = IDS[clean(s.text(r, c))]
                end = anchors[i + 1] - 1 if i + 1 < len(anchors) else s.cols
                long_headers = {
                    clean(s.text(r, cc)): cc for cc in range(c + 1, end + 1)
                }
                prop_col = next(
                    (
                        long_headers[k]
                        for k in ("property", "parameter", "variable")
                        if k in long_headers
                    ),
                    None,
                )
                value_col = next(
                    (long_headers[k] for k in ("value", "result") if k in long_headers),
                    None,
                )
                if prop_col and value_col:
                    self.long_table(
                        s,
                        r,
                        c,
                        end,
                        kind,
                        prop_col,
                        value_col,
                        long_headers.get("unit", long_headers.get("units")),
                        inferred,
                    )
                    continue
                headers = []
                for cc in range(c + 1, end + 1):
                    cell, (rr, origin) = s.header(r, cc)
                    prop, dim, comp = property_info(cell.value)
                    if prop:
                        headers.append(
                            (cc, str(cell.value), prop, dim, comp, address(rr, origin))
                        )
                # Record rows need actual property headers beside the identifier.
                if any(h[2] != "composition" for h in headers):
                    self.row_table(s, r, c, end, kind, headers, inferred)
                else:
                    self.column_table(s, r, c, end, kind, inferred)
        # Standalone equipment ledgers often use "Equipment" with explicit names, not tags.
        for (r, c), cell in list(s.cells.items()):
            if clean(cell.value) == "equipment" and (s.name, r, c) not in self.used:
                hs = []
                for cc in range(c + 1, s.cols + 1):
                    p, d, comp = property_info(s.text(r, cc))
                    if p:
                        hs.append((cc, s.text(r, cc), p, d, comp, address(r, cc)))
                if hs:
                    self.row_table(
                        s,
                        r,
                        c,
                        s.cols,
                        "equipment",
                        hs,
                        inferred,
                        identifier_inferred=True,
                    )

    def long_table(self, s, r, c, end, kind, prop_col, value_col, unit_col, inferred):
        rows = []
        for rr in range(r + 1, s.rows + 1):
            if not any(s.text(rr, cc) for cc in range(c, end + 1)):
                break
            if clean(s.text(rr, c)) in IDS:
                break
            if not s.text(rr, c):
                self.issue(
                    "missing_identifier",
                    f"{s.name}!{address(rr, c)}: property row has no identifier. Blank IDs are not carried forward.",
                )
                continue
            rows.append(rr)
        if not rows:
            return
        t = self.new_table(s, r, c, rows[-1], end, kind, "records_in_rows")
        entities = {}
        for rr in rows:
            ident = s.text(rr, c)
            if ident not in entities:
                id_ev = self.evidence(
                    s,
                    rr,
                    c,
                    s.text(r, c),
                    "identifier",
                    headers=[address(r, c)],
                    inferred=inferred,
                )
                entities[ident] = Entity(
                    key=f"{t.id}:{rr}",
                    kind=kind,
                    identifier=ident,
                    table=t.id,
                    id_evidence=id_ev,
                )
                self.report.entities.append(entities[ident])
            label = s.text(rr, prop_col)
            p, d, component = property_info(label)
            if not p:
                p = "unmapped_property"
                d = "unknown"
            units = s.text(rr, unit_col) if unit_col else None
            entities[ident].values.append(
                self.evidence(
                    s,
                    rr,
                    value_col,
                    label,
                    p,
                    d,
                    units,
                    component,
                    [address(rr, prop_col)]
                    + ([address(rr, unit_col)] if unit_col else []),
                    inferred,
                )
            )

    def new_table(self, s, r, c, rend, cend, kind, orientation):
        if len(self.report.tables) >= 300:
            raise ValueError(
                "More than 300 candidate engineering tables; split workbook."
            )
        t = Table(
            id=f"t{len(self.report.tables) + 1}",
            sheet=s.name,
            range=f"{address(r, c)}:{address(rend, cend)}",
            orientation=orientation,
            kind=kind,
        )
        self.report.tables.append(t)
        self.used.add((s.name, r, c))
        return t

    def row_table(
        self, s, r, c, end, kind, headers, inferred, identifier_inferred=False
    ):
        known_cols = {h[0] for h in headers}
        for cc in range(c + 1, end + 1):
            if s.text(r, cc) and cc not in known_cols:
                self.issue(
                    "unmapped_header",
                    f'{s.name}!{address(r, cc)}: header "{s.text(r, cc)}" was not interpreted. Review this column in the source workbook.',
                )
        for cc in range(max(1, c - 2), c):
            if clean(s.text(r, cc)) in (
                "case",
                "scenario",
                "operating case",
                "balance group",
            ):
                headers.append((cc, s.text(r, cc), "case", None, None, address(r, cc)))
        # A units-only second header row is supported; no numeric record is consumed as units.
        unitsrow = r + 1
        units = {
            cc: s.text(unitsrow, cc)
            for cc, *_ in headers
            if find_unit(s.text(unitsrow, cc))
        }
        start = r + 2 if not s.text(unitsrow, c) and units else r + 1
        rend = start - 1
        records = []
        for rr in range(start, s.rows + 1):
            if not any(
                s.text(rr, cc) or s.cell(rr, cc).formula for cc in range(c, end + 1)
            ):
                break
            if clean(s.text(rr, c)) in IDS or clean(s.text(rr, c)) == "equipment":
                break
            ident = s.text(rr, c)
            if not ident:
                if any(s.text(rr, h[0]) for h in headers):
                    self.issue(
                        "missing_identifier",
                        f"{s.name}!{address(rr, c)}: data row has no stream/equipment identifier; not assigned an invented tag.",
                    )
                rend = rr
                continue
            if clean(ident) in ("total", "totals", "sum"):
                break
            records.append((rr, ident))
            rend = rr
        if not records:
            return
        t = self.new_table(s, r, c, max(rend, r), end, kind, "records_in_rows")
        for rr, ident in records:
            downgrade = inferred or identifier_inferred
            for cc, _, prop, _, _, _ in headers:
                if prop == "provenance" and re.search(
                    r"synthetic|inferred|not verified|unverified|assum",
                    s.text(rr, cc),
                    re.IGNORECASE,
                ):
                    downgrade = True
            id_ev = self.evidence(
                s,
                rr,
                c,
                s.text(r, c),
                "identifier",
                headers=[address(r, c)],
                inferred=downgrade,
            )
            case = next(
                (s.text(rr, cc) for cc, _, p, _, _, _ in headers if p == "case"), ""
            )
            entity = Entity(
                key=f"{t.id}:{rr}",
                kind=kind,
                identifier=ident,
                case=case,
                table=t.id,
                id_evidence=id_ev,
                status="inferred" if downgrade else "verified",
            )
            if identifier_inferred:
                self.issue(
                    "name_as_identifier",
                    f"{s.name}!{id_ev.cell}: equipment name used as provisional identifier; a unique engineering tag was not supplied.",
                    [id_ev.id],
                )
            for cc, label, p, d, comp, haddr in headers:
                if p == "case":
                    continue
                u = find_unit(label) or units.get(cc)
                entity.values.append(
                    self.evidence(
                        s,
                        rr,
                        cc,
                        label,
                        p,
                        d,
                        u,
                        comp,
                        [haddr] + ([address(unitsrow, cc)] if cc in units else []),
                        downgrade,
                    )
                )
            self.report.entities.append(entity)

    def column_table(self, s, r, c, end, kind, inferred):
        props = []
        rend = r
        # Common transposed layout: property | units | S1 | S2.
        unit_col = (
            c + 1
            if clean(s.text(r, c + 1)) in ("unit", "units")
            or not s.text(r, c + 1)
            and any(
                find_unit(s.text(rr, c + 1))
                for rr in range(r + 1, min(s.rows, r + 5) + 1)
            )
            else None
        )
        for rr in range(r + 1, s.rows + 1):
            label = s.text(rr, c)
            if not label and not any(s.text(rr, cc) for cc in range(c + 1, end + 1)):
                break
            if clean(label) in IDS:
                break
            p, d, comp = property_info(label)
            if p:
                props.append((rr, label, p, d, comp))
            rend = rr
        if not props:
            return
        columns = [
            cc for cc in range(c + 1, end + 1) if cc != unit_col and s.text(r, cc)
        ]
        if not columns:
            return
        t = self.new_table(s, r, c, rend, end, kind, "records_in_columns")
        for cc in columns:
            ident = s.text(r, cc)
            id_ev = self.evidence(
                s,
                r,
                cc,
                s.text(r, c),
                "identifier",
                headers=[address(r, c)],
                inferred=inferred,
            )
            entity = Entity(
                key=f"{t.id}:{cc}",
                kind=kind,
                identifier=ident,
                table=t.id,
                id_evidence=id_ev,
                status="inferred" if inferred else "verified",
            )
            for rr, label, p, d, comp in props:
                u = find_unit(label) or (s.text(rr, unit_col) if unit_col else None)
                entity.values.append(
                    self.evidence(
                        s,
                        rr,
                        cc,
                        label,
                        p,
                        d,
                        u,
                        comp,
                        [address(rr, c)]
                        + ([address(rr, unit_col)] if unit_col else []),
                        inferred,
                    )
                )
            self.report.entities.append(entity)


def parse_excel(content: bytes, filename: str) -> BalanceReport:
    return Parser(content, filename).run()
