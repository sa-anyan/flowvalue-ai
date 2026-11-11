"""TRACE01: identity/provenance checks only; retained fixtures supply numerics."""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import types
from unittest.mock import patch
import pytest
from backend.engineering_sizing.registry import METHODS, calculate
from backend.engineering_sizing.adapter import derive
from backend.engineering_sizing.versioning import METHOD_VERSIONS, method_metadata
from backend.equipment_costing.unit_conversion import convert, identify_unit
from backend.equipment_costing.unit_conversion.bridges import (
    mechanical,
    production_sizing,
    liquid,
)
from backend.equipment_costing.unit_conversion.bridges.service import evaluate

ROOT = Path(__file__).resolve().parents[2]
NATIVE = json.loads(
    (ROOT / "backend/tests/fixtures/sizing_verification/references.json").read_text()
)
EXTRAS = [
    x
    for x in json.loads(
        (
            ROOT
            / "docs/verification/phase1/method_acceptance/evidence/additional_references.json"
        ).read_text()
    )
    if x["method"] in {"vessel_mass", "vessel_productivity", "mixing_power"}
]
EXPECTED_IDS = {
    "ion_exchange_capacity",
    "vaporizer_area",
    "gas_compression",
    "phase_change_duty",
    "evaporated_water",
    "ion_exchange_ebct",
    "vessel_hold_up",
    "pump_duty",
    "exchanger_area",
    "filter_area",
    "gas_volume",
    "dryer_chamber",
    "vessel_mass",
    "vessel_productivity",
    "mixing_power",
}


def check_metadata(data, method, layer):
    assert data["method_id"] == method
    assert data["method_version"] == "1.0.0"
    assert data["execution_layer"] == layer
    assert data["fingerprint_scheme"] == "flowvalue-loaded-engineering-v1"
    assert data["implementation_fingerprint"].startswith("sha256:")
    assert len(data["implementation_fingerprint"]) == 71
    assert not any(
        x in data for x in ["path", "timestamp", "git_head", "source_filename"]
    )


def cv(v, u, t=None):
    if v == "quantity":
        return identify_unit(u).quantity
    result = convert(v, u, t)
    assert result.value is not None
    return result.value


def synthetic_report(prop="volume_flow", value=10, unit="m3/h"):
    return {
        "entities": [
            {
                "key": "e",
                "kind": "equipment",
                "identifier": "E1",
                "stream_keys": ["s"],
                "values": [],
            },
            {
                "key": "s",
                "kind": "material",
                "identifier": "S1",
                "values": [
                    {
                        "id": "Trace!B7",
                        "property": prop,
                        "normalized_value": value,
                        "normalized_unit": unit,
                        "status": "verified",
                        "sheet": "Trace",
                        "cell": "B7",
                    }
                ],
            },
        ]
    }


def test_exact_declared_version_map():
    assert set(METHOD_VERSIONS) == EXPECTED_IDS
    assert set(METHODS) == EXPECTED_IDS - {
        "vessel_mass",
        "vessel_productivity",
        "mixing_power",
    }
    assert set(METHOD_VERSIONS.values()) == {"1.0.0"}
    with pytest.raises(KeyError):
        method_metadata("unregistered", calculate)


@pytest.mark.parametrize("r", NATIVE, ids=lambda r: r["method"])
def test_native_versions_are_stable_and_numerics_provenance_unchanged(r):
    params = copy.deepcopy(r["parameters"])
    raw = METHODS[r["method"]]["calculator"](r["value"], params)
    first = calculate(r["method"], r["value"], params)
    second = calculate(r["method"], r["value"], params)
    assert first == second
    assert first[:2] == raw[:2]
    assert {k: v for k, v in first[2].items() if k != "engineering_method"} == raw[2]
    assert first[0] == pytest.approx(
        float(r["expected"]), rel=r["relative_tolerance"], abs=r["absolute_tolerance"]
    )
    check_metadata(first[2]["engineering_method"], r["method"], "native")
    assert (
        calculate(r["method"], r["value"] * 2, params)[2]["engineering_method"]
        == first[2]["engineering_method"]
    )
    assert params == r["parameters"]


