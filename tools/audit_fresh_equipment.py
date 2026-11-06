"""Cold equipment-pipeline audit: raw workbook, empty plans, no AI-cache access.

Run from the repository root with the backend Python environment and configured
AI environment variables. Output contains private engineering information; keep
it outside public source control. No production assessment is read or updated.
"""

import argparse
import json
import os
from pathlib import Path

from backend.blocks.execution import run_stage
from backend.orchestration.provider import EngineeringProvider
from backend.orchestration.service import new_assessment
from backend.orchestration.store import Store


class NoCacheStore(Store):
    def cached(self, context, compute):
        return compute(), False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--description-file", type=Path)
    parser.add_argument("--revenue-file", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=1, choices=range(1, 11))
    parser.add_argument(
        "--python-ingestion",
        action="store_true",
        help="Skip optional AI workbook review; still parse raw file and run fresh AI equipment matching/sizing.",
    )
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new output directory; old runs are never reused.")
    args.output.mkdir(parents=True, mode=0o700)
    description = args.description_file.read_text() if args.description_file else ""
    revenue = args.revenue_file.read_text() if args.revenue_file else ""
    provider = EngineeringProvider()
    summaries = []
    for run in range(1, args.runs + 1):
        folder = args.output / f"run-{run}"
        folder.mkdir(mode=0o700)
        store = NoCacheStore(folder / "audit.sqlite3")
        state = new_assessment(
            store, args.workbook.read_bytes(), args.workbook.name, description, revenue
        )
        state["running"] = False
        store.put(state, state["revision"])
        for stage in ("engineering_data", "equipment"):
            print(f"Run {run}: {stage}", flush=True)
            state = run_stage(
                store,
                state["id"],
                stage,
                use_ai=stage == "equipment" or not args.python_ingestion,
                provider=provider,
            )
        (folder / "assessment.json").write_text(json.dumps(state, indent=2))
        result = (state.get("results") or {}).get("stages", {}).get(
            "equipment", {}
        ).get("result") or {}
        equipment = result.get("equipment", [])
        with store.db() as db:
            cache_rows = db.execute("SELECT count(*) FROM ai_cache").fetchone()[0]
        assert cache_rows == 0
        summary = {
            "run": run,
            "priced": sum(r.get("equipment_cost") is not None for r in equipment),
            "total": len(equipment),
            "ai_cache_rows": cache_rows,
            "ai_workbook_review": not args.python_ingestion,
            "unpriced": [
                {"tag": r["equipment_tag"], "issues": r["issues"]}
                for r in equipment
                if r.get("equipment_cost") is None
            ],
        }
        summaries.append(summary)
        print(json.dumps(summary), flush=True)
        (args.output / "summary.json").write_text(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
