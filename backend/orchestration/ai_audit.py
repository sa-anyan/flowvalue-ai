"""M5.6 AI decision log: every AI call and cache hit, without its content.

Each record holds the model, the prompt version (from the caller's context),
SHA-256 fingerprints of the instructions, request context and response, the
outcome and whether the cache answered. No prompt text, workbook values or
response text is written, so the log can be kept alongside private studies
without copying them.

The log is append-only JSON lines at FLOWVALUE_AI_AUDIT_LOG (default
outputs/ai_audit/decisions.jsonl). Set it to "off" to disable. A logging
failure never changes a calculation; it is reported once on stderr.
"""

import hashlib
import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

VERSION = "ai-audit-1"
_LOCK = threading.Lock()
_WARNED = False


def _digest(value):
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True, default=str)
    return hashlib.sha256(text.encode()).hexdigest()


def _path():
    raw = os.environ.get("FLOWVALUE_AI_AUDIT_LOG", "outputs/ai_audit/decisions.jsonl").strip()
    return None if raw.lower() in {"off", "false", "0", ""} else Path(raw)


def prompt_version(context):
    if isinstance(context, dict):
        for key in ("prompt_version", "task", "stage", "version"):
            if isinstance(context.get(key), str):
                return context[key]
    return None


def record(kind, *, model, context, instructions=None, response=None, outcome="ok", cached=None, error=None):
    global _WARNED
    path = _path()
    if path is None:
        return None
    entry = {
        "log_version": VERSION,
        "at": datetime.now(timezone.utc).isoformat(),
        "kind": kind,  # call, research or cache
        "model": model,
        "prompt_version": prompt_version(context),
        "context_sha256": _digest(context),
        "instructions_sha256": _digest(instructions) if instructions is not None else None,
        "response_sha256": _digest(response) if response is not None else None,
        "outcome": outcome,
        "cached": cached,
        "error_type": type(error).__name__ if error is not None else None,
    }
    try:
        with _LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, sort_keys=True) + "\n")
    except OSError as exc:
        if not _WARNED:
            print(f"FlowValue AI audit log unavailable: {type(exc).__name__}", file=sys.stderr)
            _WARNED = True
    return entry


def audited(kind, model, instructions, context, call):
    """Run one provider call and record it, whether it succeeds or fails."""
    try:
        response = call()
    except Exception as exc:
        record(kind, model=model, context=context, instructions=instructions, outcome="error", error=exc)
        raise
    record(kind, model=model, context=context, instructions=instructions, response=response)
    return response
