"""Save reproducible input/result bundles without overwriting approved files."""

import json
from dataclasses import asdict
from pathlib import Path

from .snapshots import freeze_project, snapshot_id


def save_assessment(project, result, path, *, proposal=None):
    if result.snapshot_id != snapshot_id(project):
        raise ValueError("Result is stale for this revenue project")
    if proposal is not None and proposal.project_snapshot_id != result.snapshot_id:
        raise ValueError("AI proposal is stale for this project")
    payload = {
        "schema_version": 1,
        "input_snapshot": json.loads(freeze_project(project)),
        "calculation": asdict(result),
        "ai_proposal": asdict(proposal) if proposal is not None else None,
    }
    content = json.dumps(
        payload, default=str, sort_keys=True, indent=2, allow_nan=False
    )
    destination = Path(path)
    with destination.open("x", encoding="utf-8") as stream:
        stream.write(content)
    return destination
