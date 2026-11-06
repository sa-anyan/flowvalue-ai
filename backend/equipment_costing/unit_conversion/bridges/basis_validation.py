"""Reject incompatible quantity roles without rewriting workbook observations."""

import re


def validate_bulk_liquid_basis(report, equipment_key, source, method):
    if method not in {"vessel_volume", "mixing_power"}:
        return
    bykey = {e["key"]: e for e in report["entities"]}
    equipment = bykey.get(equipment_key, {})
    names = " ".join(
        str(v.get("normalized_value") or v.get("original_value") or "")
        for v in equipment.get("values", [])
        if v.get("property") in {"name", "type", "description"}
    )
    if not re.search(r"bioreactor|ferment", names, re.I):
        return
    stream = bykey.get(source.get("entity_key"), {})
    description = " ".join(
        str(v.get("normalized_value") or v.get("original_value") or "")
        for v in stream.get("values", [])
        if v.get("property") in {"description", "name", "phase"}
    )
    gas_feed = re.search(
        r"\b(?:gas|vapour|vapor|oxygen|o2|hydrogen|h2|carbon dioxide|co2|nitrogen|n2|air)\b",
        description,
        re.I,
    )
    bulk_liquid = re.search(
        r"\b(?:broth|slurry|culture|solution|water|liquid)\b", description, re.I
    )
    if gas_feed and not bulk_liquid:
        raise ValueError(
            "Bioreactor liquid hold-up/mixing cannot use a gas-reactant feed as total broth throughput. Supply a broth/liquid inventory basis or a separately justified reactor design method."
        )
