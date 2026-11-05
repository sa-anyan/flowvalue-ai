"""Shared input ladder: exact values, LLM-selected bridges and per-item failures."""

import copy
from unittest.mock import patch
import pytest
from backend.equipment_costing.unit_conversion.bridges.automatic import resolve
from backend.equipment_costing.unit_conversion.bridges.derivations import derive
from backend.equipment_costing.unit_conversion.bridges.service import (
    measurements,
    evaluate,
)
from backend.orchestration.store import Store
from backend.tests.test_unit_conversion_bridges import REPORT


def selected(key="e"):
    return {
        "equipment_key": key,
        "curve_id": "G258-004",
        "costing_options": {"unit_context": {"target_gallon_basis": "US"}},
    }


def decision(key="e"):
    return {
        "equipment_key": key,
        "model_id": "G258-004",
        "status": "proposed",
        "method": "vessel_volume",
        "measurement_id": "m",
        "outlet_measurement_id": None,
        "same_side_reference_confirmed": False,
        "assumptions": [
            {
                "name": n,
                "value": v,
                "unit": u,
                "rationale": "Explicit test engineering assumption",
                "limitations": "Screening only",
            }
            for n, v, u in [
                ("density_kg_m3", 1000, "kg/m3"),
                ("residence_time_h", 2, "h"),
                ("working_fraction", 0.8, "fraction"),
            ]
        ],
        "derivations": [],
        "unit_context": {
            "target_gallon_basis": "US",
            "target_ton_basis": None,
            "atmospheric_pressure_pa": None,
        },
        "allow_unverified_graph_points": False,
        "extrapolation_exponent": None,
        "extrapolation_rationale": "",
        "rationale": "Test vessel hold-up scenario",
        "limitations": "No design validation",
    }


class Provider:
    model = "test-no-network"

    def generate(self, **kw):
        return {"decisions": [decision()]}


def test_highest_explicit_equipment_dimension_and_no_ai(tmp_path):
    report = copy.deepcopy(REPORT)
    report["entities"][0]["values"] = [
        {
            "id": f"v{i}",
            "property": "volume",
            "normalized_value": v,
            "normalized_unit": u,
            "status": "verified",
            "sheet": "Dimensions",
            "cell": f"A{i}",
        }
        for i, (v, u) in enumerate([(1, "m3"), (2000, "L")])
    ]

    class Fail:
        model = "never"

        def generate(self, **kw):
            raise AssertionError("No AI for exact equipment dimensions")

    plan, audit = resolve(
        report, {"equipment": [selected()]}, "", Store(tmp_path / "db"), Fail(), True
    )
    assert audit[0]["status"] == "direct_source_input"
    assert plan["equipment"][0]["unit_conversion"]["measurement_id"] == "v1"
    assert audit[0]["size"] == pytest.approx(528.344104716)


def test_llm_routes_input_then_python_derives_size_and_caches(tmp_path):
    store = Store(tmp_path / "db")
    plan, audit = resolve(
        REPORT,
        {"equipment": [selected()]},
        "Continuous liquid vessel",
        store,
        Provider(),
        True,
    )
    assert audit[-1]["status"] == "converted_with_explicit_basis"
    spec = plan["equipment"][0]["unit_conversion"]
    assert spec["input_provenance"]["residence_time_h"]["status"] == "llm_estimate"
    assert evaluate(REPORT, "e", spec)["size"] == pytest.approx(660.430130895)
    _, again = resolve(
        REPORT,
        {"equipment": [selected()]},
        "Continuous liquid vessel",
        store,
        Provider(),
        True,
    )
    assert again[-1]["cached"] is True
    # Every new deterministic run reads current source values, not cached size.
    changed = copy.deepcopy(REPORT)
    changed["entities"][1]["values"][0]["normalized_value"] = 2000
    assert evaluate(changed, "e", spec)["size"] == pytest.approx(1320.86026179)