@pytest.mark.parametrize("r", NATIVE, ids=lambda r: r["method"])
def test_adapter_exposes_version_and_retains_source_assumptions(r):
    d = METHODS[r["method"]]
    report = synthetic_report(d["input"], r["value"], d["unit"])
    spec = {
        "method": r["method"],
        "stream_key": "s",
        "parameters": copy.deepcopy(r["parameters"]),
    }
    before = copy.deepcopy((report, spec))
    value, unit, audit = derive(spec, report)
    check_metadata(audit["engineering_method"], r["method"], "sizing_adapter")
    check_metadata(audit["calculation"]["engineering_method"], r["method"], "native")
    assert audit["source_evidence"] == ["Trace!B7"] and audit["assumptions"] == spec
    assert value == pytest.approx(
        float(r["expected"]), rel=r["relative_tolerance"], abs=r["absolute_tolerance"]
    )
    assert unit == r["unit"]
    assert (report, spec) == before
    assert derive(spec, report)[2]["engineering_method"] == audit["engineering_method"]


@pytest.mark.parametrize("r", EXTRAS, ids=lambda r: r["method"])
def test_supplemental_versions_and_independent_results(r):
    if r["method"] == "vessel_mass":
        result = mechanical.evaluate(r["inputs"])
    elif r["method"] == "vessel_productivity":
        result = production_sizing.vessel_productivity(r["inputs"])
    else:
        result = liquid.evaluate(
            "mixing_power", r["value"], r["source_unit"], r["inputs"], cv
        )
    check_metadata(result[2]["engineering_method"], r["method"], "supplemental")
    assert result[0] == pytest.approx(
        float(r["expected"]), rel=r["rtol"], abs=r["atol"]
    )
    assert result[1] == r["unit"] and result[2]["formula"]


@pytest.mark.parametrize("r", EXTRAS, ids=lambda r: r["method"])
def test_equipment_bridge_top_level_and_nested_version_metadata(r):
    quantity, unit = {
        "vessel_mass": ("mass", "kg"),
        "vessel_productivity": ("volume", "m3"),
        "mixing_power": ("power", "kW"),
    }[r["method"]]
    spec = {
        "model_id": "trace-contract",
        "method": r["method"],
        "measurement_id": "Trace!B7",
        "inputs": copy.deepcopy(r["inputs"]),
        "input_provenance": {"reviewer": "synthetic-test"},
    }
    before = copy.deepcopy(spec)
    with patch(
        "backend.equipment_costing.unit_conversion.bridges.service.model_contract",
        return_value=({"id": "trace-contract"}, {"quantity": quantity}, unit),
    ):
        result = evaluate(synthetic_report(), "e", spec)
        again = evaluate(synthetic_report(), "e", spec)
    check_metadata(result["engineering_method"], r["method"], "equipment_bridge")
    check_metadata(
        result["equation"]["engineering_method"], r["method"], "supplemental"
    )
    assert result["engineering_method"] == again["engineering_method"]
    assert result["size"] == pytest.approx(
        float(r["expected"]), rel=r["rtol"], abs=r["atol"]
    )
    assert (
        result["original_user_inputs"] == spec["inputs"]
        and result["input_provenance"] == spec["input_provenance"]
    )
    assert spec == before


def test_fingerprints_follow_actual_helper_code_and_constants(monkeypatch):
    from backend.engineering_sizing import pumps, common

    reference = next(r for r in NATIVE if r["method"] == "pump_duty")
    base = calculate("pump_duty", reference["value"], reference["parameters"])
    monkeypatch.setattr(pumps, "PSI", pumps.PSI * 2)
    changed = calculate("pump_duty", reference["value"], reference["parameters"])
    assert changed[0] == base[0] / 2
    assert changed[2]["engineering_method"] != base[2]["engineering_method"]
    original = common.reject_boolean

    def changed_guard(value, name):
        return original(value, name)

    monkeypatch.setattr(common, "reject_boolean", changed_guard)
    helper_changed = calculate("pump_duty", reference["value"], reference["parameters"])
    assert helper_changed[0] == changed[0]
    assert helper_changed[2]["engineering_method"] != changed[2]["engineering_method"]


def test_selected_callable_and_transitive_mixing_helper_changes_are_detected(
    monkeypatch,
):
    from backend.engineering_sizing import vessels

    c = next(x for x in EXTRAS if x["method"] == "mixing_power")
    base = liquid.evaluate(
        "mixing_power", c["value"], c["source_unit"], c["inputs"], cv
    )[2]["engineering_method"]
    original = vessels.calculate

    def replacement(value, inputs):
        return original(value, inputs)

    monkeypatch.setitem(METHODS["vessel_hold_up"], "calculator", replacement)
    changed = liquid.evaluate(
        "mixing_power", c["value"], c["source_unit"], c["inputs"], cv
    )[2]["engineering_method"]
    assert changed != base


