"""Layout-backed provisional scope when applicability was confused with validation.

Only recover one uniquely dominant stream-table sheet; never merge ambiguous cases.
An active source is intended process data, not a verified balance.
"""

from collections import Counter

from .workbook_scope import calculation_scope


def recover(report):
    counts = Counter(
        e["id_evidence"]["sheet"]
        for e in report["entities"]
        if e["kind"] == "material"
        and any(
            v["property"] == "mass_flow" and v.get("normalized_value") is not None
            for v in e["values"]
        )
    )
    ranked = counts.most_common()
    if (
        not ranked
        or ranked[0][1] < 2
        or (len(ranked) > 1 and ranked[0][1] < 2 * ranked[1][1])
    ):
        raise ValueError(
            "Active process scope remains ambiguous; no uniquely dominant stream-table sheet"
        )
    primary = ranked[0][0]
    decisions = [
        {
            "sheet": s["name"],
            "role": "active" if s["name"] == primary else "supporting",
            "needed_entity_keys": [],
            "rationale": "Provisional source applicability from uniquely dominant explicit stream-total register; not balance verification. Supporting data retained outside cost scope until linked.",
        }
        for s in report["sheets"]
    ]
    scoped = calculation_scope(report, decisions)
    scoped["scope_recovery"] = {
        "status": "inferred_review_required",
        "primary_sheet": primary,
        "basis": dict(counts),
        "notice": "Layout-backed provisional scope; confirm intended worksheets. No engineering balance was certified.",
    }
    return scoped
