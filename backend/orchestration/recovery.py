"""Conservative numeric recovery within an existing stream block; no new topology."""

import copy
import hashlib

from openpyxl.utils import coordinate_to_tuple, range_boundaries

from backend.ingestion.balance.units import convert, unit_key
from backend.ingestion.observation_identity import recovered_identity

TOKENS = {
    "mass_flow": ("mass", "flow"),
    "molar_flow": ("mol", "flow"),
    "temperature": ("temp",),
    "pressure": ("press",),
    "density": ("density",),
    "volume_flow": ("vol", "flow"),
}


def recover(parsed, findings):
    report = copy.deepcopy(parsed["report"])
    source = {(c["sheet"], c["cell"]): c for c in parsed["source_cells"]}
    entities = {e["key"]: e for e in report["entities"]}
    tables = {t["id"]: t for t in report["tables"]}
    decisions = []
    for finding in findings:
        proposal = finding.get("recovery")
        if not proposal:
            continue
        decision = {
            "sheet": finding["sheet"],
            "cell": finding["cell"],
            "status": "pending_review",
        }
        try:
            entity = entities[proposal["entity_key"]]
            table = tables[entity["table"]]
            prop, unit = proposal["property"], proposal["original_unit"]
            if prop not in TOKENS or entity["kind"] not in {"material", "energy"}:
                raise ValueError("Unsupported automatic recovery property/entity")
            cell = source[finding["sheet"], finding["cell"]]
            header = source[finding["sheet"], proposal["header_cell"]]
            if (
                table["sheet"] != finding["sheet"]
                or entity["id_evidence"]["sheet"] != finding["sheet"]
            ):
                raise ValueError("Recovery must stay within the original stream table")
            row, col = coordinate_to_tuple(finding["cell"])
            idrow, idcol = coordinate_to_tuple(entity["id_evidence"]["cell"])
            mincol, minrow, maxcol, maxrow = range_boundaries(table["range"])
            if not (minrow <= row <= maxrow and mincol <= col <= maxcol):
                raise ValueError("Source cell lies outside identified table")
            if table["orientation"] == "records_in_columns" and col != idcol:
                raise ValueError("Source cell not in the stream column")
            if table["orientation"] == "records_in_rows" and row != idrow:
                raise ValueError("Source cell not in the stream row")
            label = str(header["value"]).lower()
            if not all(token in label for token in TOKENS[prop]) or unit_key(
                unit
            ) not in unit_key(label):
                raise ValueError(
                    "Property and unit are not explicit in the source header"
                )
            value, normalized_unit, error = convert(cell["value"], prop, unit)
            if error:
                raise ValueError(error)
            previous = [
                v
                for v in entity["values"]
                if v["property"] == prop and v["normalized_value"] is not None
            ]
            if previous:
                if any(
                    (v["normalized_value"], v["normalized_unit"])
                    != (value, normalized_unit)
                    for v in previous
                ):
                    raise ValueError(
                        "Conflicts with existing extracted value; no overwrite permitted"
                    )
                decision["status"] = "already_extracted"
            else:
                evidence = {
                    "id": "recovery:"
                    + hashlib.sha256(
                        str(
                            (entity["key"], finding["sheet"], finding["cell"], prop)
                        ).encode()
                    ).hexdigest(),
                    "workbook": report["filename"],
                    "sheet": finding["sheet"],
                    "cell": finding["cell"],
                    "header_cells": [proposal["header_cell"]],
                    "original_value": cell["value"],
                    "original_unit": unit,
                    "formula": cell.get("formula"),
                    "cached": bool(cell.get("formula")),
                    "property": prop,
                    "label": str(header["value"]),
                    "component": None,
                    "normalized_value": value,
                    "normalized_unit": normalized_unit,
                    "status": "inferred",
                    "note": "AI-assisted label interpretation; exact source cell and Python unit conversion checked. Human confirmation remains required.",
                }
                evidence.update(
                    recovered_identity(report.get("sha256"), evidence["id"], "numeric-recovery-1")
                )
                entity["values"].append(evidence)
                decision["status"] = "source_checked_inferred"
        except (ValueError, KeyError, TypeError) as exc:
            decision["reason"] = str(exc)
        decisions.append(decision)
    if any(d["status"] == "source_checked_inferred" for d in decisions):
        from backend.ingestion.balance.models import BalanceReport
        from backend.ingestion.workbook_pipeline import review_registers

        date = report.pop("extracted_on", None)
        validated = BalanceReport.model_validate(report)
        validated.checks = []
        review_registers(validated)
        report = validated.model_dump(mode="json")
        report["extracted_on"] = date
    return report, decisions
