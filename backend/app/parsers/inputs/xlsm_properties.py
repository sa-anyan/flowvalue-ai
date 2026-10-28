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
    match = re.fullmatch(r"R(\d+)C(\d+)", stream["source_cell"])
    if not match:
        return []
    anchor_row, column = map(int, match.groups())
    results = []
    indexed_labels, boundaries = index if index is not None else property_index(sheet)
    unit_row = anchor_row + 1
    for row in range(unit_row + 1, min(sheet.rows, anchor_row + MAX_PROPERTY_ROWS) + 1):
        if row in boundaries:
            break
        # Find nearest physical property label to the left, across the whole block.
        labels = indexed_labels.get(row, [])
        position = bisect_left(labels, (column, "")) - 1
        if position < 0:
            continue
        label_col, label = labels[position]
        prop, dimension, component = property_info(label)
        if label.strip().lower() == "total":
            prop, dimension, component = "component_flow", "volume_flow", None
        elif prop == "composition" or (prop is None and re.fullmatch(r"[A-Za-z][A-Za-z0-9 ]{0,35}", label)):
            prop, dimension, component = "component_flow", "volume_flow", label.strip()
        elif not prop or not dimension:
            continue
        # Explicit unit headers mark each stream's volumetric and mass subcolumns.
        columns = [column]
        if prop == "component_flow":
            columns = [column, column + 5]
        for cc in columns:
            if cc > sheet.cols:
                continue
            target = sheet.cell(row, cc)
            if number(target.value) is None:
                continue
            header = sheet.text(unit_row, cc)
            unit = find_unit(label) or find_unit(header)
            actual_prop, actual_dim = prop, dimension
            if prop == "component_flow":
                if unit and "kg/" in unit.lower():
                    actual_prop, actual_dim = ("mass_flow" if component is None else "component_mass_flow"), "mass_flow"
                elif unit and ("m³/" in unit.lower() or "m3/" in unit.lower()):
                    actual_prop, actual_dim = ("volume_flow" if component is None else "component_volume_flow"), "volume_flow"
                else:
                    actual_prop, actual_dim = "component_flow_unresolved", "volume_flow"
            normalized, normalized_unit, error = convert(target.value, actual_dim, unit)
            if actual_dim == "fraction" and target.number_format.endswith("%"):
                unit = "fraction"
                normalized, normalized_unit, error = convert(target.value, actual_dim, unit)
            if target.cached:
                error = "Formula result cache may be stale; original calculation requires review."
            if target.error:
                error = "Excel formula/error cell requires review."
            evidence = Evidence(
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
                note=error or "Matched via stream column, component row and explicit unit header; review case and equipment connection.",
            )
            results.append(evidence)
            if len(results) >= MAX_PROPERTIES_PER_UNIT:
                return results
    return results