def test_explicit_version_changes_are_detected(monkeypatch):
    from backend.engineering_sizing import versioning

    before = method_metadata("vessel_mass", mechanical.evaluate)
    monkeypatch.setattr(
        versioning, "METHOD_VERSIONS", {**METHOD_VERSIONS, "vessel_mass": "1.0.1"}
    )
    after = method_metadata("vessel_mass", mechanical.evaluate)
    assert after["method_version"] == "1.0.1"
    assert after["implementation_fingerprint"] != before["implementation_fingerprint"]


def loaded_function(source, filename):
    namespace = {"__name__": "backend.engineering_sizing.trace_fixture"}
    exec(compile(source, filename, "exec"), namespace)
    return namespace["f"]


def test_paths_debug_lines_and_unexecuted_file_edits_do_not_misidentify_loaded_code(
    tmp_path,
):
    source = "def f(x):\n    return x * 2\n"
    path = tmp_path / "first.py"
    path.write_text(source)
    first = loaded_function(path.read_text(), str(path))
    relocated = loaded_function("\n\n" + source, "/different/install/second.py")
    a = method_metadata("vessel_mass", first)
    assert method_metadata("vessel_mass", relocated) == a
    path.write_text("def f(x):\n    return x * 3\n")
    assert method_metadata("vessel_mass", first) == a  # old loaded code still executes
    reloaded = loaded_function(path.read_text(), str(path))
    assert reloaded(2) == 6 and first(2) == 4
    assert method_metadata("vessel_mass", reloaded) != a


def test_cross_process_hash_seed_stability():
    code = "from backend.engineering_sizing.registry import calculate; print(calculate('vessel_hold_up',10,{'residence_time_h':2,'working_fraction':.8})[2]['engineering_method']['implementation_fingerprint'])"
    outputs = []
    for seed in ["1", "321"]:
        env = {
            k: v
            for k, v in os.environ.items()
            if not any(
                x in k.upper()
                for x in [
                    "KEY",
                    "TOKEN",
                    "SECRET",
                    "PASSWORD",
                    "DATABASE",
                    "OPENAI",
                    "SUPABASE",
                ]
            )
        }
        env["PYTHONHASHSEED"] = seed
        outputs.append(
            subprocess.check_output(
                [sys.executable, "-c", code], cwd=ROOT, env=env, text=True
            ).strip()
        )
    assert outputs[0] == outputs[1]


def test_unit_normalization_and_ranges_remain_separate_from_version_identity():
    spec = {
        "method": "vessel_hold_up",
        "stream_key": "s",
        "parameters": {
            "residence_time_h": {
                "value": 30,
                "low": 15,
                "high": 60,
                "unit": "min",
                "source": {"cell": "D4"},
            },
            "working_fraction": 0.8,
        },
    }
    value, unit, audit = derive(spec, synthetic_report())
    assert value == 6.25 and unit == "m3"
    assert audit["size_range"]["low"] == 3.125 and audit["size_range"]["high"] == 12.5
    assert len(audit["parameter_unit_conversions"]) == 3
    assert audit["parameter_unit_conversions"][0]["conversion"]["original"][
        "source"
    ] == {"cell": "D4"}
    changed = copy.deepcopy(spec)
    changed["parameters"]["residence_time_h"]["value"] = 45
    assert (
        derive(changed, synthetic_report())[2]["engineering_method"]
        == audit["engineering_method"]
    )


def test_module_numeric_constants_are_part_of_the_executed_identity(monkeypatch):
    case = next(x for x in EXTRAS if x["method"] == "vessel_mass")
    before = mechanical.evaluate(case["inputs"])
    monkeypatch.setattr(mechanical.math, "pi", 3.0)
    after = mechanical.evaluate(case["inputs"])
    assert before[0] != after[0]
    assert before[2]["engineering_method"] != after[2]["engineering_method"]


