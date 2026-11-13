"""Python finds sizing parameters the workbook states, before the AI assumes them."""

from backend.equipment_costing.unit_conversion.bridges.workbook_parameters import for_items, parameters_in, scan
from backend.equipment_matching.deterministic import head_family


def _cells(rows):
    out = []
    for sheet, row, values in rows:
        for col, value in values:
            out.append({"sheet": sheet, "cell": f"{col}{row}", "value": value, "formula": None})
    return out


def test_label_value_and_unit_far_apart_on_merged_rows():
    cells = _cells([("Sizing", 12, [("A", 11), ("G", "Volume of 1 tank"), ("BA", 61.6), ("BF", "m3")]),
                    ("Sizing", 32, [("G", "Time for fermentation"), ("BA", 48), ("BF", "h")])])
    hits = {h["label"]: h for h in scan(cells)}
    assert hits["Volume of 1 tank"]["value"] == 61.6 and hits["Volume of 1 tank"]["unit"] == "m3"
    assert hits["Volume of 1 tank"]["id"] == "Sizing!BA12"
    assert hits["Time for fermentation"]["parameters"] == ["residence_time_h"]


def test_unit_in_label_and_no_value_means_no_hit():
    cells = _cells([("Basis", 3, [("A", "Pump efficiency (-)"), ("B", 0.75)]),
                    ("Basis", 4, [("A", "Density of feed"), ("B", "see sheet 2")])])
    hits = scan(cells)
    assert [h["label"] for h in hits] == ["Pump efficiency (-)"] and hits[0]["unit"] == "-"


def test_a_following_label_is_not_taken_as_the_value():
    cells = _cells([("Basis", 5, [("A", "Residence time"), ("B", "Density"), ("C", 998), ("D", "kg/m3")])])
    hits = scan(cells)
    assert [h["label"] for h in hits] == ["Density"]


def test_parameter_vocabulary():
    assert parameters_in("Overall heat transfer coefficient") == ["overall_u_w_m2_k"]
    assert parameters_in("Motor efficiency") == ["motor_efficiency"]
    assert "residence_time_h" in parameters_in("Hydraulic retention time (HRT)")
    assert parameters_in("Client name") == []


def test_scoping_by_tag_function_or_workbook_wide():
    cells = _cells([("B", 1, [("A", "P-7 efficiency"), ("B", 0.7)]),
                    ("B", 2, [("A", "Storage tank residence time"), ("B", 24), ("C", "h")]),
                    ("B", 3, [("A", "Density"), ("B", 1000), ("C", "kg/m3")])])
    items = [{"key": "p", "tag": "P-7", "names": ["Feed pump"]},
             {"key": "t", "tag": "T-1", "names": ["Storage tank"]}]
    scoped = for_items(scan(cells), items, head_family)
    assert {h["label"]: h["scope"] for h in scoped["p"]} == {"P-7 efficiency": "names this item's tag",
                                                            "Density": "workbook-wide"}
    assert {h["label"]: h["scope"] for h in scoped["t"]} == {"Storage tank residence time": "names this item's function",
                                                            "Density": "workbook-wide"}


def test_sizing_ai_receives_the_workbook_values(monkeypatch):
    import backend.blocks.equipment.runner as runner

    seen = {}

    def fake_resolve(report, plan, *a, **k):
        seen["params"] = report.get("_workbook_parameters")
        return plan, []

    monkeypatch.setattr("backend.equipment_costing.unit_conversion.bridges.automatic.resolve", fake_resolve)
    cells = _cells([("B", 2, [("A", "Storage tank residence time"), ("B", 24), ("C", "h")])])

    class Ctx:
        use_ai = True
        provider = None
        store = None
        upstream = {"engineering_data": {"source_cells": cells}}
        report = {"entities": [{"key": "t", "kind": "equipment", "identifier": "T-1",
                                "values": [{"property": "name", "normalized_value": "Storage tank"}]}]}
        state = {"locked": [], "description": ""}
        plan = {"equipment": [{"equipment_key": "t", "curve_id": "G303-144",
                               "model_selection": {"origin": "user", "curve_id": "G303-144"}}]}

    runner.prepare(Ctx())
    assert seen["params"]["t"][0]["id"] == "B!B2" and seen["params"]["t"][0]["value"] == 24


def test_cleared_records_saved_as_null_do_not_crash_the_equipment_run():
    from backend.blocks.equipment.runner import without_empty_records
    from backend.equipment_costing.unit_conversion.bridges.automatic import resolve

    rows = [{"equipment_key": "t", "curve_id": "G303-144", "size": None, "sizing": None, "unit_conversion": None}]
    cleaned = without_empty_records(rows)
    assert cleaned == [{"equipment_key": "t", "curve_id": "G303-144", "size": None}]
    report = {"entities": [{"key": "t", "kind": "equipment", "identifier": "T-1", "values": []}]}
    plan, audits = resolve(report, {"equipment": rows}, "", None, None, use_ai=False)  # no AttributeError
    assert audits
