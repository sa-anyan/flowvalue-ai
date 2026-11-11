"""Repeatable local catalogue audit; no network or AI calls."""

import csv, json, math
from collections import Counter
from pathlib import Path
from .registry import ROOT, list_models
from .evaluators import evaluate


def representative(row, prefix="s"):
    lo = float(row[prefix + "_lower"]) if row[prefix + "_lower"] else None
    hi = float(row[prefix + "_upper"]) if row[prefix + "_upper"] else None
    if lo is not None and hi is not None:
        return math.sqrt(lo * hi) if lo > 0 else hi / 2
    return float(row.get("s0") or 1) if prefix == "s" else 1.0


def audit():
    models = list_models()
    records = []
    for m in models:
        row = m["raw"]
        try:
            amount = evaluate(
                row,
                representative(row),
                representative(row, "s2") if row["form"] == "2-var power-law" else None,
                allow_missing_bounds=True,
            )
            mathematical = "pass"
        except (ValueError, OverflowError, TypeError) as exc:
            mathematical = str(exc)
            amount = None
        records.append(
            {
                "model_id": m["id"],
                "key": m["upstream_key"],
                "category": m["category"],
                "mathematical_validation": mathematical,
                "representative_cost": amount,
                "complete_metadata": not m["issues"] and not m["disabled_reasons"],
                "status": m["status"],
                "issues": m["issues"],
                "disabled_reasons": m["disabled_reasons"],
                "input_requirements": m["input_requirements"],
                "sizing_status": m["sizing_status"],
                "cost_scope": m["cost_scope"],
                "year": m["source_year"],
                "reference": m["reference"],
            }
        )
    return {
        "source": json.loads((ROOT / "sources.json").read_text(encoding="utf-8")),
        "counts": {
            "imported": len(models),
            "categories": len({m["category"] for m in models}),
            "mathematically_valid_representative": sum(
                r["mathematical_validation"] == "pass" for r in records
            ),
            "rejected_rows": 0,
            "disabled": sum(m["status"] == "disabled" for m in models),
            "available_provisional": sum(m["status"] != "disabled" for m in models),
            "complete_metadata": sum(r["complete_metadata"] for r in records),
            "automatically_sizeable_without_project_data": 0,
            "dimensionally_supported_measurement_or_assumption": sum(
                m["sizing_status"] != "manual_coordinate_required" for m in models
            ),
            "manual_composite_coordinate_required": sum(
                m["sizing_status"] == "manual_coordinate_required" for m in models
            ),
            "two_variable": sum(len(m["input_requirements"]) == 2 for m in models),
            "missing_first_coordinate_bounds": sum(
                not m["raw"]["s_lower"] or not m["raw"]["s_upper"] for m in models
            ),
        },
        "forms": dict(Counter(m["equation_family"] for m in models)),
        "notice": "Mathematical validation and availability are distinct from engineering applicability and automatic sizing. Counts overlap. No project data was guessed; all sizing requires measurements or explicit assumptions. Disabled rows remain visible.",
        "models": records,
    }


if __name__ == "__main__":
    report = audit()
    (ROOT / "catalogue_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["counts"], indent=2))