def test_missing_model_and_bad_item_do_not_discard_good_item(tmp_path):
    report = copy.deepcopy(REPORT)
    report["entities"].append(
        {
            "key": "e2",
            "identifier": "EL-9",
            "kind": "equipment",
            "values": [],
            "stream_keys": [],
        }
    )
    plan, audit = resolve(
        report,
        {"equipment": [selected(), {"equipment_key": "e2"}]},
        "",
        Store(tmp_path / "db"),
        Provider(),
        True,
    )
    assert any(
        a["equipment_key"] == "e2" and a["status"] == "unsupported_model" for a in audit
    )
    assert plan["equipment"][0]["unit_conversion"]["enabled"]


def test_unknown_model_and_hallucinated_source_are_not_accepted(tmp_path):
    class Bad(Provider):
        def generate(self, **kw):
            d = decision()
            d["measurement_id"] = "made-up"
            return {"decisions": [d]}

    plan, audit = resolve(
        REPORT, {"equipment": [selected()]}, "", Store(tmp_path / "db"), Bad(), True
    )
    assert "unit_conversion" not in plan["equipment"][0]
    assert audit[-1]["status"] == "input_resolution_unresolved"


def test_user_inputs_and_locked_sections_not_overridden(tmp_path):
    p = selected()
    p["size"] = 123
    p["size_unit"] = "gal"
    result, _ = resolve(
        REPORT, {"equipment": [p]}, "", Store(tmp_path / "db"), Provider(), True
    )
    assert result["equipment"][0] == p
    result, audit = resolve(
        REPORT,
        {"equipment": [selected()]},
        "",
        Store(tmp_path / "db"),
        Provider(),
        True,
        locked=True,
    )
    assert "unit_conversion" not in result["equipment"][0]
    assert audit[-1]["status"] == "awaiting_ai_or_user_inputs"


def test_meb_ratios_state_and_lmtd_use_source_references():
    obs = measurements(REPORT, "e")
    inputs, audit = derive(
        [
            {
                "name": "molecular_weight_kg_kmol",
                "method": "mixture_molecular_weight",
                "measurement_ids": ["m", "n"],
            }
        ],
        obs,
        {},
        {},
    )
    assert inputs["molecular_weight_kg_kmol"] == 1000
    assert audit[0]["source_measurements"][0]["cell"] == "A1"
    temp = [
        {
            "id": f"t{i}",
            "entity_key": str(i),
            "property": "temperature",
            "value": v,
            "unit": "degC",
        }
        for i, v in enumerate([100, 80, 20, 40])
    ]
    result, _ = derive(
        [
            {
                "name": "lmtd_k",
                "method": "lmtd_countercurrent",
                "measurement_ids": [v["id"] for v in temp],
            }
        ],
        temp,
        {},
        {},
    )
    assert result["lmtd_k"] == pytest.approx(60)
    with pytest.raises(ValueError):
        derive(
            [
                {
                    "name": "density_kg_m3",
                    "method": "density_from_flows",
                    "measurement_ids": ["m", "n"],
                }
            ],
            obs,
            {},
            {},
        )


def test_maximum_ignores_stream_flow_as_vessel_dimension(tmp_path):
    _, audit = resolve(
        REPORT, {"equipment": [selected()]}, "", Store(tmp_path / "db"), use_ai=False
    )
    assert not any(a["status"] == "direct_source_input" for a in audit)


