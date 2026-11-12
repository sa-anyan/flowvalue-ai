"""M5.7 run-to-run variance of AI equipment matching (uncached, repeated runs).

``agreement(runs)`` compares per-item decisions from several runs of the same
study and inputs. ``measure(db, key, runs)`` performs the runs on a temporary
copy with the response cache off and returns counts only. Live runs call the
configured AI model and cost money; run them deliberately.
"""

import os
import shutil
import tempfile
from collections import Counter
from pathlib import Path

FIELDS = ("selected_model_id", "match_status")


def decisions(equipment_result):
    """{equipment_tag: (selected_model_id, match_status)} from a saved equipment result."""
    out = {}
    for line in equipment_result.get("equipment") or []:
        match = (line.get("decision") or {}).get("conceptual_matching") or {}
        out[line.get("equipment_tag")] = (line.get("curve_id"), match.get("match_status"))
    return out


def agreement(runs):
    """Per-item agreement across runs: share of runs giving the most common decision."""
    if len(runs) < 2:
        raise ValueError("Variance needs at least two runs")
    tags = sorted(set().union(*runs))
    per_item = {}
    for tag in tags:
        votes = Counter(run.get(tag) for run in runs)
        top, count = votes.most_common(1)[0]
        per_item[tag] = {"distinct_decisions": len(votes), "modal_share": round(count / len(runs), 3)}
    identical = sum(1 for v in per_item.values() if v["distinct_decisions"] == 1)
    return {
        "runs": len(runs),
        "items": len(tags),
        "items_identical_every_run": identical,
        "share_identical": round(identical / len(tags), 3) if tags else None,
        "mean_modal_share": round(sum(v["modal_share"] for v in per_item.values()) / len(tags), 3) if tags else None,
        "per_item": per_item,
    }


def measure(db, key, runs=3):
    from backend.blocks.execution import run_stage
    from backend.orchestration.store import Store

    previous = os.environ.get("FLOWVALUE_AI_RESPONSE_CACHE")
    os.environ["FLOWVALUE_AI_RESPONSE_CACHE"] = "false"
    try:
        results = []
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "study.sqlite3"
            shutil.copy2(db, copy)
            store = Store(copy)
            for _ in range(runs):
                state = run_stage(store, key, "equipment", use_ai=True)
                results.append(decisions(state["results"]["stages"]["equipment"]["result"]))
        summary = agreement(results)
        # Tags are kept out of the summary so it can be shared; per-item detail is local.
        return {k: v for k, v in summary.items() if k != "per_item"}
    finally:
        if previous is None:
            os.environ.pop("FLOWVALUE_AI_RESPONSE_CACHE", None)
        else:
            os.environ["FLOWVALUE_AI_RESPONSE_CACHE"] = previous
