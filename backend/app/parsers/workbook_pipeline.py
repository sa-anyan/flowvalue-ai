"""Workbook -> blocks -> stream inventory -> explicit connections -> register.

Uses one safe workbook read. Layout adapters remain deterministic and partial.
"""
import re
from collections import defaultdict
from math import isclose

from app.parsers.balance.models import Entity, Issue, Table
from app.parsers.balance.parser import Parser
from app.parsers.balance.workbook import address, read_book
from app.parsers.inputs.xlsm_adapter import parse_xlsm
from app.parsers.inputs.xlsm_parser import TAG, classify


def build_register(report):
    units = {(e.id_evidence.sheet, e.identifier): e for e in report.entities if e.kind == "equipment"}
    for stream in [e for e in report.entities if e.kind == "material"]:
        descriptions = [v for v in stream.values if v.property in ("name", "description") and isinstance(v.original_value, str)]
        endpoints = [(v, str(v.normalized_value or v.original_value)) for v in stream.values if v.property in ("source", "destination") and v.original_value]
        for description in descriptions:
            text = str(description.original_value)
            # A directional clause must contain exactly one explicit tag on each side.
            # A mention alone never establishes a connection.
            for role, pattern in [("source", r"\bfrom\b(.*?)(?=\bto\b|$)"), ("destination", r"\bto\b(.*)$")]:
                clauses = re.findall(pattern, text, re.IGNORECASE)
                tags = [f"{m.group(1).upper()}-{m.group(2)}" for clause in clauses for m in TAG.finditer(clause)]
                if len(tags) == 1 and not any(v.property == role for v in stream.values):
                    evidence = description.model_copy(update={"id": f"{stream.key}:{role}", "property": role,
                        "label": f"Stream {stream.identifier} | {role}", "normalized_value": tags[0],
                        "status": "inferred", "note": "Explicit directional wording; review before accepting connectivity."})
                    stream.values.append(evidence)
                    endpoints.append((evidence, tags[0]))
        mentions = [(v, f"{m.group(1).upper()}-{m.group(2)}") for v in descriptions for m in TAG.finditer(str(v.original_value))]
        for evidence, tag in [*mentions, *endpoints]:
            if not TAG.fullmatch(tag):
                continue
            key = (evidence.sheet, tag)
            if key not in units:
                identity = evidence.model_copy(update={"id": f"unit:{evidence.sheet}:{tag}", "normalized_value": tag,
                    "status": "inferred", "note": "Explicit equipment tag in workbook; no sizing or design inferred."})
                units[key] = Entity(key=f"unit:{evidence.sheet}:{tag}", kind="equipment", identifier=tag,
                                    table=stream.table, id_evidence=identity)
                report.entities.append(units[key])
            unit = units[key]
            if evidence.property in ("source", "destination"):
                prop = "outlets" if evidence.property == "source" else "inlets"
                if not any(v.property == prop and v.normalized_value == stream.identifier for v in unit.values):
                    unit.values.append(evidence.model_copy(update={"id": f"{unit.key}:{stream.key}:{prop}",
                        "property": prop, "label": prop, "normalized_value": stream.identifier, "status": "inferred"}))
            if not any(v.property == "type" for v in unit.values):
                kind, basis = classify([str(v.original_value) for v in descriptions], tag)
                unit.values.append(evidence.model_copy(update={"id": f"{unit.key}:type", "property": "type",
                    "label": "Equipment type (interpreted)", "normalized_value": kind, "status": "inferred", "note": basis}))
        if not any(v.property in ("source", "destination") for v in stream.values):
            report.issues.append(Issue(code="unresolved_connection", message=f"{stream.id_evidence.sheet}: stream {stream.identifier} has no explicit tagged endpoint.", evidence_ids=[stream.id_evidence.id]))


def parse_workbook(content, filename):
    sheets, warnings = read_book(content, filename)
    report = parse_xlsm(content, filename, loaded=(sheets, warnings))
    specialized = {e.id_evidence.sheet for e in report.entities if e.kind == "material"}
    # Generic row/column/long-form adapters handle sheets without description blocks.
    remaining = [sheet for sheet in sheets if sheet.name not in specialized]
    if remaining:
        generic = Parser(content, filename, loaded=(remaining, [])).run()
        report.entities.extend(generic.entities)
        report.tables.extend(generic.tables)
        report.issues.extend(generic.issues)
        report.checks.extend(generic.checks)
        report.declarations.extend(generic.declarations)
    blocks = defaultdict(list)
    for entity in report.entities:
        if entity.kind == "material" and entity.table == "description-streams":
            blocks[(entity.id_evidence.sheet, re.sub(r"[A-Z]+", "", entity.id_evidence.cell))].append(entity)
    for (sheet, row), entities in blocks.items():
        table = Table(id=f"description:{sheet}:{row}", sheet=sheet,
                      range=f"{entities[0].id_evidence.cell}:{entities[-1].id_evidence.cell}",
                      orientation="records_in_columns", kind="material")
        report.tables.append(table)
        for entity in entities:
            entity.table = table.id
    build_register(report)
    for stream in [e for e in report.entities if e.kind == "material"]:
        for total_property, component_property in [("mass_flow", "component_mass_flow"), ("volume_flow", "component_volume_flow")]:
            totals = [v for v in stream.values if v.property == total_property and isinstance(v.original_value, (int, float))]
            components = [v for v in stream.values if v.property == component_property and isinstance(v.original_value, (int, float))]
            for total in totals:
                same_units = [v for v in components if v.original_unit == total.original_unit]
                if same_units and not isclose(sum(v.original_value for v in same_units), total.original_value, rel_tol=1e-6, abs_tol=1e-6):
                    report.issues.append(Issue(code="component_total_mismatch", message=f"{total.sheet}!{total.cell}: stream {stream.identifier} reported {total.original_value} {total.original_unit}; extracted components sum to {sum(v.original_value for v in same_units)}. Review missing components and cached formulas; no correction applied.", evidence_ids=[total.id, *[v.id for v in same_units]]))
    for sheet in sheets:
        if sheet.name in specialized:
            for (row, column), cell in sheet.cells.items():
                if cell.error or (cell.formula and cell.value is None):
                    report.issues.append(Issue(code="unresolved_formula", message=f"{sheet.name}!{address(row, column)}: formula error or unavailable stored result."))
    report.limitations.append("Supported adapters do not guarantee full-workbook coverage. Untagged streams remain independent records; ambiguous endpoints are unresolved. Sheets and source blocks are not automatically combined into one process.")
    for sheet in report.sheets:
        sheet['tables'] = sum(t.sheet == sheet['name'] for t in report.tables)
    report.parser_version = "workbook-pipeline-2.0"
    # Enforce canonical output limits before leaving the constrained worker.
    return type(report).model_validate(report.model_dump())
