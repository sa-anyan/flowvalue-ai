"""Scoped, source-backed stream/equipment graph; no numerical stream copies."""

import re
from collections import defaultdict
from hashlib import sha256

from app.parsers.balance.models import Connection, Entity, Issue
from app.parsers.balance.units import clean
from app.parsers.inputs.xlsm_parser import TYPES

TAG = re.compile(r"(?<![\w])([A-Za-z]{1,5})\s*[-–_]\s*(\d{1,6}[A-Za-z]?)(?![\w])")
FROM = re.compile(r"\bfrom\b(.*?)(?=\bto\b|$)", re.IGNORECASE)
TO = re.compile(r"\bto\b(.*)$", re.IGNORECASE)
BOUNDARIES = {
    "outside",
    "external",
    "boundary",
    "feed",
    "product",
    "waste",
    "environment",
    "atmosphere",
    "source",
    "sink",
    "unknown",
    "not specified",
    "none",
    "n/a",
}


def stable_key(kind, *scope):
    return f"{kind}:{sha256(repr(scope).encode()).hexdigest()[:32]}"


def normalize_tag(value):
    text = str(value).strip()
    match = TAG.fullmatch(text)
    return f"{match[1].upper()}-{match[2].upper()}" if match else text.upper()


def tags(text):
    return list(
        dict.fromkeys(f"{m[1].upper()}-{m[2].upper()}" for m in TAG.finditer(text))
    )


TYPE_PATTERNS = [
    (re.compile(expression + r"\s*$", re.IGNORECASE), kind)
    for expression, kind in TYPES
]


def classify(descriptions, tag):
    found = set()
    for text in descriptions:
        for hit in TAG.finditer(text):
            if normalize_tag(hit.group()) != tag:
                continue
            candidates = [
                (len(match.group()), kind)
                for pattern, kind in TYPE_PATTERNS
                if (match := pattern.search(text[: hit.start()]))
            ]
            if candidates:
                found.add(max(candidates)[1])
    if len(found) == 1:
        return found.pop(), "Tag-adjacent equipment wording; inferred type."
    return (
        (
            "Review required: conflicting types",
            "Conflicting contextual equipment types.",
        )
        if found
        else ("Unclassified: review required", "No supported type adjacent to tag.")
    )


