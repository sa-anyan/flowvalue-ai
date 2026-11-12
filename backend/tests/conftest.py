"""Shared pytest configuration for the backend tests."""

import pytest

# Cloud-sync tools (iCloud, OneDrive) create conflict copies such as
# "test_units 2.py". They are ignored by git but would otherwise be collected
# and run as duplicate, possibly stale, tests. fnmatch "*" also spans folders.
collect_ignore_glob = ["* [0-9].py", "* [0-9][0-9].py"]


@pytest.fixture(autouse=True)
def _isolated_ai_audit_log(tmp_path, monkeypatch):
    # Tests never append to the real AI decision log.
    monkeypatch.setenv("FLOWVALUE_AI_AUDIT_LOG", str(tmp_path / "ai_audit.jsonl"))
