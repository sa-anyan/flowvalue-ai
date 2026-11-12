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
        "thermal_basis": None,
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
            assert kw["context"]["review_role"] == (
                "independent_assumption_review"
                if self.calls > 1
                else "initial_input_resolution"
            )
            assert (
                "Independent preliminary-estimate review:" in kw["instructions"]
            ) == (self.calls > 1)
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


def test_strict_domain_failure_reopens_reviewed_models_without_touching_neighbor(
    tmp_path,
):
    from types import SimpleNamespace
    from backend.equipment_costing.unit_conversion.bridges.automatic import (
        repair_pricing,
    )

    failed = selected()
    failed.update(
        curve_id="openpytea:vertical_cylinder_perry_1996",
        matching={
            "match_status": "matched",
            "conceptual_validation": "suitable",
            "candidate_model_ids": [
                "openpytea:vertical_cylinder_perry_1996",
                "G258-004",
            ],
        },
        unit_conversion={
            "origin": "llm_selected_python_equation",
            "inputs": {"residence_time_h": 2},
        },
    )
    neighbor = {"equipment_key": "neighbor", "manual_price": {"amount": 123}}
    total = SimpleNamespace(
        equipment=[
            SimpleNamespace(
                equipment_cost=None,
                amount=None,
                parsed_source={"equipment_key": "e"},
                issues=["MODEL_OUT_OF_RANGE: size outside published bounds"],
            )
        ]
    )

    def repair(report, plan, *args, **kwargs):
        retry = plan["equipment"][0]
        assert not retry.get("curve_id")
        assert retry["matching"]["candidate_model_ids"] == ["G258-004"]
        assert kwargs["repair_feedback"][0]["previous_conversion"]["inputs"] == {
            "residence_time_h": 2
        }
        retry.update(curve_id="G258-004", unit_conversion={"enabled": True})
        return plan, []

    with patch(
        "backend.equipment_costing.unit_conversion.bridges.automatic.resolve",
        side_effect=repair,
    ):
        updated, _ = repair_pricing(
            REPORT,
            {"equipment": [failed, neighbor]},
            total,
            "",
            Store(tmp_path / "domain.db"),
            attempt=2,
        )
    assert updated["equipment"][0]["curve_id"] == "G258-004"
    assert updated["equipment"][1] == neighbor
    assert failed["curve_id"] == "openpytea:vertical_cylinder_perry_1996"


def test_non_garrett_extrapolation_options_rejected_before_cost_handoff(tmp_path):
    class UnsupportedOptions(Provider):
        def generate(self, **kwargs):
            d = decision()
            d.update(
                model_id="openpytea:vertical_cylinder_perry_1996",
                extrapolation_exponent=0.6,
                extrapolation_rationale="Not supported by this library",
            )
            return {"decisions": [d]}

    plan = {
        "equipment": [
            {"equipment_key": "e", "curve_id": "openpytea:vertical_cylinder_perry_1996"}
        ]
    }
    updated, audit = resolve(
        REPORT, plan, "", Store(tmp_path / "options.db"), UnsupportedOptions(), True
    )
    assert not updated["equipment"][0].get("unit_conversion", {}).get("enabled")
    assert any(
        "does not support Garrett extrapolation" in a.get("reason", "") for a in audit
    )


def test_alternative_volume_model_keeps_physical_assumptions(tmp_path):
    store = Store(tmp_path / "retain-basis.db")
    original, _ = resolve(
        REPORT, {"equipment": [selected()]}, "", store, Provider(), True
    )
    previous = original["equipment"][0]["unit_conversion"]

    class DifferentGuess(Provider):
        def generate(self, **kwargs):
            d = decision()
            d["model_id"] = "G258-008"
            d["assumptions"][1]["value"] = 999
            return {"decisions": [d]}

    retry = selected()
    retry["curve_id"] = "G258-008"
    updated, audit = resolve(
        REPORT,
        {"equipment": [retry]},
        "",
        store,
        DifferentGuess(),
        True,
        repair_feedback=[
            {
                "equipment_key": "e",
                "preserve_physical_basis": True,
                "previous_conversion": previous,
            }
        ],
    )
    spec = updated["equipment"][0]["unit_conversion"]
    assert spec["model_id"] == "G258-008"
    assert spec["inputs"]["residence_time_h"] == 2
    assert any(a["status"] == "retained_physical_basis" for a in audit)