@pytest.mark.parametrize(
    "layout", ["row_table", "column_table", "multiple_sheets", "repeated_nottingham"]
)
def test_different_workbooks_feed_same_input_and_price_path(tmp_path, layout):
    from io import BytesIO
    import openpyxl
    from backend.orchestration.ingest import parse
    from backend.blocks.equipment.calculation import calculate_equipment

    if layout == "repeated_nottingham":
        from backend.tests.test_nottingham_parser import workbook

        content = workbook()
    else:
        book = openpyxl.Workbook()
        sheet = book.active
        sheet.title = "Unrelated export name"
        cells = [
            [
                "Stream ID",
                "Description",
                "Mass flow (kg/h)",
                "Temperature (C)",
                "Pressure (bar)",
            ],
            ["IN-9", "Water entering Storage Tank TK-9", 1000, 25, 1],
            ["OUT-9", "Water leaving Storage Tank TK-9", 1000, 25, 1],
        ]
        for row in list(zip(*cells)) if layout == "column_table" else cells:
            sheet.append(list(row))
        if layout == "multiple_sheets":
            notes = book.create_sheet("General notes")
            notes.append(["Not an engineering table"])
        data = BytesIO()
        book.save(data)
        content = data.getvalue()
    # Keep reproducible input workbooks for inspection.
    (tmp_path / (layout + ".xlsx")).write_bytes(content)
    report = parse(content, layout + ".xlsx")["report"]
    equipment = [e for e in report["entities"] if e["kind"] == "equipment"]
    assert equipment
    tank = next((e for e in equipment if "MT-101" in e["identifier"]), equipment[0])
    key = tank["key"]
    row = selected(key)
    row["costing_options"]["allow_unverified"] = True

    class ContextProvider(Provider):
        def generate(self, **kw):
            assert kw["context"]["task"].startswith("equipment-input-resolution-")
            decisions = []
            for item in kw["context"]["equipment"]:
                d = decision(item["equipment_key"])
                d["measurement_id"] = next(
                    v["id"]
                    for v in item["measurements"]
                    if v["property"] == "mass_flow"
                )
                d["allow_unverified_graph_points"] = True
                decisions.append(d)
            return {"decisions": decisions}

    plan, audit = resolve(
        report,
        {"equipment": [row]},
        "Preliminary water-handling equipment",
        Store(tmp_path / (layout + ".sqlite")),
        ContextProvider(),
        True,
    )
    total, inputs = calculate_equipment(report, plan)
    line = next(e for e in total.equipment if e.equipment_tag == tank["identifier"])
    assert line.equipment_cost is not None and line.equipment_cost > 0
    assert any(a["status"] == "converted_with_explicit_basis" for a in audit)
    assert next(r for r in inputs if r["equipment_tag"] == tank["identifier"])[
        "parsed_source"
    ]["sizing"]["source_measurements"][0]["sheet"]


def test_state_and_molecular_weight_are_derived_not_llm_arithmetic(tmp_path):
    report = copy.deepcopy(REPORT)
    report["entities"][1]["values"].extend(
        [
            {
                "id": "temp",
                "property": "temperature",
                "normalized_value": 25,
                "normalized_unit": "degC",
                "status": "verified",
                "sheet": "B",
                "cell": "A8",
            },
            {
                "id": "press",
                "property": "pressure",
                "normalized_value": 1,
                "normalized_unit": "bar_gauge",
                "status": "verified",
                "sheet": "B",
                "cell": "A9",
            },
        ]
    )

    class GasProvider(Provider):
        def generate(self, **kw):
            d = decision()
            d.update(
                model_id="G261-014",
                method="gas_flow",
                assumptions=[
                    {
                        "name": "compressibility_z",
                        "value": 1,
                        "unit": "fraction",
                        "rationale": "Explicit ideal-gas screening assumption",
                        "limitations": "Check gas applicability",
                    }
                ],
                unit_context={
                    "target_gallon_basis": None,
                    "target_ton_basis": None,
                    "atmospheric_pressure_pa": 101325,
                },
            )
            return {"decisions": [d]}

    plan, audit = resolve(
        report,
        {"equipment": [{"equipment_key": "e", "curve_id": "G261-014"}]},
        "Gas handling",
        Store(tmp_path / "gas.sqlite"),
        GasProvider(),
        True,
    )
    spec = plan["equipment"][0]["unit_conversion"]
    assert spec["inputs"]["molecular_weight_kg_kmol"] == 1000
    assert spec["inputs"]["temperature_k"] == pytest.approx(298.15)
    assert spec["inputs"]["absolute_pressure_bar"] == pytest.approx(2.01325)
    assert spec["input_provenance"]["temperature_k"]["status"] == "derived_from_meb"
    assert spec["input_provenance"]["compressibility_z"]["status"] == "llm_estimate"
    changed = copy.deepcopy(report)
    changed["entities"][1]["values"][-2]["normalized_value"] = 35
    again, _ = resolve(
        changed, plan, "Gas handling", Store(tmp_path / "gas.sqlite"), use_ai=False
    )
    assert again["equipment"][0]["unit_conversion"]["inputs"][
        "temperature_k"
    ] == pytest.approx(308.15)


