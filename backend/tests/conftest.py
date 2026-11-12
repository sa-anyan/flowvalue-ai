"""Shared test settings."""

import pytest


@pytest.fixture(autouse=True)
def _isolated_ai_audit_log(tmp_path, monkeypatch):
    # Tests never append to the real AI decision log.
    monkeypatch.setenv("FLOWVALUE_AI_AUDIT_LOG", str(tmp_path / "ai_audit.jsonl"))
