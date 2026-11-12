"""G4 review entry point: reproduce the evidence in G4_gate_review_2026-11-12.md.

Run from the repository root:

    python docs/verification/phase4/g4_review/reproduce_g4.py
    python docs/verification/phase4/g4_review/reproduce_g4.py --study PATH.sqlite3 --assessment KEY

Without --study it runs the G4 test groups. With a saved study that has been
run through finance, it copies the database to a temporary folder, re-runs
every stage twice without AI, compares the output fingerprints, and builds
the financial workbook. The original database is never written. Output is
statuses, counts and check results only: no prices, quantities or metrics.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

TESTS = {
    "Roadmap Phase 4 test list, M4.1, M4.3, double-count reviews": ["backend/tests/test_phase4_acceptance.py"],
    "M4.2 Revenue Box authority": ["backend/tests/test_revenue_authority.py", "backend/tests/test_revenue_preflight.py"],
    "M4.2 six-category payments": ["backend/tests/test_revenue_mece.py", "backend/tests/test_revenue.py"],
    "M4.1 OPEX ledger": ["backend/tests/test_opex.py", "backend/tests/test_opex_cost_register.py"],
    "M4.3 schedules and cash-flow phasing": ["backend/tests/test_cashflow_schedule.py", "backend/tests/test_cashflow_cost_phasing.py"],
    "M4.5 financial engine": ["backend/tests/test_financial_modelling.py", "backend/tests/test_cashflow_break_even.py"],
    "M4.5 connected stages": ["backend/tests/test_stage_connections.py"],
    "M4.6 reconciled workbook": ["backend/tests/test_financial_workbook.py"],
}
STAGES = ("equipment", "capex", "revenue", "opex", "financial")


def run_tests():
    results = {}
    for label, files in TESTS.items():
        missing = [f for f in files if not (ROOT / f).exists()]
        if missing:
            results[label] = {"status": "MISSING", "files": missing}
            continue
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *files],
                              cwd=ROOT, capture_output=True, text=True)
        tail = (proc.stdout.strip().splitlines() or [""])[-1]
        results[label] = {"status": "PASS" if proc.returncode == 0 else "FAIL", "summary": tail}
    return results


def study_checks(db, key):
    from backend.blocks.execution import run_stage, view
    from backend.dashboard_reporting.financial_workbook import build_financial_workbook
    from backend.orchestration.store import Store

    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "study.sqlite3"
        shutil.copy2(db, copy)
        store = Store(copy)
        hashes = []
        for _ in range(2):
            for stage in STAGES:
                state = run_stage(store, key, stage)
                status = state["stage_runs"][stage].get("status")
                if status != "ready":
                    return {"status": "NOT_RUN", "stage": stage, "stage_status": status,
                            "detail": (state["stage_runs"][stage].get("message") or "")[:300]}
            runs = store.get(key)["stage_runs"]
            hashes.append({s: runs[s].get("output_hash") for s in STAGES})
        state = view(store.get(key))
        _, workbook = build_financial_workbook(state)
        financial = state["results"]["stages"]["financial"]["result"]
        opex_years = state["results"]["stages"]["opex"]["result"]["years"]
        first = sorted(opex_years, key=int)[0]
        lines = opex_years[first]["lines"]
        user_lines = [l for l in lines if str(l["id"]).startswith(("feed:", "energy:", "staff:", "other:"))]
    return {
        "status": "RUN",
        "stage_status": {s: state["results"]["stages"][s].get("status") for s in STAGES},
        "reproducible_without_ai": hashes[0] == hashes[1],
        "financial_issues": len(financial.get("issues") or []),
        "metrics_calculated": sum(1 for _, m in financial["metrics"] if m.get("status") == "calculated"),
        "metrics_total": len(financial["metrics"]),
        "workbook": {k: workbook[k] for k in ("checks", "numbers_written", "reconciled")}
        | {"checks_failed": len(workbook["checks_failed"]), "readback_mismatches": len(workbook["readback_mismatches"])},
        "opex_lines_with_payment_owner": sum(any(str(e).startswith("payment owner: ") for e in l.get("evidence") or []) for l in user_lines),
        "opex_user_lines": len(user_lines),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--study", type=Path)
    parser.add_argument("--assessment")
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()
    out = {}
    if not args.skip_tests:
        out["tests"] = run_tests()
    if args.study:
        if not args.assessment:
            parser.error("--assessment is required with --study")
        out["study"] = study_checks(args.study, args.assessment)
    print(json.dumps(out, indent=2, default=str))
    failed = [k for k, v in out.get("tests", {}).items() if v["status"] != "PASS"]
    study = out.get("study") or {}
    bad = study and (study.get("status") != "RUN" or not study.get("reproducible_without_ai")
                     or not study["workbook"]["reconciled"])
    return 1 if failed or bad else 0


if __name__ == "__main__":
    sys.exit(main())