def test_bad_unit_context_does_not_crash_other_equipment():
    from backend.blocks.equipment.calculation import calculate_equipment

    report = copy.deepcopy(REPORT)
    second = copy.deepcopy(report["entities"][0])
    second.update(key="e2", identifier="E-2")
    report["entities"].append(second)
    plan = {
        "equipment": [
            {
                "equipment_key": "e",
                "curve_id": "G258-004",
                "costing_options": {"unit_context": {"not_a_field": 7}},
            },
            {
                "equipment_key": "e2",
                "curve_id": "G258-004",
                "size": 100,
                "size_unit": "US_gal",
                "costing_options": {
                    "allow_unverified": True,
                    "unit_context": {"target_gallon_basis": "US"},
                },
            },
        ]
    }
    total, rows = calculate_equipment(report, plan)
    assert rows[0]["parsed_source"]["sizing_issue"]
    assert total.equipment[1].equipment_cost is not None


def test_provisional_graph_policy_flows_to_costing_and_can_be_disabled(tmp_path):
    from backend.blocks.equipment.calculation import calculate_equipment

    store = Store(tmp_path / "graph.sqlite")
    plan, _ = resolve(REPORT, {"equipment": [selected()]}, "", store, Provider(), True)
    total, _ = calculate_equipment(REPORT, plan)
    assert total.equipment[0].equipment_cost is not None
    assert any("UNVERIFIED" in issue for issue in total.equipment[0].issues)
    denied, _ = resolve(
        REPORT,
        {
            "equipment_input_policy": {"allow_provisional_graph_estimates": False},
            "equipment": [selected()],
        },
        "",
        store,
        Provider(),
        True,
    )
    total, _ = calculate_equipment(REPORT, denied)
    assert total.equipment[0].equipment_cost is None


def test_one_bounded_repair_pass_for_missing_source(tmp_path):
    class Repair(Provider):
        calls = 0

        def generate(self, **kw):
            self.calls += 1
            d = decision()
            if not kw["context"].get("repair_feedback"):
                d["measurement_id"] = "unknown-id"
            return {"decisions": [d]}

    provider = Repair()
    plan, audit = resolve(
        REPORT,
        {"equipment": [selected()]},
        "",
        Store(tmp_path / "repair.sqlite"),
        provider,
        True,
    )
    assert provider.calls == 2
    assert (
        audit[-1]["status"] == "converted_with_explicit_basis"
        and audit[-1]["repair_attempt"]
    )
    assert plan["equipment"][0]["unit_conversion"]["enabled"]


def test_pricing_repair_is_bounded_and_preserves_user_inputs(tmp_path):
    from types import SimpleNamespace
    from backend.equipment_costing.unit_conversion.bridges.automatic import (
        repair_pricing,
    )

    store = Store(tmp_path / "scaling.sqlite")
    plan, _ = resolve(REPORT, {"equipment": [selected()]}, "", store, Provider(), True)
    total = SimpleNamespace(
        equipment=[
            SimpleNamespace(
                equipment_cost=None,
                parsed_source={"equipment_key": "e"},
                issues=["Unsupported extrapolation: engineering exponent needed"],
            )
        ]
    )

    class Scaling(Provider):
        def generate(self, **kw):
            assert kw["context"]["repair_feedback"]
            d = decision()
            d.update(
                extrapolation_exponent=0.6,
                extrapolation_rationale="Explicit preliminary geometric scaling scenario, not a validated source exponent",
            )
            return {"decisions": [d]}

    updated, audit = repair_pricing(REPORT, plan, total, "", store, Scaling())
    assert updated["equipment"][0]["costing_options"]["extrapolation_exponent"] == 0.6
    assert audit[-1]["pricing_repair"]
    plan["equipment"][0]["unit_conversion"]["input_provenance"]["residence_time_h"][
        "status"
    ] = "user_input"
    original = copy.deepcopy(plan)
    preserved, audit = repair_pricing(REPORT, plan, total, "", store, Scaling())
    assert preserved == original and not audit