def test_ai_conceptual_first_choice_does_not_hide_reviewed_alternatives(tmp_path):
    row = selected()
    row.update(
        curve_id="G258-008",
        matching={
            "selected_model_id": "G258-008",
            "review_available": True,
            "candidate_model_ids": ["G258-008", "G258-004"],
        },
    )

    class Alternative(Provider):
        def generate(self, **kwargs):
            allowed = kwargs["schema"]["properties"]["decisions"]["items"][
                "properties"
            ]["model_id"]["enum"]
            assert "G258-004" in allowed and "G258-008" in allowed
            return super().generate(**kwargs)

    result, _ = resolve(
        REPORT,
        {"equipment": [row]},
        "",
        Store(tmp_path / "alternatives.db"),
        Alternative(),
        True,
    )
    assert result["equipment"][0]["curve_id"] == "G258-004"
    assert result["equipment"][0]["unit_conversion"]["enabled"]


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


def test_bound_schema_has_independent_identifier_fields_and_valid_source_ids():
    from backend.equipment_costing.unit_conversion.bridges.automatic import (
        decision_schema,
    )
    from backend.equipment_costing.unit_conversion.bridges.service import (
        describe,
        PARAMETERS,
    )

    c = describe(REPORT, "e", "G258-004")
    schema = decision_schema(
        [
            {
                "equipment_key": "e",
                "candidate_inputs": [c],
                "measurements": c["measurements"],
            }
        ]
    )
    fields = schema["properties"]["decisions"]["items"]["properties"]
    assert fields["equipment_key"]["enum"] == ["e"]
    assert "enum" not in fields["rationale"]
    source_choices = fields["thermal_basis"]["properties"]["source_choices"]
    assert "source_choices" in fields["thermal_basis"]["required"]
    assert set(source_choices["items"]["properties"]["measurement_id"]["enum"]) == {
        v["id"] for v in c["measurements"]
    }
    assert "enum" not in source_choices["items"]["properties"]["rationale"]
    assert set(fields["assumptions"]["items"]["properties"]["name"]["enum"]) == set(
        PARAMETERS
    )
    assert set(fields["measurement_id"]["enum"]) == {
        v["id"] for v in c["measurements"]
    } | {None}
    assert set(
        fields["thermal_basis"]["properties"]["hot_inlet_stream_key"]["enum"]
    ) == {v["entity_key"] for v in c["measurements"]} | {None}


def test_invalid_source_on_one_equipment_does_not_clear_good_neighbor(tmp_path):
    report = copy.deepcopy(REPORT)
    second = copy.deepcopy(report["entities"][0])
    second.update(key="e2", identifier="TK-2")
    report["entities"].append(second)

    class Mixed(Provider):
        def generate(self, **kw):
            result = []
            for item in kw["context"]["equipment"]:
                d = decision(item["equipment_key"])
                if item["equipment_key"] == "e2":
                    d["measurement_id"] = "invented"
                result.append(d)
            return {"decisions": result}

    result, audit = resolve(
        report,
        {"equipment": [selected(), selected("e2")]},
        "",
        Store(tmp_path / "db"),
        Mixed(),
        True,
    )
    bykey = {r["equipment_key"]: r for r in result["equipment"]}
    assert bykey["e"]["unit_conversion"]["enabled"]
    assert not bykey["e2"].get("unit_conversion")
    assert any(
        a["equipment_key"] == "e2" and a["status"] == "input_resolution_unresolved"
        for a in audit
    )


def test_failed_batch_retries_individually_without_losing_neighbor(tmp_path):
    report = copy.deepcopy(REPORT)
    second = copy.deepcopy(report["entities"][0])
    second.update(key="e2", identifier="TK-2")
    report["entities"].append(second)

    class Flaky(Provider):
        calls = []

        def generate(self, **kw):
            keys = [e["equipment_key"] for e in kw["context"]["equipment"]]
            self.calls.append(keys)
            if len(keys) > 1 or keys == ["e2"]:
                raise TimeoutError("Synthetic transport failure")
            return {"decisions": [decision(keys[0])]}

    provider = Flaky()
    result, audit = resolve(
        report,
        {"equipment": [selected(), selected("e2")]},
        "",
        Store(tmp_path / "db"),
        provider,
        True,
    )
    bykey = {r["equipment_key"]: r for r in result["equipment"]}
    assert bykey["e"]["unit_conversion"]["enabled"]
    assert not bykey["e2"].get("unit_conversion")
    assert provider.calls == [["e", "e2"], ["e"], ["e2"]]
    assert any(a.get("transport_retry") and a["equipment_key"] == "e" for a in audit)


def test_no_measurements_produces_valid_schema_not_empty_enum():
    from backend.equipment_costing.unit_conversion.bridges.automatic import (
        decision_schema,
    )

    schema = decision_schema(
        [
            {
                "equipment_key": "e",
                "candidate_inputs": [{"model_id": "m"}],
                "measurements": [],
            }
        ]
    )

    def visit(value):
        if isinstance(value, dict):
            assert value.get("enum") != []
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(schema)
    fields = schema["properties"]["decisions"]["items"]["properties"]
    assert fields["derivations"]["maxItems"] == 0
    assert fields["measurement_id"]["enum"] == [None]


