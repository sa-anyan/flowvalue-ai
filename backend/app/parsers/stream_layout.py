"""Region-level stream adapters layered on the existing canonical table parser.

One sparse workbook representation; component identities require labelled
component sections. Recognition never depends on equipment tags or row values.
"""

import re
from bisect import bisect_right

from app.parsers.balance.models import Entity
from app.parsers.balance.parser import IDS, Parser, property_info
from app.parsers.balance.units import UNITS, clean, find_unit, unit_key
from app.parsers.balance.workbook import address

COMPONENT_HEADERS = {
    "component",
    "components",
    "constituent",
    "constituents",
    "species",
    "composition",
    "componet",
}
DESCRIPTION_HEADERS = {"description", "stream description", "stream name", "name"}
INLINE_STREAM = re.compile(
    r"^\s*stream\s+(?:(?:number|no\.?|id|#)\s*[:#]?\s*)?([A-Za-z0-9][A-Za-z0-9_.-]{0,63})\s*:\s*(.+)$",
    re.IGNORECASE,
)
TOTAL_HEADERS = {"total", "totals", "total flow", "total flowrate", "total flow rate"}


def flow_basis(unit):
    key = unit_key(unit)
    for dimension in (
        "mass_flow",
        "volume_flow",
        "molar_flow",
        "fraction",
        "concentration",
    ):
        if key in UNITS[dimension]:
            if dimension == "fraction":
                if key in ("mol%", "molefraction"):
                    return "mole_fraction", dimension
                if key in ("wt%", "massfraction"):
                    return "mass_fraction", dimension
                return "composition", "unknown"  # fraction without a mass/mole basis
            return dimension, dimension
    return "composition", "unknown"


