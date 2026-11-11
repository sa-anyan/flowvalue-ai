"""Exercise the real sizing audit and named-version/report boundaries."""

from copy import deepcopy
from html import unescape

from fastapi.testclient import TestClient

from backend.api import app as api
from backend.engineering_sizing.adapter import derive
from backend.orchestration.store import Store
from backend.tests.test_engineering_method_versions import synthetic_report
from backend.tests.test_method_acceptance import REFS, evaluate_reference


def equipment(key, audit):
    return {"equipment_tag": key, "parsed_source": {"equipment_key": key, "sizing": audit}}


def test_sizing_audit_survives_named_version_and_exports(tmp_path, monkeypatch):
    _, _, prepared = derive({
        "method": "vessel_hold_up", "stream_key": "s",
        "parameters": {"residence_time_h": 1, "working_fraction": 0.8},
    }, synthetic_report())
    _, _, compressor = evaluate_reference(next(c for c in REFS if c["method"] == "gas_compression"))
    _, _, mixing = evaluate_reference(next(c for c in REFS if c["method"] == "mixing_power"))
    rows = [
        equipment("vessel", prepared),
        equipment("compressor", {"calculation": compressor}),
        equipment("mixer", {"equation": mixing}),
        equipment("legacy", {"size": 7, "size_unit": "m3"}),
    ]
    store = Store(tmp_path / "trace.sqlite3")
    monkeypatch.setattr(api, "store", store)
    saved = store.create({"plan": {}, "results": {"stages": {
        "equipment": {"result": {"equipment": deepcopy(rows)}},
    }}}, b"synthetic")
    version = store.version(saved["id"], "Executed sizing")

    def snapshot_bytes():
        with store.db() as db:
            return db.execute("SELECT state FROM versions WHERE id=?", (version,)).fetchone()[0]

    original = snapshot_bytes()
    client = TestClient(api.app)
    reopened = client.post(f"/api/versions/{version}/open")
    assert reopened.status_code == 200
    payload = reopened.json()
    key = payload["id"]
    download = client.get(f"/api/assessments/{key}/snapshot")
    assert download.status_code == 200
    for data in (payload, download.json()):
        assert data["results"]["stages"]["equipment"]["result"]["equipment"] == rows
        traces = data["equipment_sizing_traces"]
        assert traces[0]["engineering_methods"] == [
            prepared["engineering_method"], prepared["calculation"]["engineering_method"],
        ]
        assert all(len(method) == 5 for method in traces[0]["engineering_methods"])
        assert traces[1]["applicability_notes"] == compressor["applicability_warnings"]
        assert traces[2]["applicability_notes"] == [mixing["volume_basis"], mixing["scope"]]
        assert traces[3]["status"] == "unversioned"
        assert traces[3]["engineering_methods"] == []
    report = client.get(f"/api/assessments/{key}/report")
    assert report.status_code == 200
    html = unescape(report.text)
    for note in [*compressor["applicability_warnings"], mixing["volume_basis"], mixing["scope"]]:
        assert note in html
    assert prepared["engineering_method"]["implementation_fingerprint"] in html
    assert prepared["calculation"]["engineering_method"]["implementation_fingerprint"] in html
    assert "Unversioned" in html
    assert snapshot_bytes() == original
    assert store.get(saved["id"]) == saved
    assert store.get(key)["results"] == saved["results"]
