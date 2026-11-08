"""Cold equipment-pipeline audit: raw workbook, empty plans, no AI-cache access.

Run from the repository root with the backend Python environment and configured
AI environment variables. Output contains private engineering information; keep
it outside public source control. No production assessment is read or updated.
"""

import hashlib
import subprocess
import time
import argparse
import json
import os
import sys
from threading import Event
from concurrent.futures import ThreadPoolExecutor, as_completed
from math import isfinite
from pathlib import Path
from contextlib import contextmanager, ExitStack
from unittest.mock import patch

from backend.blocks.execution import run_stage
from backend.equipment_costing.models import priced_record
from backend.orchestration.provider import EngineeringProvider
from backend.orchestration.service import new_assessment
from backend.orchestration.store import Store


class NoCacheStore(Store):
    def cached(self, context, compute):
        return compute(), False


@contextmanager
def equipment_source_policy(source):
    """Audit-only allowlist: same pipeline, no alternate production engine."""
    if source == "all":
        yield
        return
    if source != "openpytea":
        raise ValueError("Unsupported audit equipment source")
    from backend.equipment_costing import registry
    from backend.equipment_matching import service as matching
    from backend.equipment_costing.unit_conversion.bridges import service, automatic

    original_list, original_model = registry.list_equipment_models, registry._model

    def restricted_list(source="garrett"):
        return original_list("openpytea") if source in {"all", "openpytea"} else []

    def restricted_model(model_id, requested):
        if not str(model_id).startswith("openpytea:"):
            raise ValueError("Audit source policy blocks non-OpenPyTEA equipment model")
        return original_model(model_id, requested)

    def blocked_cost(*args, **kwargs):
        raise ValueError("Audit source policy blocks non-OpenPyTEA equipment costing")

    with ExitStack() as stack:
        for module in (registry, matching, service, automatic):
            stack.enter_context(
                patch.object(module, "list_equipment_models", restricted_list)
            )
        stack.enter_context(patch.object(registry, "_model", restricted_model))
        for name in ("_garrett_cost", "_additional_cost", "_nottingham_cost"):
            stack.enter_context(patch.object(registry, name, blocked_cost))
        yield


class AuditProvider(EngineeringProvider):
    """Record fresh calls for diagnosis, never replay or read a previous response."""

    def __init__(self, folder):
        super().__init__()
        self.audit = {"folder": folder, "count": 0}

    def generate(self, *, instructions, context, schema):
        index = self.audit["count"]
        self.audit["count"] += 1
        started = time.monotonic()
        print(
            f"  AI call {index}: {context.get('task', context.get('specialist', context.get('requested_sections', 'review')))}",
            flush=True,
        )
        record = {
            "instructions": instructions,
            "context": context,
            "schema": schema,
            "model": self.model,
            "cache": "bypassed",
        }
        try:
            result = super().generate(
                instructions=instructions, context=context, schema=schema
            )
            record["response"] = result
            return result
        except Exception as exc:
            record["error"] = str(exc)
            print(f"  AI call {index} failed: {type(exc).__name__}: {exc}", flush=True)
            raise
        finally:
            record["elapsed_seconds"] = time.monotonic() - started
            (self.audit["folder"] / f"call-{index:03d}.json").write_text(
                json.dumps(record, indent=2)
            )


def pricing_checks(equipment):
    """Numerical/inventory checks, not proof of engineering model suitability."""
    issues = []
    seen = set()
    for row in equipment:
        tag = row["equipment_tag"]
        if tag in seen:
            issues.append(f"{tag}: duplicate output tag")
        seen.add(tag)
        if not priced_record(row):
            continue
        for field in ("amount", "quantity"):
            value = row.get(field)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                or value <= 0
            ):
                issues.append(f"{tag}: invalid {field}")
        if str(tag).upper().endswith("AB") and row.get("quantity") != 2:
            issues.append(
                f"{tag}: AB quantity is not two; review explicit quantity basis"
            )
    return issues


