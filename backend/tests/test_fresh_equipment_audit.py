"""The audit harness must never use an earlier AI response."""

from tools.audit_fresh_equipment import NoCacheStore
from backend.orchestration.store import Store


def test_audit_ignores_preexisting_response_cache(tmp_path):
    store = NoCacheStore(tmp_path / "audit.sqlite3")
    context = {"task": "independent-test"}
    Store.cached(store, context, lambda: {"value": "old response"})
    calls = []
    result, cached = store.cached(
        context, lambda: (calls.append(True) or {"value": "fresh response"})
    )
    assert result == {"value": "fresh response"} and not cached
    assert calls == [True]


def test_local_cache_off_ignores_existing_responses_and_never_writes(
    monkeypatch, tmp_path
):
    store = Store(tmp_path / "local.db")
    monkeypatch.delenv("FLOWVALUE_AI_RESPONSE_CACHE", raising=False)
    Store.cached(store, {"task": "old"}, lambda: {"value": "old response"})
    monkeypatch.setenv("FLOWVALUE_AI_RESPONSE_CACHE", "false")
    calls = []
    for task in ["old", "new", "new"]:
        value, cached = store.cached(
            {"task": task}, lambda: (calls.append(task) or {"value": "fresh"})
        )
        assert value == {"value": "fresh"} and not cached
    assert calls == ["old", "new", "new"]
    with store.db() as db:
        assert db.execute("select count(*) from ai_cache").fetchone()[0] == 1
