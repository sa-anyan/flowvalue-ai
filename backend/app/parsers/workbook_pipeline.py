"""One safe read -> region adapters -> scoped references -> deterministic review."""

import re
from collections import defaultdict
from math import isclose
from time import perf_counter

from openpyxl.utils import coordinate_to_tuple

from app.parsers.balance.models import BalanceReport, Issue
from app.parsers.balance.validation import validate
from app.parsers.engineering_register import build_register
from app.parsers.stream_layout import StreamLayoutParser


def review_registers(report):
    scopes = defaultdict(list)
    for entity in report.entities:
        scopes[entity.id_evidence.sheet, entity.case].append(entity)
    for (sheet, _case), entities in scopes.items():
        # Do not combine unrelated worksheets into a physical process balance.
        scoped = BalanceReport(
            filename=report.filename,
            sha256=report.sha256,
            sheets=[],
            entities=entities,
            declarations=[v for v in report.declarations if v.sheet == sheet],
        )
        validate(scoped)
        # Register graph, rather than a name-only heuristic, owns connectivity issues.
        report.issues.extend(
            i for i in scoped.issues if i.code != "unresolved_connection"
        )
        report.checks.extend(scoped.checks)
    for stream in [e for e in report.entities if e.kind == "material"]:
        available = {v.property for v in stream.values}
        missing = [
            name for name in ("temperature", "pressure") if name not in available
        ]
        if not available.intersection({"mass_flow", "volume_flow", "molar_flow"}):
            missing.append("total flow")
        if missing:
            report.issues.append(
                Issue(
                    code="incomplete_stream",
                    message=f"{stream.id_evidence.sheet}: stream {stream.identifier} lacks {', '.join(missing)}; no defaults supplied.",
                    evidence_ids=[stream.id_evidence.id],
                )
            )
        for total_property, component_property in [
            ("mass_flow", "component_mass_flow"),
            ("volume_flow", "component_volume_flow"),
        ]:
            totals = [
                v
                for v in stream.values
                if v.property == total_property and v.component is None
            ]
            components = [
                v
                for v in stream.values
                if v.property == component_property and v.component
            ]
            for total in totals:
                # Compare only safely normalised numeric observations on one basis.
                values = [
                    v
                    for v in components
                    if v.normalized_unit == total.normalized_unit
                    and isinstance(v.normalized_value, (int, float))
                ]
                if not values or not isinstance(total.normalized_value, (int, float)):
                    continue
                amount = sum(v.normalized_value for v in values)
                if not isclose(
                    amount, total.normalized_value, rel_tol=1e-6, abs_tol=1e-6
                ):
                    report.issues.append(
                        Issue(
                            code="component_total_mismatch",
                            message=f"{total.sheet}!{total.cell}: stream {stream.identifier} reported {total.normalized_value} {total.normalized_unit}; identified component sum {amount}. Review missing components/caches; no correction applied. This is worksheet arithmetic, not physical volume-additivity or process-conservation validation.",
                            evidence_ids=[total.id, *[v.id for v in values]],
                        )
                    )
    # Every reference must resolve inside this response. Reject rather than emit
    # ambiguous graph edges or silently truncate oversized records.
    entities = {e.key: e for e in report.entities}
    evidence_ids = {v.id for e in report.entities for v in [e.id_evidence, *e.values]}
    evidence_ids.update(v.id for v in report.declarations)
    table_ids = {t.id for t in report.tables}
    if len(entities) != len(report.entities) or any(
        e.table not in table_ids for e in report.entities
    ):
        raise ValueError(
            "Internal register/table references are inconsistent; parsing stopped."
        )
    for entity in report.entities:
        if any(
            key not in entities or entities[key].kind != "material"
            for key in entity.stream_keys
        ):
            raise ValueError(
                "Internal equipment/stream reference is unresolved; parsing stopped."
            )
    for connection in report.connections:
        if (
            connection.stream_key not in entities
            or (
                connection.equipment_key is not None
                and connection.equipment_key not in entities
            )
            or any(key not in evidence_ids for key in connection.evidence_ids)
        ):
            raise ValueError(
                "Internal connection evidence is unresolved; parsing stopped."
            )


def parse_workbook(content, filename, *, metrics=None, loaded=None):
    start = perf_counter()
    parser = StreamLayoutParser(content, filename, loaded=loaded)
    opened = perf_counter()
    report = parser.run()
    extracted = perf_counter()
    # Canonical generic adapters sometimes represent component flow as mass_flow
    # plus a component; make the distinction explicit without copying evidence.
    sheet_lookup = {sheet.name: sheet for sheet in parser.sheets}
    for entity in report.entities:
        for value in entity.values:
            if value.component and value.property in (
                "mass_flow",
                "volume_flow",
                "molar_flow",
            ):
                value.property = f"component_{value.property}"
            # Preserve component labels exactly as supplied, including case/symbols.
            if value.component and value.header_cells:
                sheet = sheet_lookup[value.sheet]
                rr, cc = coordinate_to_tuple(value.header_cells[0])
                label = sheet.text(rr, cc)
                match = re.search(
                    r"\s+".join(re.escape(part) for part in value.component.split()),
                    label,
                    re.IGNORECASE,
                )
                if match:
                    value.component = match.group()
    build_register(report)
    mapped = perf_counter()
    review_registers(report)
    for entity in report.entities:
        statuses = {v.status for v in [entity.id_evidence, *entity.values]}
        entity.status = (
            "unresolved"
            if "unresolved" in statuses
            else "inferred"
            if "inferred" in statuses
            else "verified"
        )
    report.parser_version = "workbook-pipeline-3.0"
    report.limitations.append(
        "Partial, deterministic extraction for supported labelled table regions. Relationships use scoped keys; untagged streams are retained. Mention edges do not establish connectivity. Separate worksheets/cases are never silently merged. Cached formulas were not recalculated. Volume component sums are arithmetic comparisons only, not evidence of physical additivity."
    )
    result = type(report).model_validate(report.model_dump())
    if metrics is not None:
        metrics.update(
            open_validate_s=opened - start,
            extract_s=extracted - opened,
            map_s=mapped - extracted,
            review_validate_s=perf_counter() - mapped,
        )
    return result
