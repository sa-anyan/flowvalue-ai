"""The audit harness must never use an earlier AI response."""

from tools.audit_fresh_equipment import NoCacheStore, pricing_checks
from backend.orchestration.store import Store
from tools.audit_fresh_equipment import parallel_runs
from types import SimpleNamespace
import json
from unittest.mock import patch


def test_repeat_campaign_does_not_count_skipped_runs_as_passes(tmp_path):
    args = SimpleNamespace(
        output=tmp_path,
        workbook=tmp_path / "source.xlsx",
        description_file=None,
        revenue_file=None,
        python_ingestion=False,
        workers=1,
        runs=3,
        stop_on_incomplete=True,
        equipment_source="all",
    )

    def failed(command, **kwargs):
        output = tmp_path / "replicate-001"
        output.mkdir()
        (output / "summary.json").write_text(
            json.dumps(
                [
                    {
                        "priced": 5,
                        "total": 7,
                        "code_unchanged": True,
                        "unpriced": [{"tag": "R-001"}],
                        "numerical_inventory_issues": [],
                    }
                ]
            )
        )
        return SimpleNamespace(returncode=0)

    with patch(
        "tools.audit_fresh_equipment.code_fingerprint", return_value="test"
    ), patch("tools.audit_fresh_equipment.subprocess.run", side_effect=failed) as run:
        parallel_runs(args, "test")
    result = json.loads((tmp_path / "summary.json").read_text())
    assert run.call_count == 1
    assert sum(bool(r.get("not_run")) for r in result) == 2
    assert result[0]["priced"] == 5


def test_openpytea_audit_blocks_other_catalogues_and_calculation_routes():
    import pytest
    from tools.audit_fresh_equipment import equipment_source_policy
    from backend.equipment_costing import registry
    from backend.equipment_matching.service import catalogue

    before = registry.list_equipment_models("all")
    with equipment_source_policy("openpytea"):
        assert all(
            m["id"].startswith("openpytea:")
            for m in registry.list_equipment_models("all")
        )
        assert all(m["model_id"].startswith("openpytea:") for m in catalogue())
        for model in [
            "G258-004",
            "fermenter_reactor_turton_2001",
            "N501-PUMP-CAST_IRON",
        ]:
            with pytest.raises(ValueError, match="Audit source policy"):
                registry.estimate_cost(model, 10, size_unit="m3")
        assert (
            registry.estimate_cost(
                "openpytea:spray_dryer_seider_2013", 14, size_unit="kg/h"
            ).estimate.amount
            > 0
        )
    assert registry.list_equipment_models("all") == before


def test_audit_detects_duplicate_tags_and_ab_quantity():
    row = {
        "equipment_tag": "P-101AB",
        "equipment_cost": 100.0,
        "amount": 100.0,
        "quantity": 1,
        "cost_scope": "purchased_equipment",
    }
    issues = pricing_checks([row, dict(row)])
    assert any("duplicate" in issue for issue in issues)
    assert any("quantity is not two" in issue for issue in issues)


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
