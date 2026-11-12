"""Deterministic first-pass equipment matching (prototype)."""

import re
import time
from pathlib import Path

import pytest

from backend.equipment_matching import deterministic as D


def _report(items):
    entities = []
    for i, (tag, names) in enumerate(items):
        entities.append({
            "key": f"equipment:{i}", "kind": "equipment", "identifier": tag, "stream_keys": [],
            "values": [{"property": "name" if j == 0 else "type", "original_value": n, "normalized_value": n}
                       for j, n in enumerate(names)],
        })
    return {"entities": entities}


def _one(tag, *names):
    return D.match_register(_report([(tag, list(names))]))["matches"][0]


@pytest.mark.parametrize("names, family", [
    (["Centrifugal pump"], "pump"),
    (["Raw water storage tank", "Storage tank"], "tank"),
    (["Cation exchanger"], "ion_exchange"),           # not a heat exchanger
    (["Product pre-heater"], "heat_exchanger"),
    (["PEM water electrolyser", "Electrolyser / electrochemical reactor"], "electrolyser"),
    (["Bioreactor; agitated-vessel costing proxy may be appropriate"], "reactor"),
    (["Spray dryer"], "dryer"),
    (["Product cyclone"], "cyclone"),
    (["Biomass settler"], "settler"),
    (["Reverse-osmosis water-treatment unit"], "reverse_osmosis"),
])
def test_function_comes_from_the_items_own_name(names, family):
    assert D.classify({"tag": "X-9", "names": names})["family"] == family


def test_name_beats_a_misleading_tag_prefix():
    # A P- tag is not necessarily a pump; a C- tag is not necessarily a compressor.
    m = _one("P-900", "pH adjustment unit")
    assert m["family"] == "ph_adjustment" and m["family_basis"] == "name"
    assert _one("C-900", "Spray dryer")["family"] == "dryer"


def test_tag_prefix_alone_is_never_auto_selected():
    m = _one("P-900")
    assert m["status"] == "prefix_only" and m["selected_model_id"] is None and m["options"]


def test_unknown_function_is_left_for_the_ai_or_user():
    m = _one("U-900", "Unit 3")
    assert m["status"] == "unmatched" and m["options"] == [] and m["selected_model_id"] is None


def test_unspecified_configuration_asks_the_user_with_distinct_options():
    m = _one("E-900", "Heat exchanger")
    assert m["status"] == "choose" and m["selected_model_id"] is None
    subtypes = [o["subtype"][1] for o in m["options"]]
    assert len(subtypes) == len(set(subtypes)) > 1
    assert "shell tube" in subtypes  # common configurations surface first


def test_stated_configuration_is_preselected():
    for name, subtype in (("Double pipe heat exchanger", "double pipe"),
                          ("Plate and frame heat exchanger", "plate frame"),
                          ("Cation exchanger", "ion exchanger")):
        m = _one("E-900", name)
        assert m["status"] == "auto" and m["selected_model_id"] == m["options"][0]["model_id"]
        assert m["options"][0]["subtype"][1] == subtype


def test_centrifugal_pump_is_a_pump_and_ranks_centrifugal_models_first():
    m = _one("P-900", "Centrifugal pump")
    assert m["family"] == "pump" and "centrifugal" in m["options"][0]["subtype"][1]


def test_uk_and_us_spellings_match_the_same_models():
    uk = _one("X-900", "PEM electrolyser")["options"]
    us = _one("X-900", "PEM electrolyzer")["options"]
    assert [o["model_id"] for o in uk] == [o["model_id"] for o in us] and uk[0]["score"] > 0


def test_disabled_models_are_never_offered():
    disabled = {m["model_id"] for m in D.catalogue() if m.get("availability") == "disabled"}
    report = _report([("X-1", ["Reverse osmosis unit"]), ("X-2", ["Heat exchanger"]), ("X-3", ["Pump"])])
    offered = {o["model_id"] for m in D.match_register(report)["matches"] for o in m["options"]}
    assert offered and not offered & disabled


def test_deterministic_and_fast():
    D.index()  # built once per process
    items = [(f"X-{i}", [n]) for i, n in enumerate(
        ["Centrifugal pump", "Storage tank", "Heat exchanger", "Spray dryer", "Bioreactor"] * 10)]
    start = time.perf_counter()
    first = D.match_register(_report(items))
    elapsed = time.perf_counter() - start
    assert first == D.match_register(_report(items))
    assert elapsed < 0.5, elapsed  # 50 items; well under the time of one AI call


def test_rules_hold_no_project_equipment_tags():
    text = Path(D.__file__).read_text()
    assert re.findall(r"\b[A-Z]{1,4}-\d{2,4}[A-Z]{0,2}\b", text) == []


# --- Sizing ranking: can the study size the model from its own data? ---------

