"""Synthetic local version checks: no production records or external services."""

from copy import deepcopy

import pytest

from backend.orchestration.store import Store


def test_reopen_forks_without_mutating_original_revision(tmp_path):
    store = Store(tmp_path / "synthetic.sqlite3")
    original = store.create(
        {"running": False, "plan": {"marker": "original"}},
        b"synthetic-not-a-user-workbook",
    )
    snapshot = deepcopy(original)
    version = store.version(original["id"], "Phase0 synthetic baseline")
    edited = deepcopy(original)
    edited["plan"]["marker"] = "edited"
    store.put(edited, original["revision"])
    reopened = store.load(version)
    assert reopened["id"] != original["id"]
    assert reopened["plan"] == snapshot["plan"]
    assert reopened["parent_version"] == version
    assert store.get(original["id"])["plan"]["marker"] == "edited"
    again = store.load(version)
    assert again["plan"] == snapshot["plan"]
    assert store.workbook(again["id"]) == b"synthetic-not-a-user-workbook"


def test_stale_writer_cannot_replace_newer_revision(tmp_path):
    store = Store(tmp_path / "synthetic.sqlite3")
    state = store.create({"plan": {}}, b"synthetic")
    updated = store.put({**state, "plan": {"revision_marker": 1}}, 0)
    with pytest.raises(ValueError, match="changed"):
        store.put({**state, "plan": {"revision_marker": 2}}, 0)
    assert store.get(state["id"]) == updated