def build_register(report):
    original_units = [e for e in report.entities if e.kind == "equipment"]
    streams = [e for e in report.entities if e.kind != "equipment"]
    units = {}
    linked_streams = defaultdict(set)
    for entity in streams:
        entity.key = stable_key(
            entity.kind,
            report.sha256,
            entity.id_evidence.sheet,
            entity.table,
            entity.case,
            entity.id_evidence.cell,
        )
    for unit in original_units:
        scope = (unit.id_evidence.sheet, unit.case, normalize_tag(unit.identifier))
        if scope in units:
            units[scope].values.extend([unit.id_evidence, *unit.values])
        else:
            unit.key = stable_key("equipment", report.sha256, *scope)
            unit.stream_keys = []
            units[scope] = unit
    stream_index = defaultdict(list)
    for stream in streams:
        if stream.kind == "material":
            stream_index[
                stream.id_evidence.sheet, stream.case, stream.identifier
            ].append(stream)
    ledger_endpoints = defaultdict(list)
    for (sheet, case, tag), unit in units.items():
        for evidence in unit.values:
            if (
                evidence.property not in ("inlets", "outlets")
                or evidence.original_value is None
            ):
                continue
            text = str(evidence.normalized_value or evidence.original_value).strip()
            references = (
                [text]
                if (sheet, case, text) in stream_index
                else [
                    item.strip() for item in re.split(r"[,;|\n]", text) if item.strip()
                ]
            )
            for reference in references:
                matches = stream_index.get((sheet, case, reference), [])
                if len(matches) != 1:
                    report.issues.append(
                        Issue(
                            code="unresolved_stream_reference",
                            message=f"{sheet}: equipment {unit.identifier} {evidence.property} references unknown or ambiguous stream {reference!r}; no link chosen.",
                            evidence_ids=[evidence.id],
                        )
                    )
                    continue
                role = "destination" if evidence.property == "inlets" else "source"
                ledger_endpoints[matches[0].key].append((role, tag, evidence))
    edges = {}
    for stream in streams:
        if stream.kind != "material":
            continue
        scope = (stream.id_evidence.sheet, stream.case)
        descriptions = [
            v
            for v in stream.values
            if v.property in ("name", "description")
            and isinstance(v.original_value, str)
        ]
        mentions = defaultdict(list)
        candidates = {"source": [], "destination": []}
        for role, tag, evidence in ledger_endpoints[stream.key]:
            candidates[role].append((tag, evidence, "explicit_field"))
        for value in stream.values:
            if (
                value.property in candidates
                and value.original_value is not None
                and clean(value.original_value)
            ):
                endpoint = (
                    value.normalized_value
                    if value.normalized_value is not None
                    else value.original_value
                )
                candidates[value.property].append(
                    (normalize_tag(endpoint), value, "explicit_field")
                )
        for description in descriptions:
            text = str(description.original_value)
            for tag in tags(text):
                mentions[tag].append(description)
            for role, expression in [("source", FROM), ("destination", TO)]:
                matches = expression.findall(text)
                found = list(
                    dict.fromkeys(tag for clause in matches for tag in tags(clause))
                )
                if len(found) == 1:
                    candidates[role].append((found[0], description, "directional_text"))
                elif found:
                    report.issues.append(
                        Issue(
                            code="ambiguous_connection",
                            message=f"{scope[0]}: stream {stream.identifier} has multiple {role} tags; no endpoint chosen.",
                            evidence_ids=[description.id],
                        )
                    )

        def equipment(
            tag, evidence, scope=scope, stream=stream, descriptions=descriptions
        ):
            key = (*scope, tag)
            if key not in units:
                identity = evidence.model_copy(
                    update={
                        "id": stable_key("equipment-evidence", report.sha256, *key),
                        "property": "identifier",
                        "normalized_value": tag,
                        "status": "inferred",
                        "note": "Explicit tag/name from source evidence; not a designed or validated unit.",
                    }
                )
                units[key] = Entity(
                    key=stable_key("equipment", report.sha256, *key),
                    kind="equipment",
                    identifier=tag,
                    case=stream.case,
                    table=stream.table,
                    id_evidence=identity,
                )
                description_text = [str(d.original_value) for d in descriptions]
                kind, basis = classify(description_text, tag)
                units[key].values.append(
                    identity.model_copy(
                        update={
                            "id": stable_key("type", *key),
                            "property": "type",
                            "label": "Equipment type (interpreted)",
                            "normalized_value": kind,
                            "note": basis,
                        }
                    )
                )
            unit = units[key]
            if stream.key not in linked_streams[unit.key]:
                linked_streams[unit.key].add(stream.key)
                unit.stream_keys.append(stream.key)
            return unit

        def edge(
            tag,
            evidence,
            role,
            basis,
            status="inferred",
            stream=stream,
            equipment=equipment,
        ):
            unit = equipment(tag, evidence) if tag is not None else None
            key = stable_key(
                "connection", stream.key, unit.key if unit else None, role, basis
            )
            if key not in edges:
                edges[key] = Connection(
                    key=key,
                    stream_key=stream.key,
                    equipment_key=unit.key if unit else None,
                    role=role,
                    basis=basis,
                    status=status,
                    note="Source-backed relationship for review."
                    if unit
                    else "Endpoint not explicitly identified; not invented.",
                )
            if evidence.id not in edges[key].evidence_ids:
                edges[key].evidence_ids.append(evidence.id)

        for tag, evidence in mentions.items():
            for value in evidence:
                edge(tag, value, "mention", "mention")
        for role, choices in candidates.items():
            unique = {tag for tag, _, _ in choices}
            conflict = len(unique) > 1
            if len(unique) == 1 and not any(v.property == role for v in stream.values):
                tag, evidence, _basis = choices[0]
                stream.values.append(
                    evidence.model_copy(
                        update={
                            "id": stable_key("endpoint", stream.key, role),
                            "property": role,
                            "label": f"Stream {stream.identifier} | {role}",
                            "normalized_value": tag,
                            "status": "inferred",
                            "note": "Resolved from explicit source evidence; relationship requires review.",
                        }
                    )
                )
            if not choices:
                edge(None, stream.id_evidence, role, "missing", "unresolved")
                report.issues.append(
                    Issue(
                        code="unresolved_connection",
                        message=f"{scope[0]}: stream {stream.identifier} {role} endpoint is unresolved.",
                        evidence_ids=[stream.id_evidence.id],
                    )
                )
            elif conflict:
                report.issues.append(
                    Issue(
                        code="conflicting_connection",
                        message=f"{scope[0]}: stream {stream.identifier} has conflicting {role} evidence; alternatives retained.",
                        evidence_ids=list(dict.fromkeys(v.id for _, v, _ in choices)),
                    )
                )
            for tag, evidence, basis in choices:
                # Explicit external boundary labels are preserved on stream records,
                # but do not become fabricated equipment items.
                if clean(tag) in BOUNDARIES:
                    edge(
                        None,
                        evidence,
                        role,
                        basis,
                        "inferred" if not conflict else "unresolved",
                    )
                    continue
                edge(
                    tag, evidence, role, basis, "unresolved" if conflict else "inferred"
                )
    report.entities = [*streams, *units.values()]
    report.connections = list(edges.values())
