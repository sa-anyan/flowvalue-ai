"""Versioned uncertainty jobs reuse the authenticated assessment store and executor."""

import hashlib
from pathlib import Path

from .discovery import discover
from .engine import evaluate, simulate, summarize
from .models import Settings
from .sampling import validate
from .scenarios import apply, prepare


def source_fingerprint():
    roots = [
        "equipment_costing",
        "capex",
        "opex",
        "revenue",
        "financial_modelling",
        "engineering_sizing",
        "equipment_resolution",
    ]
    paths = [p for root in roots for p in (Path("backend") / root).rglob("*.py")]
    paths += [
        Path("backend/orchestration") / name
        for name in (
            "pipeline.py",
            "operating_economics.py",
            "incremental_economics.py",
            "sizing.py",
            "codec.py",
        )
    ]
    paths += [
        Path("backend/scenarios_and_uncertainty/monte_carlo") / name
        for name in (
            "discovery.py",
            "models.py",
            "sampling.py",
            "scenarios.py",
            "engine.py",
        )
    ]
    paths += list(Path("backend/equipment_costing/indexes/garrett/data").glob("*.json"))
    return hashlib.sha256(
        b"".join(str(p).encode() + p.read_bytes() for p in sorted(paths))
    ).hexdigest()


def preflight(state, settings):
    if state.get("running"):
        raise ValueError("Wait for assessment processing before freezing a simulation")
    if (
        settings.baseline_revision is not None
        and settings.baseline_revision != state["revision"]
    ):
        raise ValueError(
            "Assessment changed; rediscover parameters before freezing simulation"
        )
    original = Settings.model_validate(discover(state)["settings"])
    enabled, _ = validate(settings, original)
    plan = prepare(state, settings)
    central = []
    for p in enabled:
        if p.distribution == "discrete":
            central.append(p.choices[p.probabilities.index(max(p.probabilities))])
        elif p.distribution == "uniform":
            central.append(p.minimum + (p.maximum - p.minimum) / 2)
        else:
            central.append(p.mode)
    apply(plan, enabled, central)
    report = (
        state.get("scoped_report")
        or state.get("effective_report")
        or state["parsed"]["report"]
    )
    coverage = evaluate(
        report, state["description"], plan, [a.equipment_key for a in settings.aliases]
    )
    return {k: coverage[k] for k in ("coverage", "unpriced", "issues", "status")}


def start(store, key, settings):
    state = store.get(key)
    coverage = preflight(state, settings)
    snapshot = store.create({"kind": "monte_carlo_snapshot", "assessment": state}, b"")
    job = store.create(
        {
            "kind": "monte_carlo_job",
            "parent_assessment": key,
            "baseline_revision": state["revision"],
            "snapshot_id": snapshot["id"],
            "calculation_source_hash": source_fingerprint(),
            "settings": settings.model_dump(),
            "status": "queued",
            "completed": 0,
            "total": settings.iterations,
            "preflight": {
                k: coverage[k] for k in ("coverage", "unpriced", "issues", "status")
            },
            "summary": None,
        },
        b"",
    )
    return job


def update_job(store, key, patch):
    for attempt in range(3):
        current = store.get(key)
        current.update(patch)
        try:
            return store.put(current, current["revision"])
        except ValueError:
            if attempt == 2:
                raise


def work(store, job_id):
    job = store.get(job_id)
    try:
        state = store.get(job["snapshot_id"])["assessment"]

        def progress(done, total):
            current = update_job(
                store, job_id, {"status": "running", "completed": done, "total": total}
            )
            return not current.get("cancel_requested", False)

        result = simulate(state, Settings.model_validate(job["settings"]), progress)
        result["audit"]["frozen_snapshot_id"] = job["snapshot_id"]
        result["audit"]["calculation_source_hash"] = job.get("calculation_source_hash")
        result["audit"]["source_changed_during_run"] = bool(
            job.get("calculation_source_hash")
            and job["calculation_source_hash"] != source_fingerprint()
        )
        if result["audit"]["source_changed_during_run"]:
            for row in result["runs"]:
                if row["status"] == "complete":
                    row["status"] = "partial"
                row.setdefault("invalid_calculations", []).append(
                    {
                        "stage": "source_version",
                        "issues": [
                            "Calculation library changed during the job; repeat with a fixed version"
                        ],
                    }
                )
            settings = Settings.model_validate(job["settings"])
            result["summary"] = summarize(
                result["runs"], [p for p in settings.parameters if p.enabled], settings
            )
            result["summary"]["source_review_required"] = True
        saved = store.create(
            {"kind": "monte_carlo_results", "source_job": job_id, "result": result}, b""
        )
        current = store.get(job_id)
        current.update(
            status="cancelled" if current.get("cancel_requested") else "complete",
            completed=len(result["runs"]),
            summary=result["summary"],
            result_id=saved["id"],
        )
        store.put(current, current["revision"])
    except Exception as exc:  # noqa: BLE001 -- background boundary always persists failures
        current = store.get(job_id)
        current.update(status="failed", error=str(exc)[:1200])
        store.put(current, current["revision"])


def get_job(store, key, job_id):
    job = store.get(job_id)
    if job.get("kind") != "monte_carlo_job" or job.get("parent_assessment") != key:
        raise KeyError("Simulation not found for this assessment")
    return job


def get_results(store, key, job_id):
    job = get_job(store, key, job_id)
    if not job.get("result_id"):
        raise ValueError("Simulation results are not ready")
    record = store.get(job["result_id"])
    if record.get("source_job") != job_id:
        raise KeyError("Result snapshot mismatch")
    return record["result"]