def test_thermal_adapter_owns_lmtd_and_retains_redundant_ai_binding_audit(tmp_path):
    from backend.tests.test_heat_exchanger_basis import fixture

    observations, basis, inputs = fixture()
    report = {
        "entities": [
            {
                "kind": "equipment",
                "key": "e",
                "identifier": "HE-9",
                "values": [],
                "stream_keys": ["hot_inlet", "hot_outlet", "cold_inlet", "cold_outlet"],
            }
        ]
    }
    for role in ["hot_inlet", "hot_outlet", "cold_inlet", "cold_outlet"]:
        report["entities"].append(
            {
                "kind": "material",
                "key": role,
                "identifier": role,
                "values": [
                    {
                        "id": v["id"],
                        "property": v["property"],
                        "normalized_value": v["value"],
                        "normalized_unit": v["unit"],
                        "status": "verified",
                        "sheet": "Balance",
                        "cell": "A1",
                    }
                    for v in observations
                    if v["entity_key"] == role
                ],
            }
        )

    class Thermal(Provider):
        def generate(self, **kw):
            d = decision()
            d.update(
                model_id="G286-091",
                method="exchanger_area",
                measurement_id=None,
                thermal_basis=basis,
                assumptions=[
                    {
                        "name": n,
                        "value": v,
                        "unit": u,
                        "rationale": "Synthetic thermal scenario",
                        "limitations": "Preliminary",
                    }
                    for n, v, u in [
                        ("overall_u_w_m2_k", 500, "W/m2/K"),
                        ("lmtd_correction", 1, "fraction"),
                    ]
                ],
                derivations=[
                    {
                        "name": "lmtd_k",
                        "method": "lmtd_countercurrent",
                        "measurement_ids": [
                            "hot_inlettemperature",
                            "cold_inlettemperature",
                            "cold_outlettemperature",
                        ],
                    }
                ],
            )
            return {"decisions": [d]}

    result, audit = resolve(
        report,
        {"equipment": [{"equipment_key": "e", "curve_id": "G286-091"}]},
        "",
        Store(tmp_path / "db"),
        Thermal(),
        True,
    )
    spec = result["equipment"][0]["unit_conversion"]
    assert audit[-1]["status"] == "converted_with_explicit_basis"
    assert len(spec["omitted_redundant_derivations"]) == 1
    assert not any(b["method"].startswith("lmtd_") for b in spec["derivations"])
    assert evaluate(report, "e", spec)["size"] > 0


def test_stream_composition_reaches_engineer_with_component_identity_and_lineage(
    tmp_path,
):
    report = copy.deepcopy(REPORT)
    report["entities"][1]["values"].append(
        {
            "id": "water-component",
            "property": "component_mass_flow",
            "component": "water",
            "normalized_value": 950,
            "normalized_unit": "kg/h",
            "status": "verified",
            "sheet": "Balance",
            "cell": "C9",
        }
    )

    class Context(Provider):
        def generate(self, **kw):
            composition = kw["context"]["equipment"][0]["stream_context"][0][
                "composition"
            ]
            assert composition[0]["component"] == "water"
            assert composition[0]["value"] == 950
            assert composition[0]["cell"] == "C9"
            # It is context, not a replacement for total-stream hydraulic flow.
            assert "water-component" not in [
                v["id"] for v in kw["context"]["equipment"][0]["measurements"]
            ]
            return super().generate(**kw)

    result, _ = resolve(
        report, {"equipment": [selected()]}, "", Store(tmp_path / "db"), Context(), True
    )
    assert result["equipment"][0]["unit_conversion"]["enabled"]


def test_binding_repairs_preserve_failed_proposal_and_stop_at_three_attempts(tmp_path):
    class BadBinding(Provider):
        calls = 0

        def generate(self, **kw):
            self.calls += 1
            assert kw["context"]["repair_depth"] == self.calls - 1
            if self.calls > 1:
                feedback = kw["context"]["repair_feedback"]
                assert (
                    feedback[-1]["failed_proposal"]["measurement_id"] == "not-a-source"
                )
            proposal = decision()
            proposal["measurement_id"] = "not-a-source"
            return {"decisions": [proposal]}

    provider = BadBinding()
    plan, audit = resolve(
        REPORT,
        {"equipment": [selected()]},
        "",
        Store(tmp_path / "bounded.db"),
        provider,
        True,
    )
    assert provider.calls == 3
    assert not plan["equipment"][0].get("unit_conversion")
    assert [
        a["attempt"] for a in audit if a["status"] == "input_resolution_unresolved"
    ] == [1, 2, 3]


