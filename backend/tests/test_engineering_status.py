"""Engineering notes distinguish inconsistent data, unchecked closure and scope."""

from copy import deepcopy

from backend.engineering_status import balance_summary, project_status, refresh_scope_notes
from backend.equipment_resolution.register_completeness import check


def stream(key, sheet, name, total=100, parts=(60, 40)):
    return {"key": key, "kind": "material", "identifier": key,
            "id_evidence": {"sheet": sheet},
            "values": [{"property": "description", "normalized_value": name, "sheet": sheet, "cell": "A1"},
                       {"property": "mass_flow", "normalized_value": total, "normalized_unit": "kg/h", "sheet": sheet, "cell": "B4"},
                       *[{"property": "component_mass_flow", "component": f"C{i}", "normalized_value": v,
                          "normalized_unit": "kg/h"} for i, v in enumerate(parts)]]}


def report():
    return {"entities": [{"key": "T1", "kind": "equipment", "identifier": "Tank T1",
                          "id_evidence": {"sheet": "Process"}, "stream_keys": ["S1"], "values": []},
                         stream("S1", "Process", "Feed to tank"),
                         stream("S2", "Example", "Hot mash to cooler")], "checks": []}


def test_unlinked_example_is_scope_question_not_missing_process_equipment():
    result = check(report())
    assert result["possibly_missing"] == []
    assert result["scope_review"][0]["family"] == "heat_exchanger"
    assert result["scope_review"][0]["evidence"][0]["source"] == "Example!A1"


def test_real_unregistered_unit_in_connected_process_still_flagged():
    r = report()
    r["entities"].append(stream("S3", "Process", "Feed to RO"))
    assert [i["family"] for i in check(r)["possibly_missing"]] == ["reverse_osmosis"]


def test_explicit_active_second_sheet_is_not_hidden():
    r = report()
    r["calculation_scope"] = {"worksheets": [{"sheet": s, "role": "active"} for s in ("Process", "Example")]}
    assert check(r)["possibly_missing"][0]["family"] == "heat_exchanger"
    r["calculation_scope"]["worksheets"][1]["role"] = "reference"
    assert check(r)["possibly_missing"] == []
    assert check(r)["scope_review"] == []


def test_no_equipment_does_not_hide_named_units():
    r = report()
    r["entities"] = r["entities"][1:]
    assert "heat_exchanger" in {i["family"] for i in check(r)["possibly_missing"]}


def test_equal_component_sums_are_not_proof_of_plant_closure():
    result = balance_summary(report())
    assert result["mass"] == result["energy"] == "unverified"
    assert not result["mismatches"]


def test_component_mismatch_has_source_and_does_not_change_source():
    r = report()
    r["entities"][1]["values"][1]["normalized_value"] = 90
    before = deepcopy(r)
    result = balance_summary(r)
    assert result["mass"] == "inconsistent"
    assert result["mismatches"][0] == {"stream": "S1", "source": "Process!B4", "reported": "90",
                                        "component_sum": "100", "difference": "10", "unit": "kg/h"}
    assert r == before


def test_unknown_component_is_not_called_an_imbalance_or_zero():
    r = report()
    r["entities"][1]["values"][-1]["normalized_value"] = None
    assert balance_summary(r)["mass"] == "unverified"
    assert not balance_summary(r)["mismatches"]


def test_explicit_verified_checks_and_failed_residual_are_distinct():
    r = report()
    r["checks"] = [{"name": n, "status": "verified", "residual": 0}
                   for n in ("Overall mass balance", "Energy balance")]
    assert balance_summary(r)["mass"] == "verified"
    r["checks"][0].update(status="unresolved", residual=12)
    assert balance_summary(r)["mass"] == "imbalanced"


def test_saved_diagnostics_refresh_without_recalculating_or_changing_approval():
    state = {"effective_report": report(), "engineering_data_approved": True,
             "results": {"stages": {"equipment": {"result": {"amount": 123,
                         "pricing_coverage": {"complete": False, "tiers": {"register_completeness": "unconfirmed: cooler"}}}}}}}
    project_status(state)
    equipment = state["results"]["stages"]["equipment"]["result"]
    assert equipment["amount"] == 123 and state["engineering_data_approved"]
    assert equipment["pricing_coverage"]["register_completeness"]["possibly_missing"] == []
    assert "register_completeness" not in equipment["pricing_coverage"]["tiers"]
    assert not equipment["pricing_coverage"]["complete"]  # scope still needs review


def test_saved_review_decisions_survive_scope_warning_refresh():
    previous = {"resolved": [{"family": "pump", "decision": "included_in", "basis": "Package scope"}],
                "possibly_missing": [{"family": "heat_exchanger", "label": "Cooler", "evidence": [{"source": "Example!A1"}]},
                                     {"family": "reverse_osmosis", "label": "RO", "evidence": [{"source": "Process!A1"}]}]}
    result = refresh_scope_notes(report(), previous, {})
    assert [i["family"] for i in result["possibly_missing"]] == ["reverse_osmosis"]
    assert result["resolved"] == previous["resolved"]
    assert result["scope_review"][0]["family"] == "heat_exchanger"