from backend.equipment_matching import sizing_paths as SP


def _sized_report(stream_values, equipment_values=()):
    streams = [{"key": f"stream:{i}", "kind": "material", "identifier": str(i),
                "values": [{"property": p, "normalized_value": v, "normalized_unit": u}
                           for p, v, u in values]}
               for i, values in enumerate(stream_values)]
    item = {"key": "equipment:0", "kind": "equipment", "identifier": "X-1",
            "stream_keys": [s["key"] for s in streams],
            "values": [{"property": p, "normalized_value": v, "normalized_unit": u} for p, v, u in equipment_values]}
    return {"entities": [item, *streams]}


def _model(quantity):
    return {"size_inputs": [{"quantity": quantity, "unit": "x"}]}


def test_source_quantity_is_direct():
    offer = SP.available(_sized_report([[("mass_flow", 100.0, "kg/h")]]), "equipment:0")
    assert SP.path(_model("mass_flow"), "electrolyser", offer)["status"] == "direct"


def test_vessel_volume_is_derived_from_flow_with_named_assumptions():
    report = _sized_report([[("mass_flow", 100.0, "kg/h"), ("volume_flow", 0.1, "m3/h")]])
    route = SP.path(_model("volume"), "tank", SP.available(report, "equipment:0"))
    assert route["status"] == "derived" and route["recipe"] == "vessel_volume"
    assert "density_kg_m3" in route["source_supported"]  # mass and volume flow give density
    assert set(route["assumptions"]) == {"residence_time_h", "working_fraction"}


def test_exchanger_area_needs_a_duty():
    two_enthalpies = _sized_report([[("enthalpy_flow", 10.0, "kW")], [("enthalpy_flow", 4.0, "kW")]])
    flow_only = _sized_report([[("mass_flow", 100.0, "kg/h")]])
    assert SP.path(_model("area"), "heat_exchanger", SP.available(two_enthalpies, "equipment:0"))["recipe"] == "exchanger_area"
    assert SP.path(_model("area"), "heat_exchanger", SP.available(flow_only, "equipment:0"))["status"] == "needs_input"


def test_recipes_only_apply_to_their_equipment_function():
    offer = SP.available(_sized_report([[("mass_flow", 100.0, "kg/h")]]), "equipment:0")
    assert SP.path(_model("area"), "filter", offer)["recipe"] == "filter_area"
    assert SP.path(_model("area"), "membrane", offer)["status"] == "needs_input"


def test_two_pressures_supply_the_pump_differential_pressure():
    report = _sized_report([[("mass_flow", 100.0, "kg/h"), ("pressure", 1.0, "bar")],
                            [("mass_flow", 100.0, "kg/h"), ("pressure", 4.0, "bar")]])
    route = SP.path(_model("flow_pressure_product"), "pump", SP.available(report, "equipment:0"))
    assert "differential_pressure_bar" in route["source_supported"]
    assert route["assumptions"] == ["density_kg_m3"]


def test_unresolved_catalogue_coordinate_is_unsizeable():
    assert SP.path(_model("unresolved"), "pump", {"quantities": set(), "supported_parameters": set()})["tier"] == 3


def test_sizeable_models_rank_above_unsizeable_at_equal_fit():
    report = _sized_report([[("mass_flow", 100.0, "kg/h")]])
    report["entities"][0]["values"] = [{"property": "name", "original_value": "Pump", "normalized_value": "Pump"}]
    options = D.match_register(report)["matches"][0]["options"]
    tiers = [min(o["sizing"]["tier"], 1) if o["sizing"]["tier"] <= 1 else o["sizing"]["tier"] - 1
             for o in options if o["score"] == options[0]["score"]]
    assert tiers == sorted(tiers) and options[0]["sizing"]["tier"] <= 1


def test_direct_contact_coolers_are_not_offered_as_heat_exchangers():
    families = {o["model_id"] for o in _one("E-900", "Heat exchanger")["options"]}
    contact = {m["model_id"] for m in D.index()["by_family"].get("direct_contact", [])}
    assert not families & contact


# --- Design-basis values feed the sizing check --------------------------------

def _db(parameter, value, unit, cell="C9"):
    return {"id": f"Basis!{cell}", "parameter": parameter, "value": value, "unit": unit}


def _items(*pairs):
    return [{"key": f"equipment:{i}", "tag": t, "family": f} for i, (t, f) in enumerate(pairs)]


def test_unique_role_links_a_duty_to_the_only_heat_exchanger():
    links = SP.link_design_basis([_db("Thermal duty to cooling water", 500.0, "kW")],
                                 _items(("X-1", "electrolyser"), ("X-2", "heat_exchanger")), D.head_family)
    row = links["linked"]["equipment:1"][0]
    assert row["quantity"] == "heat_duty" and row["link"] == "only item with this role"


