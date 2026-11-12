"""G3 review entry point: reproduce the evidence in G3_gate_review_2026-11-12.md.

Run from the repository root:

    python docs/verification/phase3/g3_review/reproduce_g3.py
    python docs/verification/phase3/g3_review/reproduce_g3.py --study PATH.sqlite3 --assessment KEY

Without --study it runs the G3 test files and the catalogue checks. With a
saved study (for example Charlie or Team 8) it copies the database to a
temporary folder, re-prices equipment and CAPEX there without AI, and builds
the Basis of Estimate. The original database is never written. Output is
counts, ratios and check results only: no sizes, prices or other study values.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

TESTS = {
    "T3-2 duplicate tags": ["backend/tests/test_fresh_equipment_audit.py"],
    "T3-2 missing equipment, unpriced never zero": ["backend/tests/test_total_equipment_cost.py"],
    "T3-2 historical cost years and escalation": ["backend/tests/test_cost_translation.py", "backend/tests/test_cepci_series.py"],
    "T3-2/T3-4 installed vs purchased, no double count": ["backend/tests/test_installation_costs.py", "backend/tests/test_capex_scope.py"],
    "M3.2 Garrett corrections": ["backend/tests/test_garrett_c01_corrections.py"],
    "M3.7 library preference and user model choice": ["backend/tests/test_library_preference.py"],
    "CHARLIE-COV03 minimum-size floor": ["backend/tests/test_below_range_floor.py"],
    "M3.5 estimate class": ["backend/tests/test_estimate_class.py"],
    "M3.6 Basis of Estimate": ["backend/tests/test_basis_of_estimate.py"],
    "M3.7 coverage tiers and unpriced significance": ["backend/tests/test_coverage_tiers.py"],
}

REQUIRED_FIELDS = {
    "openpytea": ["cost_scope", "source_year", "currency", "reference", "equation_family"],
    "nottingham": ["source_year", "currency", "source", "source_page"],
    "additional_models": ["cost_scope", "source_year", "currency", "reference", "source_page"],
    "garrett": ["pdf_page", "printed_page", "size_unit"],  # scope, USD, CE 320 and early 1987 are fixed in code
}


def run_tests():
    results = {}
    for label, files in TESTS.items():
        missing = [f for f in files if not (ROOT / f).exists()]
        if missing:
            results[label] = {"status": "MISSING", "files": missing}
            continue
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *files],
            cwd=ROOT, capture_output=True, text=True,
        )
        tail = (proc.stdout.strip().splitlines() or [""])[-1]
        results[label] = {"status": "PASS" if proc.returncode == 0 else "FAIL", "summary": tail}
    return results


def _library(model_id):
    if model_id.startswith("openpytea:"):
        return "openpytea"
    if model_id.startswith("N501"):
        return "nottingham"
    if model_id[:1] == "G" and model_id[1:2].isdigit():
        return "garrett"
    return "additional_models"


def catalogue_checks():
    from backend.equipment_costing.cost_to_future.cost_translation import catalogue
    from backend.equipment_costing.registry import list_equipment_models

    models = list_equipment_models(source="all")
    by_library = Counter()
    missing = Counter()
    for m in models:
        lib = _library(m["id"])
        by_library[lib] += 1
        for field in REQUIRED_FIELDS[lib]:
            if m.get(field) in (None, "", []):
                missing[f"{lib}.{field}"] += 1
    cepci = catalogue()["series"].get("CEPCI", {})
    uncited = [y for y, p in cepci.get("observations", {}).items() if not p.get("source")]
    garrett_status = Counter(m.get("review_status") for m in models if _library(m["id"]) == "garrett")
    return {
        "models": len(models),
        "by_library": dict(by_library),
        "missing_required_fields": dict(missing),
        "A2_status": "PASS" if not missing else "FAIL",
        "garrett_review_status": dict(garrett_status),
        "cepci_observations": len(cepci.get("observations", {})),
        "cepci_uncited": uncited,
        "cepci_has_2025_or_2026": any(y.startswith(("2025", "2026")) for y in cepci.get("observations", {})),
    }


def study_checks(db, key):
    from backend.blocks.execution import run_stage, view
    from backend.dashboard_reporting.basis_of_estimate import build_basis_of_estimate
    from backend.orchestration.store import Store

    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "study.sqlite3"
        shutil.copy2(db, copy)
        store = Store(copy)
        state = store.get(key)
        if not (state.get("plan") or {}).get("capex"):
            return {"status": "NOT_RUN", "reason": "Study has no CAPEX settings; set them in the app first"}
        for stage in ("equipment", "capex"):
            state = run_stage(store, key, stage)
            if state["stage_runs"][stage].get("status") != "ready":
                return {"status": "NOT_RUN", "stage": stage, "detail": state["stage_runs"][stage].get("message")}
        boe = build_basis_of_estimate(view(store.get(key)))
    rows = boe["scope"]["priced_equipment"]
    flags = lambda r: " ".join(r["flags"])  # noqa: E731
    items = len(rows) + len(boe["scope"]["unpriced_equipment"])
    floored = sum("minimum-size floor" in flags(r) for r in rows)
    extrapolated = sum("extrapolated" in flags(r) for r in rows)
    user = sum("user comparable" in flags(r) for r in rows)
    in_range = len(rows) - floored - extrapolated - user
    totals = boe["totals"]
    e = Decimal(totals["purchased_equipment"])
    return {
        "status": "RUN",
        "items": items,
        "coverage": {
            "priced_any_method": len(rows), "source_supported_in_range": in_range,
            "minimum_size_floor": floored, "extrapolated": extrapolated, "user_comparable": user,
            "unpriced": len(boe["scope"]["unpriced_equipment"]),
            "priced_fraction": round(len(rows) / items, 3) if items else None,
            "in_range_fraction": round(in_range / items, 3) if items else None,
        },
        "tiers_m3_7": {
            name: {"items": t["items"], "fraction_of_items": t["fraction_of_items"],
                   "fraction_of_priced_value": t["fraction_of_priced_value"]}
            for name, t in boe["coverage"]["tiers"]["tiers"].items()
        },
        "assumption_kinds": boe["coverage"]["tiers"]["assumption_kinds"],
        "meets_target_without_assumptions": boe["coverage"]["tiers"]["meets_coverage_target_without_assumptions"],
        "unpriced_significance": {
            k: boe["coverage"]["unpriced_significance"].get(k)
            for k in ("status", "significance", "share_of_priced_equipment")
        },
        "escalation": boe["price_basis"]["escalation_by_status"],
        "double_count_checks": {c["id"]: c["passed"] for c in boe["checks"]["double_count"]},
        "reconciliation": boe["checks"]["reconciliation"]["status"],
        "estimate_class": {k: boe["estimate_class"].get(k) for k in ("proposed_class", "status")},
        "fixed_capital_to_equipment": str(round(Decimal(totals["fixed_capital"]) / e, 2)) if totals.get("fixed_capital") else None,
        "categories_without_source": boe["exclusions_and_gaps"]["categories_without_source"],
        "open_items": len(boe["open_items"]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--study", type=Path)
    parser.add_argument("--assessment")
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()
    out = {"catalogue": catalogue_checks()}
    if not args.skip_tests:
        out["tests"] = run_tests()
    if args.study:
        if not args.assessment:
            parser.error("--assessment is required with --study")
        out["study"] = study_checks(args.study, args.assessment)
    print(json.dumps(out, indent=2, default=str))
    failed = [k for k, v in out.get("tests", {}).items() if v["status"] != "PASS"]
    return 1 if failed or out["catalogue"]["A2_status"] != "PASS" else 0


if __name__ == "__main__":
    sys.exit(main())