def code_fingerprint():
    names = subprocess.check_output(
        ["git", "ls-files", "backend"], text=True
    ).splitlines()
    digest = hashlib.sha256()
    for name in sorted(names):
        path = Path(name)
        if (
            path.is_file()
            and path.suffix in {".py", ".json", ".csv"}
            and "/tests/" not in name
        ):
            digest.update(name.encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def parallel_runs(args, fingerprint):
    """Independent OS processes and databases; threads only supervise children."""
    stop = Event()

    def run_one(number):
        if stop.is_set() or (args.output / "STOP").exists():
            return {
                "run": number,
                "not_run": True,
                "reason": "Campaign stopped; not an acceptance pass",
            }
        if code_fingerprint() != fingerprint:
            return {"run": number, "error": "Code changed; acceptance version ended"}
        output = args.output / f"replicate-{number:03d}"
        command = [
            sys.executable,
            "-m",
            "tools.audit_fresh_equipment",
            str(args.workbook),
            "--output",
            str(output),
        ]
        for flag, value in (
            ("--description-file", args.description_file),
            ("--revenue-file", args.revenue_file),
        ):
            if value:
                command.extend([flag, str(value)])
        if args.python_ingestion:
            command.append("--python-ingestion")
        command.extend(["--equipment-source", args.equipment_source])
        with (args.output / f"replicate-{number:03d}.log").open("w") as log:
            process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        summary_path = output / "summary.json"
        if process.returncode or not summary_path.exists():
            if args.stop_on_incomplete:
                stop.set()
            return {
                "run": number,
                "error": "Audit process failed",
                "exit_code": process.returncode,
            }
        result = json.loads(summary_path.read_text())[0]
        result["run"] = number
        if args.stop_on_incomplete and (
            not result.get("total")
            or result.get("priced") != result.get("total")
            or result.get("numerical_inventory_issues")
            or not result.get("code_unchanged")
            or any(
                b.get("status") != "reviewed"
                for b in result.get("engineering_review", {})
                .get("review", {})
                .get("batches", [])
            )
        ):
            stop.set()
        return result

    summaries = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = [pool.submit(run_one, i) for i in range(1, args.runs + 1)]
        for completed in as_completed(pending):
            summaries.append(completed.result())
            summaries.sort(key=lambda row: row["run"])
            (args.output / "summary.json").write_text(json.dumps(summaries, indent=2))
            row = completed.result()
            print(
                json.dumps(
                    {
                        key: row.get(key)
                        for key in ("run", "priced", "total", "unpriced", "error")
                    }
                ),
                flush=True,
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--description-file", type=Path)
    parser.add_argument("--revenue-file", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=1, choices=range(1, 1001))
    parser.add_argument(
        "--equipment-source", choices=["all", "openpytea"], default="all"
    )
    parser.add_argument(
        "--stop-on-incomplete",
        action="store_true",
        help="Stop queued runs after an incomplete result; retain failures and in-flight results.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        choices=range(1, 9),
        help="Bounded independent cold-run processes; no response sharing.",
    )
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
    os.environ["FLOWVALUE_AI_RESPONSE_CACHE"] = "false"
    fingerprint = code_fingerprint()
    if args.workers > 1:
        parallel_runs(args, fingerprint)
        return
    source_hash = hashlib.sha256(args.workbook.read_bytes()).hexdigest()
    summaries = []
    for run in range(1, args.runs + 1):
        folder = args.output / f"run-{run}"
        folder.mkdir(mode=0o700)
        if code_fingerprint() != fingerprint:
            raise RuntimeError(
                "Code changed during acceptance; start a new versioned audit"
            )
        provider = AuditProvider(folder)
        started = time.monotonic()
        store = NoCacheStore(folder / "audit.sqlite3")
        state = new_assessment(
            store, args.workbook.read_bytes(), args.workbook.name, description, revenue
        )
        state["running"] = False
        store.put(state, state["revision"])
        with equipment_source_policy(args.equipment_source):
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
            "equipment_source_policy": args.equipment_source,
            "run": run,
            "priced": sum(priced_record(r) for r in equipment),
            "elapsed_seconds": time.monotonic() - started,
            "fresh_ai_calls": provider.audit["count"],
            "code_fingerprint": fingerprint,
            "code_unchanged": code_fingerprint() == fingerprint,
            "workbook_sha256": source_hash,
            "engineering_review": state.get("ai", {}),
            "scope_review_pending": [
                d
                for d in state.get("recoveries", [])
                if d.get("status") == "pending_process_scope"
            ],
            "inventory_tags": sorted(r["equipment_tag"] for r in equipment),
            "drops": result.get("duplicate_review", []),
            "prices": [
                {
                    "tag": r["equipment_tag"],
                    "amount": r.get("amount"),
                    "scope": r.get("cost_scope"),
                    "model": r.get("curve_id"),
                    "quantity": r.get("quantity"),
                    "size": (
                        (r.get("calculation") or {}).get("estimate", {}).get("size")
                        if (r.get("calculation") or {}).get("estimate")
                        else None
                    ),
                    "issues": r.get("issues", []),
                }
                for r in equipment
            ],
            "total": len(equipment),
            "ai_cache_rows": cache_rows,
            "ai_workbook_review": not args.python_ingestion,
            "unpriced": [
                {"tag": r["equipment_tag"], "issues": r["issues"]}
                for r in equipment
                if not priced_record(r)
            ],
            "numerical_inventory_issues": pricing_checks(equipment),
        }
        summaries.append(summary)
        if args.equipment_source == "openpytea":
            assert all(
                str(r.get("curve_id", "")).startswith("openpytea:")
                for r in equipment
                if priced_record(r)
            ), "Non-OpenPyTEA cost escaped audit allowlist"
        print(json.dumps(summary), flush=True)
        (args.output / "summary.json").write_text(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
