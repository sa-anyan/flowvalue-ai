"""Bounded, evidence-first property association for horizontally arranged XLSM streams.

Uses the already-loaded, safety-checked workbook; no extra read or AI call.
Only columns with an explicit stream description anchor are considered.
"""
import re

from app.parsers.balance.models import Evidence, Issue
from app.parsers.balance.parser import property_info
from app.parsers.balance.units import convert, find_unit, number
from app.parsers.balance.workbook import address

MAX_PROPERTIES_PER_UNIT = 200
MAX_PROPERTY_ROWS = 150

def stream_properties(sheet, stream, filename, tag):
    match = re.fullmatch(r"R(\d+)C(\d+)", stream["source_cell"])
    if not match:
        return []
    anchor_row, column = map(int, match.groups())
    results = []
    # Search this stream's column down to the next table section, bounded.
    for row in range(anchor_row + 1, min(sheet.rows, anchor_row + MAX_PROPERTY_ROWS) + 1):
        target = sheet.cell(row, column)
        if target.value is None or number(target.value) is None:
            continue
        # A numerical value may only be attached when its property label
        # occurs on exactly the same row, to the left of the stream column.
        candidates = []
        for left in range(max(1, column - 14), column):
            label = sheet.text(row, left)
            if not label:
                continue
            prop, dimension, component = property_info(label)
            if prop and dimension and prop not in ("composition", "unmapped_property"):
                candidates.append((left, label, prop, dimension, component))
        if not candidates:
            continue
        # The nearest qualifying label is the strongest evidence; if equally
        # close alternatives exist no property is silently selected.
        left, label, prop, dimension, component = max(candidates, key=lambda c: c[0])
        unit = find_unit(label)
        normalized, normalized_unit, error = convert(target.value, dimension, unit)
        # A percentage-formatted cell already contains a fraction.
        if dimension == "fraction" and target.number_format.endswith("%"):
            unit = "fraction"
            normalized, normalized_unit, error = convert(target.value, dimension, unit)
        evidence = Evidence(
            id=f"property:{tag}:{sheet.name}:{row}:{column}",
            workbook=filename, sheet=sheet.name, cell=address(row, column),
            header_cells=[address(row, left)],
            original_value=target.value, original_unit=unit,
            formula=target.formula, cached=target.cached,
            property=prop, label=f"Stream {stream['stream_id']} | {label}",
            component=component, normalized_value=normalized if not target.cached else None,
            normalized_unit=normalized_unit,
            status="unresolved" if error or target.cached else "inferred",
            note=(error or "Formula cache may be stale; confirm original calculation."
                  if target.cached else "Associated by shared stream column and row label; verify operating case."),
        )
        results.append(evidence)
        if len(results) >= MAX_PROPERTIES_PER_UNIT:
            break
    return results