def test_role_is_not_guessed_when_two_items_could_hold_it():
    links = SP.link_design_basis([_db("Thermal duty to cooling water", 500.0, "kW")],
                                 _items(("X-1", "heat_exchanger"), ("X-2", "heat_exchanger")), D.head_family)
    assert links["linked"] == {} and links["unlinked"][0]["parameter"].startswith("Thermal duty")


def test_tag_and_function_links():
    items = _items(("HE-7", "heat_exchanger"), ("HE-8", "heat_exchanger"), ("X-3", "electrolyser"))
    links = SP.link_design_basis([_db("HE 8 duty", 50.0, "kW"), _db("Electrolyser pressure", 1.0, "barg", "C10")],
                                 items, D.head_family)
    assert links["linked"]["equipment:1"][0]["link"] == "names the tag"
    assert links["linked"]["equipment:2"][0]["link"] == "names the function"


def test_short_tags_match_whole_words_only():
    links = SP.link_design_basis([_db("Hydrogen production", 100.0, "kg/h")], _items(("RO", "reverse_osmosis")),
                                 D.head_family)
    assert links["linked"] == {}


def test_differences_residuals_and_zero_values_are_not_sizing_data():
    rows = [_db("Coolant temperature rise", 10.0, "K"), _db("Cooling duty closure", 5.0, "kW", "C10"),
            _db("Net heat removed", 0, "kW", "C11")]
    links = SP.link_design_basis(rows, _items(("X-1", "heat_exchanger")), D.head_family)
    assert links["linked"] == {} and links["unlinked"] == []


def test_design_basis_duty_makes_exchanger_models_sizeable_and_is_cited():
    report = _report([("X-1", ["Heat exchanger"])])
    without = D.match_register(report)["matches"][0]
    with_basis = D.match_register(report, [_db("Thermal duty to cooling water", 500.0, "kW")])["matches"][0]
    shell = lambda m: next(o for o in m["options"] if o["subtype"][1] == "shell tube")
    assert shell(without)["sizing"]["status"] == "needs_input"
    route = shell(with_basis)["sizing"]
    assert route["recipe"] == "exchanger_area" and route["design_basis_cells"] == ["Basis!C9"]
    assert with_basis["design_basis"][0]["id"] == "Basis!C9"


# --- API: matches are served straight after extraction ------------------------

def test_equipment_matches_endpoint_after_extraction(tmp_path, monkeypatch):
    from io import BytesIO

    import openpyxl
    from fastapi.testclient import TestClient

    import backend.api.app as api
    from backend.blocks.execution import run_stage
    from backend.orchestration.store import Store

    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Balance"
    sheet.append(["Stream ID", "Description", "Mass flow (kg/h)", "Temperature (C)", "Pressure (bar)"])
    sheet.append(["S-1", "Feed to Storage Tank T-1", 1000, 25, 1])
    sheet.append(["S-2", "Water from Storage Tank T-1 to Pump P-1", 1000, 25, 1])
    sheet.append(["S-3", "Water leaving Pump P-1", 1000, 25, 4])
    data = BytesIO()
    book.save(data)
    store = Store(tmp_path / "api.sqlite")
    monkeypatch.setattr(api, "store", store)
    client = TestClient(api.app)
    key = client.post("/api/assessments", files={"file": ("b.xlsx", data.getvalue())}).json()["id"]
    assert client.get(f"/api/assessments/{key}/equipment-matches").status_code == 409
    run_stage(store, key, "engineering_data", use_ai=False)
    body = client.get(f"/api/assessments/{key}/equipment-matches").json()
    by_tag = {m["tag"]: m for m in body["matches"]}
    assert by_tag["T-1"]["family"] == "tank" and by_tag["P-1"]["family"] == "pump"
    assert by_tag["P-1"]["user_confirmed_model_id"] is None and body["elapsed_ms"] < 1000
    assert store.get(key)["revision"] == body["revision"]  # reading matches saves nothing


def test_model_in_use_is_offered_and_never_swapped_by_default():
    report = _report([("X-1", ["Bioreactor"])])
    in_use = "openpytea:jacketed_agitated_reactor_turton_2001"
    m = D.match_register(report, current_models={"equipment:0": in_use})["matches"][0]
    current = [o for o in m["options"] if o["current"]]
    assert [o["model_id"] for o in current] == [in_use]
    assert m["selected_model_id"] in (None, in_use)


def test_clear_match_that_differs_from_the_model_in_use_becomes_a_choice():
    report = _report([("X-1", ["pH adjustment unit"])])
    m = D.match_register(report, current_models={"equipment:0": "G303-144"})["matches"][0]
    assert m["status"] == "choose" and m["selected_model_id"] is None and "check it" in m["reason"]
