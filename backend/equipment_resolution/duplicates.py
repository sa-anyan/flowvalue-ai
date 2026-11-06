"""Reversible register exclusions under the founder's tag/AB convention.

Source registers are never mutated. Only identical normalized tags or a plain
numbered tag with its AB counterpart are combined; semantic similarities are
not evidence of duplication. Restored rows remain separate until re-excluded.
"""

import copy
import re


def token(tag):
    return re.sub(r"[^A-Z0-9]", "", str(tag).upper())


def reconcile(report, plan):
    report, plan = copy.deepcopy(report), copy.deepcopy(plan)
    entities = [e for e in report["entities"] if e.get("kind") == "equipment"]
    rows = {r["equipment_key"]: r for r in plan.get("equipment", [])}
    groups = {}
    for e in entities:
        name = token(e.get("identifier", ""))
        if name:
            groups.setdefault(name, []).append(e)
    destinations = {}
    for name, members in groups.items():
        base_pair = groups.get(name + "AB") if re.search(r"\d$", name) else None
        keeper = (base_pair or members)[0]
        for e in members:
            if e["key"] != keeper["key"]:
                destinations[e["key"]] = (
                    keeper["key"],
                    (
                        "Plain tag represented by AB pair"
                        if base_pair
                        else "Repeated normalized equipment tag"
                    ),
                )
    by_key = {e["key"]: e for e in entities}
    # Resolve exact-duplicate AB rows to the same retained pair.
    for key, (dest, why) in list(destinations.items()):
        seen = {key}
        while dest in destinations and dest not in seen:
            seen.add(dest)
            dest = destinations[dest][0]
        destinations[key] = (dest, why)
    audit, dropped = [], set()
    for key, (dest, reason) in destinations.items():
        e, survivor = by_key[key], by_key[dest]
        restored = rows.get(key, {}).get("duplicate_action") == "restore"
        audit.append(
            {
                "equipment_key": key,
                "tag": e["identifier"],
                "retained_equipment_key": dest,
                "retained_tag": survivor["identifier"],
                "reason": reason,
                "status": "restored" if restored else "dropped",
                "source": e.get("id_evidence"),
                "stream_keys": e.get("stream_keys", []),
                "notice": "User-defined tag convention; not independently verified physical identity.",
            }
        )
        if restored:
            continue
        dropped.add(key)
        survivor["stream_keys"] = list(
            dict.fromkeys(survivor.get("stream_keys", []) + e.get("stream_keys", []))
        )
        existing = {v.get("id") for v in survivor.get("values", [])}
        survivor.setdefault("values", []).extend(
            v for v in e.get("values", []) if v.get("id") not in existing
        )
        survivor.setdefault("duplicate_source_keys", []).append(key)
    report["entities"] = [e for e in report["entities"] if e["key"] not in dropped]
    connections = []
    for c in report.get("connections", []):
        if c.get("equipment_key") in dropped:
            c = {
                **c,
                "original_equipment_key": c["equipment_key"],
                "equipment_key": destinations[c["equipment_key"]][0],
                "status": "user_tag_convention_reference",
            }
        connections.append(c)
    report["connections"] = connections
    return report, plan, audit
