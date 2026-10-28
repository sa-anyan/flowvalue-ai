"""Safe web adapter for the unchanged founder-supplied XLSM extraction script."""
from hashlib import sha256
import re

from app.parsers.balance.models import BalanceReport, Entity, Evidence, Issue
from app.parsers.balance.workbook import address, read_book, safe_filename
from .xlsm_parser import parse_sheet, classify


def parse_xlsm(content: bytes, filename: str):
    filename = safe_filename(filename)
    sheets, warnings = read_book(content, filename)
    report = BalanceReport(filename=filename, sha256=sha256(content).hexdigest(),
                           parser_version="xlsm-descriptions-1.0", sheets=[])
    grouped = {}
    for sheet in sheets:
        matrix = [[sheet.cell(r, c).value for c in range(1, sheet.cols + 1)]
                  for r in range(1, sheet.rows + 1)]
        streams, issues = parse_sheet(sheet.name, matrix)
        report.sheets.append(dict(name=sheet.name, rows=sheet.rows, columns=sheet.cols,
                                  hidden=sheet.hidden, tables=0,
                                  nonempty_cells=len(sheet.cells), extracted_cells=len(streams)))
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
        kind, basis = classify([s['description'] for _, _, s in observations])
        first = values[0]
        classification = first.model_copy(update=dict(id=f"{tag}:type", property="type", label="Equipment type (interpreted)",
                                                     normalized_value=kind, note=basis))
        # Type is an interpretation, never a supplied equipment design.
        report.entities.append(Entity(key=tag, kind="equipment", identifier=tag, table="description-tags",
                                      id_evidence=first, values=[*values, classification]))
    for warning in warnings:
        report.issues.append(Issue(code="workbook_warning", message=warning))
    report.limitations.append("Tagged equipment from stream descriptions only. No numerical mass/energy balance extraction, equipment sizing or connectivity validation. Macros are ignored.")
    return report
