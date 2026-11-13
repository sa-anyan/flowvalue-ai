"""Autopilot sequences the existing stages and records what it decided."""

from io import BytesIO

import openpyxl

from backend.blocks import autopilot
from backend.blocks.execution import run_stage
from backend.orchestration.store import Store


def _workbook():
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Balance"
    sheet.append(["Stream ID", "Description", "Mass flow (kg/h)", "Temperature (C)", "Pressure (bar)"])
    sheet.append(["S-1", "Feed water to Storage Tank T-1", 1000, 25, 1])
    sheet.append(["S-2", "Water from Storage Tank T-1 to Pump P-1", 1000, 25, 1])
    sheet.append(["S-3", "Water leaving Pump P-1", 1000, 25, 4])
    data = BytesIO()
    book.save(data)
    return data.getvalue()


def _study(tmp_path):
    from fastapi.testclient import TestClient

    import backend.api.app as api

    store = Store(tmp_path / "a.sqlite")
    api.store = store
    key = TestClient(api.app).post("/api/assessments", files={"file": ("b.xlsx", _workbook())}).json()["id"]
    run_stage(store, key, "engineering_data", use_ai=False)
    return store, key


def test_autopilot_approves_picks_models_runs_stages_and_lists_decisions(tmp_path, monkeypatch):
    import backend.api.app as api

    original = api.store
    try:
        store, key = _study(tmp_path)
        state = autopilot.run(store, key, use_ai=False)
    finally:
        api.store = original
    assert state["engineering_approval"]["by"] == autopilot.VERSION
    picked = {p["tag"] for p in state["autopilot"]["picked_models"]}
    assert picked == {"T-1", "P-1"}
    rows = state["plan"]["equipment"]
    assert all((r.get("model_selection") or {}).get("origin") == "autopilot" for r in rows if r.get("curve_id"))
    assert set(state["stage_runs"]) >= {"equipment", "capex", "revenue", "opex", "financial"}
    kinds = {item["kind"] for item in state["autopilot"]["review"]}
    assert {"approval", "models"} <= kinds
    assert state["autopilot"]["status"] == "finished" and state["running"] is False
    assert "total_capex" in state["autopilot"]["headline"]


def test_user_model_choice_is_never_changed(tmp_path):
    import backend.api.app as api

    original = api.store
    try:
        store, key = _study(tmp_path)
        state = store.get(key)
        tank = next(e["key"] for e in state["stage_outputs"]["engineering_data"]["report"]["entities"]
                    if e.get("identifier") == "T-1")
        state["plan"]["equipment"] = [{"equipment_key": tank, "curve_id": "G303-144",
                                       "model_selection": {"origin": "user", "curve_id": "G303-144"}}]
        store.put(state, state["revision"])
        state = autopilot.run(store, key, use_ai=False)
    finally:
        api.store = original
    row = next(r for r in state["plan"]["equipment"] if r["equipment_key"] == tank)
    assert row["curve_id"] == "G303-144" and row["model_selection"]["origin"] == "user"
    assert "T-1" not in {p["tag"] for p in state["autopilot"]["picked_models"]}


def test_capex_runs_with_python_defaults_when_nothing_was_chosen():
    from backend.capex.defaults import fill_missing

    report = {"entities": [{"key": "e1", "kind": "equipment", "identifier": "D-1",
                            "values": [{"property": "name", "normalized_value": "Spray dryer"}]},
                           {"key": "e2", "kind": "equipment", "identifier": "P-1",
                            "values": [{"property": "name", "normalized_value": "Feed pump"}]}]}
    filled, applied = fill_missing({}, report)
    assert filled["process_type"] == "mixed" and filled["delivery_basis"] == "delivered"
    assert filled["factor_selection"] == "midpoint" and filled["selected_factors"] == {"offsite_facilities": 0.0}
    assert {a["setting"] for a in applied} == {"process_type", "delivery_basis", "factor_selection"}
    kept, applied = fill_missing({"process_type": "fluids", "delivery_basis": "ex_works", "selected_factors": {"piping": 0.3}}, report)
    assert kept["delivery_basis"] == "ex_works" and kept["selected_factors"] == {"piping": 0.3} and applied == []


def test_user_price_on_the_study_date_adds_into_the_capex_total():
    from decimal import Decimal
    from types import SimpleNamespace

    from backend.capex.engine import _basis
    from backend.capex.models import EquipmentCost

    def cost(tag, series, index, period="2026-09"):
        return EquipmentCost(tag=tag, purchased_cost=Decimal("1000"), currency="USD", period=period,
                             index_series=series, index_value=Decimal(index), cost_scope="purchased_equipment",
                             delivery_basis="delivered")

    issues = []
    total, _ = _basis(SimpleNamespace(equipment=(cost("A", "US_CPI_U_NSA_1982_84", "336.9"),
                                                 cost("B", "PRICE_BASIS:USD:2026-09", "1"))), False, issues)
    assert issues == [] and total == Decimal("2000")
    issues = []
    total, _ = _basis(SimpleNamespace(equipment=(cost("A", "US_CPI_U_NSA_1982_84", "336.9"),
                                                 cost("B", "PRICE_BASIS:USD:2024", "1", period="2024"))), False, issues)
    assert total is None and "B is costed in USD 2024" in issues[0]


def _price(tag, amount, period, scope="purchased_equipment"):
    return {"equipment_tag": tag, "curve_id": None, "size": None, "size_unit": None, "quantity": 1,
            "manual_price": {"amount": amount, "currency": "USD", "price_period": period, "cost_scope": scope,
                             "source": "User-entered equipment price", "notes": "test", "approved": True}}


def test_equipment_total_keeps_packages_separate_and_names_date_mismatches():
    from backend.equipment_costing.total_cost.calculator import calculate_total_cost

    total = calculate_total_cost([_price("T-1", 1000.0, "2026-09"), _price("T-2", 500.0, "2026-09")])
    assert total.equipment_cost_total == 1500.0
    mixed = calculate_total_cost([_price("T-1", 1000.0, "2026-09"), _price("T-2", 500.0, "2024")])
    assert mixed.equipment_cost_total is None
    assert "USD 2024: T-2" in mixed.issues[0] and "USD 2026-09: T-1" in mixed.issues[0]


def test_year_only_user_price_counts_on_the_study_basis():
    from backend.equipment_costing.total_cost.calculator import calculate_total_cost

    total = calculate_total_cost([_price("T-1", 1000.0, "2026-09"), _price("T-2", 500.0, "2026")])
    assert total.equipment_cost_total == 1500.0
    assert any("T-2: dated 2026, counted on the 2026-09 basis" in i for i in total.issues)
    other_year = calculate_total_cost([_price("T-1", 1000.0, "2026-09"), _price("T-2", 500.0, "2024")])
    assert other_year.equipment_cost_total is None
