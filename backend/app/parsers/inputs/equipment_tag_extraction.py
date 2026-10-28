"""Deterministic equipment-tag evidence derived only from workbook cell text.

Augments the existing balance report; never sizes equipment or assumes connectivity.
Runs inside the already resource-limited Excel worker.
"""
import re

from app.parsers.balance.models import Entity, Evidence, Issue
from app.parsers.balance.workbook import address, read_book

TAG = re.compile(r"(?<![A-Za-z0-9])([A-Z]{1,4})\s*[-–]\s*(\d{2,5})(?!\d)", re.IGNORECASE)
KEYWORDS = {
    "storage tank": "Storage tank",
    "buffer tank": "Buffer tank",
    "ph adjustment": "pH adjustment unit",
    "bioreactor": "Bioreactor",
    "settler": "Settler",
    "heat exchanger": "Heat exchanger",
    "pump": "Pump",
    "compressor": "Compressor",
    "reactor": "Reactor",
    "column": "Column",
    "vessel": "Vessel",
}
MAX_EQUIPMENT = 300

def augment_equipment(report, content, filename):
    sheets, _ = read_book(content, filename)
    existing = {entity.identifier.upper() for entity in report.entities if entity.kind == "equipment"}
    matches = {}
    for sheet in sheets:
        for (row, col), cell in sheet.cells.items():
            if not isinstance(cell.value, str) or not cell.value.strip():
                continue
            text = cell.value.strip()
            for hit in TAG.finditer(text):
                tag = hit.group(1).upper() + "-" + hit.group(2)
                if tag in existing:
                    continue
                matches.setdefault(tag, []).append((sheet.name, row, col, text, cell))
    available = max(0, 1500 - len(report.entities))
    for index, (tag, sightings) in enumerate(sorted(matches.items())):
        if index >= min(MAX_EQUIPMENT, available):
            report.issues.append(Issue(code="equipment_tag_limit",message="Additional equipment tags omitted due to extraction limits."))
            break
        name, row, col, raw, cell = sightings[0]
        labels = {value for description in [s[3].lower() for s in sightings] for key, value in KEYWORDS.items() if key in description and not (key == "reactor" and "bioreactor" in description)}
        classification = next(iter(labels)) if len(labels) == 1 else None
        eid = f"tag-{index + 1}"
        evidence = Evidence(
            id=eid, workbook=report.filename, sheet=name, cell=address(row,col),
            original_value=raw, property="identifier", label="Equipment tag in source text",
            normalized_value=tag, status="inferred",
            note="Deterministic tag extraction from workbook text; equipment identity and connections require review.",
        )
        values = []
        if classification:
            values.append(Evidence(
                id=eid+"-type", workbook=report.filename, sheet=name, cell=address(row,col),
                original_value=raw, property="type", label="Keyword-based equipment classification",
                normalized_value=classification, status="inferred",
                note="Description keyword classification; not an independently verified equipment specification.",
            ))
        report.entities.append(Entity(
            key="equipment-text:"+tag, kind="equipment", identifier=tag,
            table="description-evidence", id_evidence=evidence, values=values, status="inferred"
        ))
        if classification is None and len(report.issues) < 2000:
            report.issues.append(Issue(code="equipment_type_review",message=f"{tag}: equipment type cannot be classified unambiguously from source text.",evidence_ids=[eid]))
    report.coverage += " Equipment tags in free-text cells are extracted as inferred evidence; links, quantities and cost are not established."
    return report
