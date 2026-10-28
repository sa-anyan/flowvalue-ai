"""Safe web adapter for the unchanged founder-supplied XLSM extraction script."""
import re
from hashlib import sha256

from app.parsers.balance.models import BalanceReport, Entity, Evidence, Issue
from app.parsers.balance.workbook import address, read_book, safe_filename

from .xlsm_parser import classify, parse_sheet
from .xlsm_properties import stream_properties


def parse_xlsm(content: bytes, filename: str):
    filename = safe_filename(filename)
    sheets, warnings = read_book(content, filename)
    report = BalanceReport(filename=filename, sha256=sha256(content).hexdigest(),
                           parser_version="xlsm-properties-1.1", sheets=[])
    grouped = {}
    sheet_lookup = {sheet.name: sheet for sheet in sheets}
    for sheet in sheets:
        matrix = [[sheet.cell(r, c).value for c in range(1, sheet.cols + 1)]
                  for r in range(1, sheet.rows + 1)]
        streams, issues = parse_sheet(sheet.name, matrix)
        report.sheets.append({"name": sheet.name, "rows": sheet.rows, "columns": sheet.cols,
                                  "hidden": sheet.hidden, "tables": 0,
                                  "nonempty_cells": len(sheet.cells), "extracted_cells": len(streams)})
        for issue in issues:
            report.issues.append(Issue(code="xlsm_description_conflict", message=f"{sheet.name}!{issue['cell']}: {issue['issue']}"))
        for stream in streams:
            match = re.fullmatch(r"R(\d+)C(\d+)", stream["source_cell"])
            cell = address(int(match[1]), int(match[2]))
            for tag in stream["equipment_tags"]:
                grouped.setdefault(tag, []).append((sheet.name, cell, stream))
    for tag, observations in sorted(grouped.items()):
        values = []
        for index, (sheet, cell, stream) in enumerate(observations):
            values.append(Evidence(id=f"{tag}:{index}", workbook=filename, sheet=sheet,
                                   cell=cell, property="description", label=f"Stream {stream['stream_id']}",
                                   original_value=stream['description'], normalized_value=stream['description'],
                                   status="inferred", note="Equipment tag extracted from stream description; connectivity not established."))
        kind, basis = classify([s['description'] for _, _, s in observations], tag)
        first = values[0]
        classification = first.model_copy(update={"id": f"{tag}:type", "property": "type", "label": "Equipment type (interpreted)",
                                                     "normalized_value": kind, "note": basis})
        # Preserve each stream's observations, but count the tag as one unit.
        properties = []
        for sheet_name, _, stream in observations:
            for ev in stream_properties(sheet_lookup[sheet_name], stream, filename, tag):
                if len(properties) + len(values) + 1 >= 256:
                    break
                properties.append(ev)
        report.entities.append(Entity(key=tag, kind="equipment", identifier=tag, table="description-tags",
                                      id_evidence=first, values=[*values, classification, *properties]))
    for warning in warnings:
        report.issues.append(Issue(code="workbook_warning", message=warning))
    report.limitations.append("Stream numeric observations are associated by same-column and row-label evidence, not validated equipment design values. Missing units remain unresolved. No sizing or connectivity validation. Macros are ignored.")
    return report
