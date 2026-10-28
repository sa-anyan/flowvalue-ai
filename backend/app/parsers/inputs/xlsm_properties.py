"""Bounded, evidence-first property association for horizontally arranged XLSM streams.

Uses the already-loaded, safety-checked workbook; no extra read or AI call.
Only columns with an explicit stream description anchor are considered.
"""
import re
from bisect import bisect_left

from app.parsers.balance.models import Evidence
from app.parsers.balance.parser import property_info
from app.parsers.balance.units import convert, find_unit, number
from app.parsers.balance.workbook import address

MAX_PROPERTIES_PER_UNIT = 200
MAX_PROPERTY_ROWS = 150

def property_index(sheet):
    labels = {}
    boundaries = set()
    for (row, column), cell in sheet.cells.items():
        if isinstance(cell.value, str) and cell.value.strip():
            labels.setdefault(row, []).append((column, cell.value.strip()))
            if column <= 12 and "stream number" in cell.value.lower():
                boundaries.add(row)
    return {row: sorted(items) for row, items in labels.items()}, boundaries


def stream_properties(sheet, stream, filename, tag, index=None):
    """Extract a horizontal stream's component rows independently of equipment tags.

    The Component/Total markers delimit component rows. Named components are
    taken from the label column, never inferred from adjacent stream values.
    """
    match = re.fullmatch(r"R(\d+)C(\d+)", stream["source_cell"])
    if not match:
        return []
    anchor_row, column = map(int, match.groups())
    indexed_labels, boundaries = index if index is not None else property_index(sheet)
    unit_row = anchor_row + 1
    end_row = min(sheet.rows, anchor_row + MAX_PROPERTY_ROWS)
    for boundary in sorted(boundaries):
        if boundary > anchor_row:
            end_row = min(end_row, boundary - 1)
            break

    # Find a distinct "Component" column belonging to this stream block.
    component_cols = [(cc, sheet.text(unit_row, cc))
                      for cc in range(1, column)
                      if sheet.text(unit_row, cc).strip().casefold() == "component"]
    component_col = component_cols[-1][0] if component_cols else None
    in_components = component_col is not None
    results = []
    for row in range(unit_row + 1, end_row + 1):
        component = None
        prop = dimension = None
        label_col = 0
        label = ""
        if component_col is not None:
            label_col = component_col
            label = sheet.text(row, label_col)
            if not label:
                continue
            if in_components and label.casefold() == "total":
                in_components = False
                prop, dimension = "component_flow", "volume_flow"
            elif in_components:
                # A component is identified by the explicit component column.
                # Blank/nonnumeric observations are not fabricated.
                component = label.strip()
                prop, dimension = "component_flow", "volume_flow"
            else:
                prop, dimension, _ = property_info(label)
        else:
            # Fallback for layouts without an explicit Component header.
            labels = indexed_labels.get(row, [])
            position = bisect_left(labels, (column, "")) - 1
            if position < 0:
                continue
            label_col, label = labels[position]
            prop, dimension, component = property_info(label)
            if label.casefold() == "total":
                prop, dimension, component = "component_flow", "volume_flow", None
            elif prop == "composition":
                prop, dimension, component = "component_flow", "volume_flow", label.strip()

        if not prop or not dimension:
            continue
        candidate_columns = [column]
        if prop == "component_flow":
            candidate_columns = [
                cc for cc in range(column, stream.get("end_column", column) + 1)
                if find_unit(sheet.text(unit_row, cc))
            ] or [column]

        for cc in candidate_columns:
            target = sheet.cell(row, cc)
            if number(target.value) is None:
                continue
            unit = find_unit(label) or find_unit(sheet.text(unit_row, cc))
            actual_prop, actual_dim = prop, dimension
            if prop == "component_flow":
                if unit and "kg/" in unit.lower():
                    actual_prop = "component_mass_flow" if component else "mass_flow"
                    actual_dim = "mass_flow"
                elif unit and ("m³/" in unit.lower() or "m3/" in unit.lower()):
                    actual_prop = "component_volume_flow" if component else "volume_flow"
                    actual_dim = "volume_flow"
                else:
                    actual_prop = "component_flow_unresolved"
            normalized, normalized_unit, error = convert(target.value, actual_dim, unit)
            if actual_dim == "fraction" and target.number_format.endswith("%"):
                unit = "fraction"
                normalized, normalized_unit, error = convert(target.value, actual_dim, unit)
            if target.cached:
                error = "Formula result cache may be stale; original calculation requires review."
            if target.error:
                error = "Excel formula/error cell requires review."
            results.append(Evidence(
                id=f"property:{tag}:{sheet.name}:{row}:{cc}",
                workbook=filename, sheet=sheet.name, cell=address(row, cc),
                header_cells=[address(row, label_col), address(unit_row, cc)],
                original_value=target.value, original_unit=unit,
                formula=target.formula, cached=target.cached,
                property=actual_prop, label=f"Stream {stream['stream_id']} | {label}",
                component=component,
                normalized_value=None if error else normalized,
                normalized_unit=normalized_unit,
                status="unresolved" if error else "inferred",
                note=error or "Stream-row and unit-column association; engineering review required.",
            ))
            if len(results) >= MAX_PROPERTIES_PER_UNIT:
                return results
    return results