def test_prompt_requires_all_five_conversion_matching_skills(tmp_path):
    class Skills(Provider):
        def generate(self, **kw):
            for phrase in [
                "Exact unit and parameter matching",
                "Semantic matching",
                "Chemical engineering knowledge",
                "Contextual reasoning",
                "Engineering validation",
            ]:
                assert phrase in kw["instructions"]
            return super().generate(**kw)

    plan, _ = resolve(
        REPORT,
        {"equipment": [selected()]},
        "",
        Store(tmp_path / "skills.sqlite"),
        Skills(),
        True,
    )
    assert plan["equipment"][0]["unit_conversion"]["enabled"]


def test_semantic_throughput_synonym_requires_correct_physical_dimension():
    from backend.equipment_costing.unit_conversion.bridges.automatic import (
        direct_maximum,
    )

    report = copy.deepcopy(REPORT)
    report["entities"][0]["values"] = [
        {
            "id": "capacity",
            "property": "volumetric_throughput",
            "normalized_value": 5,
            "normalized_unit": "m3/h",
            "status": "verified",
        }
    ]
    row = {"equipment_key": "e", "curve_id": "N501-WATER-PACKAGED_RO"}
    spec = direct_maximum(report, row)
    assert spec["method"] == "direct" and spec["measurement_id"] == "capacity"
    report["entities"][0]["values"][0]["normalized_unit"] = "m3"
    assert direct_maximum(report, row) is None  # inventory volume is not throughput


def test_gauge_pressure_difference_and_absolute_gas_pressure():
    observations = [
        {
            "id": "p1",
            "property": "pressure",
            "entity_key": "s1",
            "value": 1,
            "unit": "bar_gauge",
        },
        {
            "id": "p2",
            "property": "pressure",
            "entity_key": "s2",
            "value": 3,
            "unit": "bar_gauge",
        },
    ]
    inputs, _ = derive(
        [
            {
                "name": "differential_pressure_bar",
                "method": "pressure_difference",
                "measurement_ids": ["p1", "p2"],
            }
        ],
        observations,
        {},
        {},
    )
    assert inputs["differential_pressure_bar"] == 2
    with pytest.raises(ValueError):
        derive(
            [
                {
                    "name": "absolute_pressure_bar",
                    "method": "absolute_pressure",
                    "measurement_ids": ["p1"],
                }
            ],
            observations,
            {},
            {},
        )
    inputs, _ = derive(
        [
            {
                "name": "absolute_pressure_bar",
                "method": "absolute_pressure",
                "measurement_ids": ["p1"],
            }
        ],
        observations,
        {},
        {"atmospheric_pressure_pa": 101325},
    )
    assert inputs["absolute_pressure_bar"] == pytest.approx(2.01325)


def test_ambiguous_configuration_with_candidates_can_receive_assumptions(tmp_path):
    row = {
        "equipment_key": "e",
        "curve_id": None,
        "matching": {
            "match_status": "ambiguous",
            "conceptual_validation": "uncertain",
            "model_scope": "equipment",
            "candidate_model_ids": ["G258-004"],
            "reason": "Vessel family known, configuration uncertain",
        },
    }
    plan, audit = resolve(
        REPORT,
        {"equipment": [row]},
        "Water holding vessel",
        Store(tmp_path / "ambiguous.sqlite"),
        Provider(),
        True,
    )
    assert plan["equipment"][0]["unit_conversion"]["enabled"]
    assert audit[-1]["status"] == "converted_with_explicit_basis"


def test_stream_descriptions_and_required_conventions_reach_planner(tmp_path):
    report = copy.deepcopy(REPORT)
    report["entities"][1]["values"].append(
        {
            "id": "description",
            "property": "description",
            "normalized_value": "Wet product leaving biological reactor",
            "sheet": "Balance",
            "cell": "A10",
            "status": "verified",
        }
    )

    class Context(Provider):
        def generate(self, **kw):
            item = kw["context"]["equipment"][0]
            assert (
                item["stream_context"][0]["descriptions"][0]["text"]
                == "Wet product leaving biological reactor"
            )
            assert item["candidate_inputs"][0]["required_unit_conventions"]
            return super().generate(**kw)

    plan, _ = resolve(
        report,
        {"equipment": [selected()]},
        "",
        Store(tmp_path / "context.sqlite"),
        Context(),
        True,
    )
    assert plan["equipment"][0]["unit_conversion"]["enabled"]
