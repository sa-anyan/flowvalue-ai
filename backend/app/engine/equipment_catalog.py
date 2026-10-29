"""Source-linked equipment-name matching, independent of sizing and cost calculations.

No tag-prefix inference, model calls, process reconstruction or baseline mutation.
A name match does not establish suitability of a historical cost curve.
"""

import json
import re
import sqlite3
import unicodedata
from functools import lru_cache
from importlib.resources import files

from fastapi import APIRouter

from app.parsers.balance.models import BalanceReport

router = APIRouter(prefix="/api/equipment", tags=["Equipment catalog"])


@lru_cache(maxsize=4096)
def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).casefold().replace("&", " and ")
    tokens = re.findall(r"[a-z0-9]+", text)
    # Engineering naming variants; no stemming that could turn a tag into a type.
    irregular = {
        "centrifuges": "centrifuge",
        "vessels": "vessel",
        "batteries": "battery",
    }
    return " ".join(
        irregular.get(
            t, t[:-1] if t.endswith("s") and not t.endswith(("ss", "gas")) else t
        )
        for t in tokens
    )


@lru_cache(maxsize=1)
def catalog():
    path = files("app.data").joinpath("equipment_catalog.sqlite3")
    with sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        version, source = db.execute(
            "SELECT version, source_json FROM metadata"
        ).fetchone()
        records = [
            dict(row) for row in db.execute("SELECT * FROM equipment ORDER BY pdf_page")
        ]
        sources = [
            json.loads(r[0])
            for r in db.execute("SELECT source_json FROM sources ORDER BY id")
        ]
        for row in records:
            row["source_refs"] = [
                dict(r)
                for r in db.execute(
                    "SELECT source_id, pdf_page, printed_page FROM equipment_sources WHERE equipment_id=? ORDER BY source_id",
                    (row["id"],),
                )
            ]
            row["aliases"] = [
                r[0]
                for r in db.execute(
                    "SELECT alias FROM aliases WHERE equipment_id=?", (row["id"],)
                )
            ]
    return {
        "version": version,
        "source": json.loads(source),
        "sources": sources,
        "equipment": records,
    }


# Broad terms can suggest a family but cannot select a historical subtype chart.
FAMILIES = {
    "pump": "pump",
    "compressor": "compressor",
    "heat exchanger": "heat exchanger",
    "exchanger": "heat exchanger",
    "mill": "mill",
    "crusher": "mill",
    "press": "press",
    "bioreactor": "reactor",
    "fermenter": "reactor",
    "fermentor": "reactor",
    "settler": "settler",
    "sedimentation tank": "settler",
    "classifier": "classifier",
    "adsorber": "adsorber",
    "cooler": "cooler",
    "screen": "screen",
    "column": "column",
    "absorption column": "column",
}


def contains(text, phrase):
    return f" {normalize(phrase)} " in f" {normalize(text)} "


def equipment_context(text: str, tag: str, explicit: bool) -> str:
    # Only the clause immediately naming this tag; never borrow an upstream unit's type.
    found = re.search(
        r"(?<![\w-])" + re.escape(tag) + r"(?![\w-])", text, re.IGNORECASE
    )
    if not found:
        return text if explicit else ""
    before = text[: found.start()]
    clause = re.split(
        r"\b(?:to|from|into|through|then)\b|[;|\n]", before, flags=re.IGNORECASE
    )[-1].strip()
    previous_tags = list(re.finditer(r"\b[A-Z]{1,5}[- ]?\d{2,5}\b", clause))
    if previous_tags:
        clause = clause[previous_tags[-1].end() :].strip(" ,:")
    # Support "P-101: centrifugal pump" as well as "centrifugal pump P-101".
    if not clause:
        after = text[found.end() :].lstrip(" :–—-")
        clause = re.split(
            r"\b(?:to|from|into|through)\b|[;|\n]", after, flags=re.IGNORECASE
        )[0]
    return clause[-160:]


def match_report(report: BalanceReport):
    data = catalog()
    by_key = {entity.key: entity for entity in report.entities}
    results = []
    for unit in report.entities:
        if unit.kind != "equipment":
            continue
        observations = list(unit.values)
        for key in unit.stream_keys:
            stream = by_key.get(key)
            if stream is not None and stream.kind == "material":
                observations.extend(
                    v for v in stream.values if v.property in ("description", "name")
                )
        hits, families, used, contexts = set(), set(), {}, []
        for value in observations:
            if value.property not in (
                "type",
                "equipment_type",
                "description",
                "name",
            ) or not isinstance(value.original_value, str):
                continue
            context = equipment_context(
                value.original_value,
                unit.identifier,
                value in unit.values
                and value.property in ("type", "equipment_type", "name"),
            )
            if not context or re.search(
                r"\b(?:no|not|without)\b", context, re.IGNORECASE
            ):
                continue
            aliases = [
                (item, alias)
                for item in data["equipment"]
                for alias in item["aliases"]
                if contains(context, alias)
            ]
            # Prefer "small tank" over "tank", "waste heat boiler" over "boiler".
            aliases = [
                (item, a)
                for item, a in aliases
                if not any(
                    normalize(a) != normalize(b) and contains(b, a) for _, b in aliases
                )
            ]
            exact_ids = {item["id"] for item, _ in aliases}
            hits.update(exact_ids)
            context_families = {
                family for alias, family in FAMILIES.items() if contains(context, alias)
            }
            # An explicit subtype already resolves its family. Keep unrelated families as conflicts.
            context_families -= {item["family"] for item, _ in aliases}
            families.update(context_families)
            if exact_ids or context_families:
                used[
                    (value.workbook, value.sheet, value.cell, value.original_value)
                ] = value.model_dump()
                contexts.append(context)
        candidates = {
            item["id"]: item
            for item in data["equipment"]
            if item["id"] in hits or item["family"] in families
        }
        if len(hits) == 1 and not families:
            status, reason = (
                "match",
                "Equipment name/alias found in source evidence. Chart applicability still requires engineering review.",
            )
        elif candidates:
            status, reason = (
                "review",
                "Family-level or conflicting descriptions; confirm equipment type before selecting a chart.",
            )
        else:
            status, reason = (
                "no_match",
                "No supported equipment name found. Tags alone do not establish equipment type.",
            )
        results.append(
            {
                "equipment_key": unit.key,
                "tag": unit.identifier,
                "sheet": unit.id_evidence.sheet,
                "case": unit.case,
                "status": status,
                "reason": reason,
                "descriptions": list(dict.fromkeys(contexts)),
                "candidates": list(candidates.values()),
                "evidence": list(used.values()),
                "tag_source": unit.id_evidence.model_dump(),
            }
        )
    return {
        "catalog_version": data["version"],
        "catalog_count": len(data["equipment"]),
        "source": data["source"],
        "sources": data["sources"],
        "results": results,
        "notice": "Name matching only. Cost curves are not digitized; a catalog match does not calculate or approve a cost.",
    }


@router.get("/catalog")
def get_catalog():
    return catalog()


@router.post("/match")
def match_equipment(report: BalanceReport):
    return match_report(report)
