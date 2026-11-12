"""Repeated stream groups with shared component rows and per-property subheaders.

Recognises layout evidence, not a worksheet title or hardcoded stream numbers.
Reference MW/hf columns are outside stream groups. No formulas are evaluated.
"""

import re

from backend.ingestion.balance.models import Entity
from backend.ingestion.balance.parser import IDS, property_info
from backend.ingestion.balance.units import UNITS, clean, find_unit, unit_key
from backend.ingestion.balance.workbook import address


def _property_columns(sheet, header, first, last):
    count = 0
    for cc in range(first, last + 1):
        label = sheet.text(header, cc)
        key = unit_key(find_unit(label))
        if (key in UNITS["mass_flow"] or key in UNITS["molar_flow"] or key in UNITS["volume_flow"]
                or ("mol" in clean(label) and "%" in label)):
            count += 1
    return count


def parse_blocks(parser, sheet, inferred):
    anchors = sorted(
        (r, c)
        for (r, c), cell in sheet.cells.items()
        if clean(cell.value).rstrip(":") in IDS
        and IDS[clean(cell.value).rstrip(":")] == "material"
    )
    handled = set()
    for row, label_col in anchors:
        region_end = next(
            (cc - 1 for rr, cc in anchors if rr == row and cc > label_col), sheet.cols
        )
        candidates = [
            rr
            for rr in range(row + 1, min(row + 7, sheet.rows + 1))
            if clean(sheet.text(rr, label_col))
            in {"component", "components", "species", "constituent"}
        ]
        if not candidates:
            continue
        # Held-out finding: a stray partial "Component" row above the real
        # subheader hid every flow column of the block. Use the candidate with
        # the most recognised property columns; ties go to the later row, which
        # sits directly above the data.
        header = max(
            candidates,
            key=lambda rr: (_property_columns(sheet, rr, label_col + 1, region_end), rr),
        )
        starts = []
        origins = set()
        for col in range(label_col + 1, region_end + 1):
            cell, origin = sheet.header(row, col)
            text = str(cell.value or "").strip()
            if origin in origins or not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9_.-]{0,40}", text
            ):
                continue
            origins.add(origin)
            starts.append((origin[1], origin, text))
        # Group extent is established by the next stream or repeated subheaders,
        # not by unrelated notes at the right of the engineering table.
        groups = []
        for i, (col, origin, text) in enumerate(starts):
            stop = starts[i + 1][0] - 1 if i + 1 < len(starts) else region_end
            props = []
            for cc in range(col, stop + 1):
                label = sheet.text(header, cc)
                unit = find_unit(label)
                key = unit_key(unit)
                if key in UNITS["mass_flow"]:
                    props.append((cc, "mass_flow", "mass_flow", unit))
                elif key in UNITS["molar_flow"]:
                    props.append((cc, "molar_flow", "molar_flow", unit))
                elif key in UNITS["volume_flow"]:
                    props.append((cc, "volume_flow", "volume_flow", unit))
                elif "mol" in clean(label) and "%" in label:
                    props.append((cc, "mole_fraction", "fraction", "mol%"))
                elif "wt%" in clean(label) or "mass fraction" in clean(label):
                    props.append((cc, "mass_fraction", "fraction", unit or "fraction"))
            if any(p[1] == "mass_flow" for p in props):
                groups.append((col, origin, text, props))
        if not groups:
            continue  # generic/vertical/single-property adapters remain available
        end = next(
            (rr - 1 for rr, cc in anchors if cc == label_col and rr > row), sheet.rows
        )
        table = parser.new_table(
            sheet,
            row,
            label_col,
            end,
            max(p[0] for *_, props in groups for p in props),
            "material",
            "records_in_columns",
        )
        handled.add((row, label_col))
        for col, origin, identifier, props in groups:
            identity = parser.evidence(
                sheet,
                *origin,
                "Stream identifier",
                "identifier",
                headers=[address(row, label_col)],
                inferred=inferred,
            )
            entity = Entity(
                key=f"{table.id}:{address(*origin)}",
                kind="material",
                identifier=identifier,
                table=table.id,
                id_evidence=identity,
            )
            description = next(
                (
                    rr
                    for rr in range(row + 1, header)
                    if clean(sheet.text(rr, label_col))
                    in {"description", "stream description", "stream name"}
                ),
                None,
            )
            if description:
                value, pos = sheet.header(description, col)
                if value.value is not None:
                    entity.values.append(
                        parser.evidence(
                            sheet,
                            *pos,
                            "Description",
                            "description",
                            headers=[address(description, label_col)],
                            inferred=inferred,
                        )
                    )
            component_section = True
            for rr in range(header + 1, end + 1):
                label = sheet.text(rr, label_col)
                if not label:
                    continue
                total = clean(label).rstrip(":") in {
                    "total",
                    "totals",
                    "total flow",
                    "total flowrate",
                }
                prop, dim, _ = property_info(label.replace("Enhalpy", "Enthalpy"))
                if total:
                    component_section = False
                if total or component_section:
                    for cc, physical, dimension, unit in props:
                        if total and dimension == "fraction":
                            continue
                        if (
                            sheet.cell(rr, cc).value is None
                            and not sheet.cell(rr, cc).formula
                        ):
                            continue
                        entity.values.append(
                            parser.evidence(
                                sheet,
                                rr,
                                cc,
                                label,
                                physical
                                if total or dimension == "fraction"
                                else "component_" + physical,
                                dimension,
                                unit,
                                component=None if total else label,
                                headers=[
                                    address(rr, label_col),
                                    address(header, cc),
                                    address(*origin),
                                ],
                                inferred=inferred,
                            )
                        )
                elif prop and dim:
                    value, pos = sheet.header(rr, col)
                    if value.value is not None or value.formula:
                        entity.values.append(
                            parser.evidence(
                                sheet,
                                *pos,
                                label,
                                prop,
                                dim,
                                headers=[address(rr, label_col), address(*origin)],
                                inferred=inferred,
                            )
                        )
            parser.report.entities.append(entity)
    return handled