class StreamLayoutParser(Parser):
    def validate_report(self):
        # Connections and scopes are built before validating the final registers.
        pass

    def long_table(
        self, sheet, row, col, end, kind, prop_col, value_col, unit_col, inferred
    ):
        case_col = next(
            (
                cc
                for cc in range(max(1, col - 2), end + 1)
                if clean(sheet.text(row, cc))
                in ("case", "scenario", "operating case", "balance group")
            ),
            None,
        )
        if case_col is None:
            return super().long_table(
                sheet, row, col, end, kind, prop_col, value_col, unit_col, inferred
            )
        records = []
        for rr in range(row + 1, sheet.rows + 1):
            if not any(
                sheet.text(rr, cc) or sheet.cell(rr, cc).formula
                for cc in range(col, end + 1)
            ):
                break
            if clean(sheet.text(rr, col)) in IDS:
                break
            if not sheet.text(rr, col):
                self.issue(
                    "missing_identifier",
                    f"{sheet.name}!{address(rr, col)}: blank ID in long-form table; not carried forward.",
                )
                continue
            records.append(rr)
        if not records:
            return
        table = self.new_table(
            sheet, row, col, records[-1], end, kind, "records_in_rows"
        )
        groups = {}
        for rr in records:
            identifier, case = sheet.text(rr, col), sheet.text(rr, case_col)
            if (identifier, case) not in groups:
                identity = self.evidence(
                    sheet,
                    rr,
                    col,
                    "Stream identifier",
                    "identifier",
                    headers=[address(row, col)],
                    inferred=inferred,
                )
                entity = Entity(
                    key=f"{table.id}:{rr}",
                    kind=kind,
                    identifier=identifier,
                    case=case,
                    table=table.id,
                    id_evidence=identity,
                )
                entity.values.append(
                    self.evidence(
                        sheet,
                        rr,
                        case_col,
                        "Operating case",
                        "case",
                        headers=[address(row, case_col)],
                        inferred=inferred,
                    )
                )
                groups[identifier, case] = entity
                self.report.entities.append(entity)
            label = sheet.text(rr, prop_col)
            prop, dimension, component = property_info(label)
            groups[identifier, case].values.append(
                self.evidence(
                    sheet,
                    rr,
                    value_col,
                    label,
                    prop or "unmapped_property",
                    dimension if prop else "unknown",
                    sheet.text(rr, unit_col) if unit_col else None,
                    component,
                    [address(rr, prop_col)]
                    + ([address(rr, unit_col)] if unit_col else []),
                    inferred,
                )
            )

    def tables(self, sheet, inferred):
        # Sparse indexes avoid re-scanning every cell for every stream.
        row_columns = {}
        anchors = []
        for (row, col), cell in sheet.cells.items():
            row_columns.setdefault(row, []).append(col)
            if clean(cell.value).rstrip(":") in IDS:
                anchors.append((row, col))
        anchors.sort()
        by_col = {}
        by_row = {}
        for row, col in anchors:
            by_col.setdefault(col, []).append(row)
            by_row.setdefault(row, []).append(col)
        for row, col in anchors:
            if IDS[clean(sheet.text(row, col)).rstrip(":")] != "material":
                continue
            next_cols = [cc for cc in by_row[row] if cc > col]
            end_col = next_cols[0] - 1 if next_cols else sheet.cols
            # Actual property headers alongside IDs mean records-in-rows.
            if any(
                property_info(sheet.text(row, cc))[0] not in (None, "composition")
                for cc in row_columns[row]
                if col < cc <= end_col
            ):
                continue
            next_row = bisect_right(by_col[col], row)
            end_row = (
                by_col[col][next_row] - 1 if next_row < len(by_col[col]) else sheet.rows
            )
            description_row = component_row = case_row = None
            for rr in range(row + 1, min(end_row, row + 6) + 1):
                label = clean(sheet.text(rr, col)).rstrip(":")
                if label in ("case", "scenario", "operating case", "balance group"):
                    case_row = rr
                if label in DESCRIPTION_HEADERS:
                    description_row = rr
                if label in COMPONENT_HEADERS:
                    component_row = rr
                    break
                if rr > row + 1 and not label:
                    break
            if description_row is None and component_row is None:
                continue  # generic property/units and long-form adapters remain available
            starts = []
            origins = set()
            for cc in range(col + 1, end_col + 1):
                cell, origin = sheet.header(row, cc)
                if (
                    origin[1] <= col
                    or origin in origins
                    or cell.value is None
                    or not str(cell.value).strip()
                ):
                    continue
                origins.add(origin)
                # Unit headers are not stream IDs.
                if clean(cell.value) in ("units", "unit"):
                    continue
                identifier = str(cell.value).strip()
                if (
                    clean(identifier) in ("n/a", "na", "none", "unknown", "-")
                    or cell.error
                ):
                    self.issue(
                        "missing_identifier",
                        f"{sheet.name}!{address(*origin)}: invalid/placeholder stream identifier; not invented.",
                    )
                    continue
                if component_row:
                    raw_unit = sheet.header(component_row, cc)[0].value
                    unit_text = str(raw_unit or "").strip()
                    known_unit = any(
                        unit_key(unit_text) in choices for choices in UNITS.values()
                    )
                    compact_unit = re.fullmatch(
                        r"[A-Za-zµ%°][A-Za-z0-9µ%°*/^._-]{0,31}", unit_text
                    )
                    compact_id = re.fullmatch(
                        r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,63}", identifier
                    )
                    if not (
                        known_unit or (compact_id and (compact_unit or not unit_text))
                    ):
                        continue  # adjacent calculation/report headings are not streams
                elif not re.fullmatch(
                    r"[A-Za-z0-9][A-Za-z0-9_.:/ -]{0,63}", identifier
                ):
                    continue
                starts.append((cc, origin, identifier))
            if not starts:
                continue
            last_col, last_origin, _identifier = starts[-1]
            if sheet.merged.get((row, last_col + 1)) == last_origin:
                end_col = last_col
                while (
                    end_col < sheet.cols
                    and sheet.merged.get((row, end_col + 1)) == last_origin
                ):
                    end_col += 1
            first_data = (component_row or description_row) + 1
            last = first_data - 1
            for rr in range(first_data, end_row + 1):
                if not any(
                    sheet.cell(rr, cc).value is not None or sheet.cell(rr, cc).formula
                    for cc in row_columns.get(rr, [])
                    if col <= cc <= end_col
                ):
                    break
                last = rr
            table = self.new_table(
                sheet,
                row,
                col,
                max(last, component_row or description_row),
                end_col,
                "material",
                "records_in_columns",
            )
            self.used.add((sheet.name, row, col))  # dispatch by region, not worksheet
            # Interpret row roles once for all stream groups in this block.
            specs = []
            component_section = component_row is not None
            for rr in range(first_data, last + 1):
                label = sheet.text(rr, col)
                prop, dim, component = property_info(label)
                base = clean(label).rstrip(":")
                if base in COMPONENT_HEADERS:
                    component_section = True
                    continue
                if base in TOTAL_HEADERS:
                    specs.append((rr, label, "total", None, None))
                    component_section = False
                elif prop and prop != "composition":
                    specs.append((rr, label, prop, dim, component))
                    component_section = False
                elif component_section:
                    # Only a label within an explicit component section establishes identity.
                    specs.append((rr, label, "component", None, label or None))
                elif label:
                    self.issue(
                        "unmapped_property",
                        f"{sheet.name}!{address(rr, col)}: unsupported property {label!r}; no component inferred.",
                    )
            for index, (cc, origin, identifier) in enumerate(starts):
                stop = starts[index + 1][0] - 1 if index + 1 < len(starts) else end_col
                if sheet.merged.get((row, cc + 1)) == origin:
                    # An explicit merged stream header declares the group's extent.
                    stop = cc
                    while (
                        stop < end_col and sheet.merged.get((row, stop + 1)) == origin
                    ):
                        stop += 1
                identity = self.evidence(
                    sheet,
                    *origin,
                    "Stream identifier",
                    "identifier",
                    headers=[address(row, col)],
                    inferred=inferred,
                )
                entity = Entity(
                    key=f"{table.id}:{address(*origin)}",
                    kind="material",
                    identifier=identifier,
                    case=sheet.text(case_row, cc) if case_row else "",
                    table=table.id,
                    id_evidence=identity,
                )
                if case_row:
                    entity.values.append(
                        self.evidence(
                            sheet,
                            case_row,
                            cc,
                            "Operating case",
                            "case",
                            headers=[address(case_row, col)],
                            inferred=inferred,
                        )
                    )
                if description_row:
                    source, pos = sheet.header(description_row, cc)
                    if source.value is not None:
                        entity.values.append(
                            self.evidence(
                                sheet,
                                *pos,
                                f"Stream {identifier} | Description",
                                "description",
                                headers=[address(description_row, col)],
                                inferred=inferred,
                            )
                        )
                for rr, label, prop, dim, component in specs:
                    if prop in ("component", "total"):
                        columns = [
                            c
                            for c in range(cc, stop + 1)
                            if (
                                component_row
                                and sheet.header(component_row, c)[0].value is not None
                            )
                            or sheet.cell(rr, c).value is not None
                            or sheet.cell(rr, c).formula
                        ]
                        if not columns:
                            columns = [
                                cc
                            ]  # unknown basis retained, never treated as zero
                        for c in columns:
                            raw_unit, unit_pos = (
                                sheet.header(component_row, c)
                                if component_row
                                else (None, (rr, col))
                            )
                            unit = (
                                str(raw_unit.value).strip()
                                if raw_unit and raw_unit.value is not None
                                else None
                            )
                            physical, dimension = flow_basis(unit)
                            if prop == "component" and component is None:
                                self.issue(
                                    "missing_component",
                                    f"{sheet.name}!{address(rr, col)}: component identity missing; values retained unresolved.",
                                )
                            value = sheet.cell(rr, c)
                            if value.value is None and not value.formula:
                                continue
                            if physical == "composition":
                                physical = (
                                    "component_flow_unresolved"
                                    if prop == "component"
                                    else "total_flow_unresolved"
                                )
                            physical = (
                                f"component_{physical}"
                                if prop == "component" and physical.endswith("_flow")
                                else physical
                            )
                            ev = self.evidence(
                                sheet,
                                rr,
                                c,
                                f"Stream {identifier} | {label or 'Unnamed component'}",
                                physical,
                                dimension,
                                unit,
                                component,
                                [address(rr, col), address(*unit_pos)],
                                inferred=True,
                            )
                            if prop == "component" and component is None:
                                ev.status, ev.normalized_value, ev.note = (
                                    "unresolved",
                                    None,
                                    "Component identity missing.",
                                )
                            entity.values.append(ev)
                    else:
                        unit = find_unit(label)
                        # Non-flow state properties use the stream's primary column.
                        if (
                            sheet.cell(rr, cc).value is None
                            and not sheet.cell(rr, cc).formula
                        ):
                            continue
                        entity.values.append(
                            self.evidence(
                                sheet,
                                rr,
                                cc,
                                f"Stream {identifier} | {label}",
                                prop,
                                dim,
                                unit,
                                component,
                                [address(rr, col)],
                                inferred=inferred,
                            )
                        )
                self.report.entities.append(entity)
        super().tables(sheet, inferred)
        for (rr, cc), cell in sheet.cells.items():
            if (sheet.name, rr, cc) in self.used or not isinstance(cell.value, str):
                continue
            inline = INLINE_STREAM.match(cell.value)
            if not inline:
                continue
            table = self.new_table(sheet, rr, cc, rr, cc, "material", "records_in_rows")
            identity = self.evidence(
                sheet, rr, cc, "Inline stream identifier", "identifier", inferred=True
            )
            identity.normalized_value = inline[1]
            identity.note = "Identifier explicitly supplied in an inline Stream ID: description label."
            description = self.evidence(
                sheet,
                rr,
                cc,
                f"Stream {inline[1]} | Description",
                "description",
                inferred=True,
            )
            description.normalized_value = inline[2]
            self.report.entities.append(
                Entity(
                    key=f"{table.id}:{rr}:{cc}",
                    kind="material",
                    identifier=inline[1],
                    table=table.id,
                    id_evidence=identity,
                    values=[description],
                )
            )