def test_third_binding_attempt_can_recover_without_restarting_the_register(tmp_path):
    class Recover(Provider):
        calls = 0

        def generate(self, **kw):
            self.calls += 1
            proposal = decision()
            if self.calls < 3:
                proposal["measurement_id"] = "not-a-source"
            return {"decisions": [proposal]}

    provider = Recover()
    plan, audit = resolve(
        REPORT,
        {"equipment": [selected()]},
        "",
        Store(tmp_path / "recover.db"),
        provider,
        True,
    )
    assert provider.calls == 3
    assert plan["equipment"][0]["unit_conversion"]["enabled"]
    assert audit[-1]["status"] == "converted_with_explicit_basis"


def _range_failure_total(*keys):
    from types import SimpleNamespace

    return SimpleNamespace(
        equipment=[
            SimpleNamespace(
                equipment_cost=None,
                amount=None,
                parsed_source={"equipment_key": key},
                issues=["MODEL_OUT_OF_RANGE: size outside published bounds"],
            )
            for key in keys
        ]
    )


def _out_of_range_row(key, curve, candidates):
    row = selected(key)
    row.update(
        curve_id=curve,
        matching={
            "match_status": "matched",
            "conceptual_validation": "suitable",
            "candidate_model_ids": list(candidates),
        },
        unit_conversion={
            "enabled": True,
            "origin": "llm_selected_python_equation",
            "inputs": {"residence_time_h": 2},
        },
    )
    return row


def test_pricing_repair_does_not_call_ai_when_no_alternative_remains(tmp_path):
    """Charlie HE-101/HE-102 (11 Nov): once every reviewed candidate has failed its
    published range, repair records why instead of asking the AI again."""
    from backend.equipment_costing.unit_conversion.bridges.automatic import (
        repair_pricing,
    )

    model = "openpytea:double_pipe_hx_towler_2010"
    row = _out_of_range_row("e", model, [model])

    class NoCall(Provider):
        def generate(self, **kw):
            raise AssertionError("no reviewed alternative is left to offer")

    plan = {"equipment": [row]}
    updated, audit = repair_pricing(
        REPORT, plan, _range_failure_total("e"), "", Store(tmp_path / "x.db"), NoCall()
    )
    assert updated == plan
    assert audit == [
        {
            "equipment_key": "e",
            "status": "pricing_repair_exhausted",
            "reason": "MODEL_OUT_OF_RANGE: size outside published bounds",
            "excluded_model_ids": [model],
            "pricing_repair": True,
            "pricing_attempt": 1,
        }
    ]


def test_unresolved_pricing_repair_is_not_repeated_with_identical_inputs(tmp_path):
    """A refused repair is not re-sent unchanged on later pricing passes that run
    only because a neighbouring item was repaired; failed models stay excluded."""
    from backend.equipment_costing.unit_conversion.bridges.automatic import (
        repair_pricing,
    )

    stuck = _out_of_range_row(
        "e", "openpytea:double_pipe_seider_2013",
        ["openpytea:double_pipe_seider_2013", "openpytea:double_pipe_hx_towler_2010"],
    )
    fixable = _out_of_range_row("n", "G258-004", ["G258-004", "G258-008"])
    offered = []

    def fake_resolve(report, plan, *args, **kwargs):
        plan = copy.deepcopy(plan)
        for retry in plan["equipment"]:
            offered.append(
                (retry["equipment_key"], retry["matching"]["candidate_model_ids"])
            )
            if retry["equipment_key"] == "n" and len(offered) < 4:
                retry.update(curve_id="G258-008", unit_conversion={"enabled": True})
        return plan, [{"equipment_key": "e", "status": "input_resolution_unresolved"}]

    with patch(
        "backend.equipment_costing.unit_conversion.bridges.automatic.resolve",
        side_effect=fake_resolve,
    ), patch(
        "backend.blocks.equipment.calculation.calculate_equipment",
        return_value=(_range_failure_total("e", "n"), []),
    ):
        updated, audit = repair_pricing(
            REPORT,
            {"equipment": [stuck, fixable]},
            _range_failure_total("e", "n"),
            "",
            Store(tmp_path / "y.db"),
        )
    # "e" is asked once; "n" fails again on G258-008 and has nothing left.
    assert offered == [
        ("e", ["openpytea:double_pipe_hx_towler_2010"]),
        ("n", ["G258-008"]),
    ]
    assert updated["equipment"][0] == stuck
    exhausted = [a for a in audit if a["status"] == "pricing_repair_exhausted"]
    assert [a["equipment_key"] for a in exhausted] == ["n"]
    assert exhausted[0]["excluded_model_ids"] == ["G258-004", "G258-008"]