def test_adapter_nested_global_helpers_and_normalization_changes_are_detected(
    monkeypatch,
):
    from backend.engineering_sizing import adapter
    from backend.equipment_costing.unit_conversion import sizing_parameters

    spec = {
        "method": "vessel_hold_up",
        "stream_key": "s",
        "parameters": {"residence_time_h": 2, "working_fraction": 0.8},
    }
    base = derive(spec, synthetic_report())[2]["engineering_method"]
    original = adapter.observation

    def alternate_observation(*args, **kwargs):
        return original(*args, **kwargs)

    monkeypatch.setattr(adapter, "observation", alternate_observation)
    changed = derive(spec, synthetic_report())[2]["engineering_method"]
    assert base != changed
    normalizer = sizing_parameters.normalize_parameters

    def alternate_normalizer(*args, **kwargs):
        return normalizer(*args, **kwargs)

    monkeypatch.setattr(sizing_parameters, "normalize_parameters", alternate_normalizer)
    assert derive(spec, synthetic_report())[2]["engineering_method"] != changed


@pytest.mark.parametrize(
    "recipe,method_id,quantity,target,prop,value,unit,inputs,expected",
    [
        (
            "filter_area",
            "filter_area",
            "area",
            "m2",
            "volume_flow",
            10,
            "m3/h",
            {"hydraulic_loading_m_h": 2},
            5,
        ),
        (
            "vessel_volume",
            "vessel_hold_up",
            "volume",
            "m3",
            "volume_flow",
            10,
            "m3/h",
            {"residence_time_h": 2, "working_fraction": 0.8},
            25,
        ),
        (
            "exchanger_area",
            "exchanger_area",
            "area",
            "m2",
            "heat_duty",
            100,
            "kW",
            {"overall_u_w_m2_k": 500, "lmtd_k": 20, "lmtd_correction": 1},
            10,
        ),
    ],
)
def test_native_bridge_recipe_identity_mapping(
    recipe, method_id, quantity, target, prop, value, unit, inputs, expected
):
    spec = {
        "model_id": "trace-contract",
        "method": recipe,
        "measurement_id": "Trace!B7",
        "inputs": inputs,
    }
    with patch(
        "backend.equipment_costing.unit_conversion.bridges.service.model_contract",
        return_value=({"id": "trace-contract"}, {"quantity": quantity}, target),
    ):
        result = evaluate(synthetic_report(prop, value, unit), "e", spec)
    assert result["size"] == pytest.approx(expected)
    assert result["source_measurements"][0]["cell"] == "B7"
    check_metadata(result["engineering_method"], method_id, "equipment_bridge")
    check_metadata(result["equation"]["engineering_method"], method_id, "native")


def test_native_output_validator_is_versioned_even_if_kernel_alias_is_unchanged(
    monkeypatch,
):
    from backend.engineering_sizing import common

    r = next(x for x in NATIVE if x["method"] == "gas_volume")
    before = calculate(r["method"], r["value"], r["parameters"])
    original = common.positive

    def changed_validator(*args, **kwargs):
        return original(*args, **kwargs)

    monkeypatch.setattr(common, "positive", changed_validator)
    after = calculate(r["method"], r["value"], r["parameters"])
    assert before[:2] == after[:2]
    assert before[2]["engineering_method"] != after[2]["engineering_method"]


def test_bridge_local_preparation_helpers_are_in_the_fingerprint(monkeypatch):
    from backend.equipment_costing.unit_conversion.bridges import derivations

    spec = {
        "model_id": "trace-contract",
        "method": "vessel_volume",
        "measurement_id": "Trace!B7",
        "inputs": {"residence_time_h": 2, "working_fraction": 0.8},
    }
    with patch(
        "backend.equipment_costing.unit_conversion.bridges.service.model_contract",
        return_value=({"id": "trace-contract"}, {"quantity": "volume"}, "m3"),
    ):
        base = evaluate(synthetic_report(), "e", spec)
        original = derivations.derive

        def changed_preparation(*args, **kwargs):
            return original(*args, **kwargs)

        monkeypatch.setattr(derivations, "derive", changed_preparation)
        changed = evaluate(synthetic_report(), "e", spec)
    assert base["size"] == changed["size"]
    assert base["engineering_method"] != changed["engineering_method"]


def test_fingerprint_algorithm_code_is_itself_versioned(monkeypatch):
    from backend.engineering_sizing import versioning

    before = method_metadata("vessel_mass", mechanical.evaluate)
    original = versioning._Encoder.encode

    def changed_encoding(self, value):
        return original(self, value)

    monkeypatch.setattr(versioning._Encoder, "encode", changed_encoding)
    after = method_metadata("vessel_mass", mechanical.evaluate)
    assert before["implementation_fingerprint"] != after["implementation_fingerprint"]
