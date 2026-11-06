"""Bulk parity against pinned upstream source, no LLM/network/parallelisation."""

import copy, csv, json, math
from dataclasses import replace
from pathlib import Path
import pandas as pd
import pytest
from backend.equipment_costing.indexes.openpytea.registry import (
    list_models,
    get_model,
    model_id,
    ROOT,
)
from backend.equipment_costing.indexes.openpytea.evaluators import evaluate
from backend.equipment_costing.indexes.openpytea.audit import audit, representative
from backend.tests.openpytea_reference.pinned import CostCorrelationDB
from backend.equipment_costing.registry import (
    estimate_cost,
    list_equipment_models,
    estimate_from_parsed_inputs,
)
from backend.equipment_costing.unit_conversion import ConversionContext, Measurement
from backend.equipment_costing.total_cost.calculator import calculate_total_cost
from backend.capex.connectors import prepare_capex_inputs
from backend.capex import calculate_capex
from backend.equipment_costing.cost_to_future.cost_translation import DEFAULT_POLICY

MODELS = list_models()
UPSTREAM = CostCorrelationDB(pd.read_csv(ROOT / "correlations.csv"))
CONTEXT = ConversionContext(
    input_gallon_basis="US",
    target_gallon_basis="US",
    input_ton_basis="short",
    target_ton_basis="short",
    input_gas_reference="Explicit synthetic standard conditions",
    target_gas_reference="Explicit synthetic standard conditions",
)


@pytest.mark.parametrize("model", MODELS, ids=[m["upstream_key"] for m in MODELS])
def test_every_imported_equation_parity(model):
    row = model["raw"]
    s = representative(row)
    s2 = representative(row, "s2") if row["form"] == "2-var power-law" else None
    expected, units, year = UPSTREAM.evaluate(row["key"], s, s2)
    assert units == 1
    assert int(model["source_year"]) == year
    assert evaluate(row, s, s2, allow_missing_bounds=True) == pytest.approx(
        expected, rel=1e-12
    )
    # Compare at each positive published boundary as well as representative input.
    for bound in ["s_lower", "s_upper"]:
        if row[bound] and float(row[bound]) > 0:
            value = float(row[bound])
            expected, units, _ = UPSTREAM.evaluate(row["key"], value, s2)
            if expected > 0 and math.isfinite(expected):
                assert evaluate(
                    row, value, s2, allow_missing_bounds=True
                ) == pytest.approx(expected, rel=1e-12)
            else:
                with pytest.raises(ValueError):
                    evaluate(row, value, s2, allow_missing_bounds=True)


@pytest.mark.parametrize(
    "model",
    [m for m in MODELS if m["status"] != "disabled"],
    ids=lambda m: m["upstream_key"],
)
def test_every_available_adapter_preserves_source_and_units(model):
    row = model["raw"]
    s = representative(row)
    options = {"allow_unverified": True, "unit_context": CONTEXT}
    if len(model["input_requirements"]) > 1:
        options.update(
            second_size=representative(row, "s2"),
            second_size_unit=model["input_requirements"][1]["unit"],
        )
    result = estimate_cost(model["id"], s, size_unit=model["size_unit"], **options)
    expected, _, _ = UPSTREAM.evaluate(row["key"], s, options.get("second_size"))
    assert result.estimate.amount == pytest.approx(expected, rel=1e-12)
    assert result.estimate.cost_scope == model["cost_scope"]
    assert (
        result.evidence["source_commit"]
        == json.loads((ROOT / "sources.json").read_text())["commit"]
    )
    assert result.evidence["upstream_escalation"] is False
    assert result.evidence["upstream_parallelisation"] is False


def test_import_audit_and_idempotency():
    from backend.equipment_costing.indexes.openpytea.import_catalogue import (
        import_snapshot,
    )
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        # The exact pinned source files are intentionally external to this test;
        # hash rejection is tested without downloading anything.
        for name in [
            "LICENSE",
            "cost_correlations.csv",
            "cepci_values.csv",
            "equipment.py",
        ]:
            Path(folder, name).write_text("wrong")
        with pytest.raises(ValueError, match="hash mismatch"):
            import_snapshot(folder)
    a = audit()
    assert a == audit()
    assert a["counts"]["imported"] == 421 and a["counts"]["categories"] == 35
    assert a["counts"]["mathematically_valid_representative"] == 421
    assert len({m["id"] for m in MODELS}) == 421
    assert len(list_equipment_models("openpytea")) == 421
    assert list_equipment_models()[0]["id"].startswith("G")
    assert all(m["raw"]["key"] == m["upstream_key"] for m in MODELS)


@pytest.mark.parametrize(
    "model",
    [m for m in MODELS if m["status"] == "disabled"],
    ids=lambda m: m["upstream_key"],
)
def test_disabled_rows_are_visible_and_not_automatically_priced(model):
    assert get_model(model["id"])["disabled_reasons"]
    with pytest.raises(ValueError, match="MODEL_DISABLED"):
        estimate_cost(
            model["id"],
            representative(model["raw"]),
            size_unit=model["size_unit"],
            allow_unverified=True,
        )


@pytest.mark.parametrize("value", [0, -1, None, True, float("nan"), float("inf")])
def test_invalid_size(value):
    with pytest.raises((TypeError, ValueError)):
        estimate_cost(model_id("fermenter_reactor_turton_2001"), value, size_unit="m3")


def test_no_extrapolation_parallelisation_or_silent_missing_range():
    with pytest.raises(ValueError, match="MODEL_OUT_OF_RANGE"):
        estimate_cost(model_id("fermenter_reactor_turton_2001"), 1000, size_unit="m3")
    m = next(m for m in MODELS if not m["raw"]["s_lower"] and m["status"] != "disabled")
    with pytest.raises(ValueError, match="MODEL_APPLICABILITY_UNVERIFIED"):
        estimate_cost(m["id"], 1, size_unit=m["size_unit"])


def test_quartic_optional_coefficients_and_overflow():
    row = {
        "form": "log-log quadratic",
        "K1": "1",
        "K2": "2",
        "K3": "0",
        "K4": "3",
        "K5": "4",
    }
    assert evaluate(row, 10, enforce_bounds=False) == pytest.approx(10**10)
    row.update(K4="", K5="")
    assert evaluate(row, 10, enforce_bounds=False) == pytest.approx(1000)
    row.update(K1="10000")
    with pytest.raises(ValueError, match="Nonfinite"):
        evaluate(row, 10, enforce_bounds=False)
    row.update(K1="nan")
    with pytest.raises(ValueError):
        evaluate(row, 10, enforce_bounds=False)


def test_two_independent_inputs_and_conversion_source():
    key = model_id("belt_conveyor_seider_2013")
    c = estimate_from_parsed_inputs(
        key,
        {
            "size": Measurement(0.508, "m", {"cell": "D4"}),
            "second_size": Measurement(30.48, "m", {"cell": "D5"}),
        },
    )
    assert c.estimate.amount == pytest.approx(48800)
    assert c.evidence["second_input_conversion"]["original"]["source"]["cell"] == "D5"
    with pytest.raises(ValueError, match="MISSING_SIZING_INPUT"):
        estimate_cost(key, 20, size_unit="in")
    with pytest.raises(ValueError, match="MODEL_OUT_OF_RANGE"):
        estimate_cost(key, 20, size_unit="in", second_size=301, second_size_unit="ft")


def test_generic_material_installation_are_explicit_and_relative():
    m = next(
        m
        for m in MODELS
        if m["default_material"] == "304 stainless steel"
        and m["cost_scope"] == "purchased_equipment"
        and m["status"] != "disabled"
    )
    s = representative(m["raw"])
    a = estimate_cost(
        m["id"],
        s,
        size_unit=m["size_unit"],
        allow_unverified=True,
        unit_context=CONTEXT,
    )
    b = estimate_cost(
        m["id"],
        s,
        size_unit=m["size_unit"],
        allow_unverified=True,
        unit_context=CONTEXT,
        material="304 stainless steel",
    )
    assert a.estimate.amount == b.estimate.amount
    with pytest.raises(ValueError, match="confirmation"):
        estimate_cost(
            m["id"],
            s,
            size_unit=m["size_unit"],
            allow_unverified=True,
            unit_context=CONTEXT,
            material="Carbon steel",
        )
    c = estimate_cost(
        m["id"],
        s,
        size_unit=m["size_unit"],
        allow_unverified=True,
        unit_context=CONTEXT,
        material="Carbon steel",
        installation_profile="Fluids",
        adjustment_basis_confirmed=True,
    )
    assert c.estimate.amount == pytest.approx(a.estimate.amount / 1.3)
    assert c.installation_cost > 0
    assert c.equipment_and_installation_cost == pytest.approx(
        c.equipment_cost + c.installation_cost
    )


def test_installed_scope_and_capex_no_purchase_factor_uplift():
    m = next(
        m
        for m in MODELS
        if m["cost_scope"] == "installed_equipment" and m["status"] != "disabled"
    )
    total = calculate_total_cost(
        [
            {
                "equipment_tag": "PK-1",
                "curve_id": m["id"],
                "size": representative(m["raw"]),
                "size_unit": m["size_unit"],
                "quantity": 2,
                "costing_options": {"allow_unverified": True},
            }
        ],
        translation_policy=DEFAULT_POLICY,
    )
    line = total.equipment[0]
    assert (
        line.amount and line.equipment_cost is None and line.installation_cost is None
    )
    i = prepare_capex_inputs(
        total,
        process_type="fluids",
        delivery_basis="delivered",
        factor_selection="minimum",
    )
    c = calculate_capex(inputs=i)
    assert c.total_capex is not None, c.issues
    assert float(c.plant_cost) == pytest.approx(line.amount)
    assert c.purchased_equipment == 0
    with pytest.raises(ValueError, match="No extra"):
        estimate_cost(
            m["id"],
            representative(m["raw"]),
            size_unit=m["size_unit"],
            allow_unverified=True,
            installation_profile="Fluids",
            adjustment_basis_confirmed=True,
        )


def test_two_variable_bridge_uses_independent_sources_and_preserves_assumptions():
    from backend.equipment_costing.unit_conversion.bridges.service import (
        evaluate as bridge,
    )
    from backend.tests.test_unit_conversion_bridges import REPORT

    report = copy.deepcopy(REPORT)
    report["entities"][1]["values"] = [
        dict(
            id="width",
            property="width",
            normalized_value=0.508,
            normalized_unit="m",
            status="verified",
            sheet="Design",
            cell="D4",
        ),
        dict(
            id="length",
            property="length",
            normalized_value=30.48,
            normalized_unit="m",
            status="verified",
            sheet="Design",
            cell="D5",
        ),
    ]
    spec = {
        "model_id": model_id("belt_conveyor_seider_2013"),
        "method": "direct",
        "measurement_id": "width",
        "inputs": {},
        "secondary_input": {
            "measurement_id": "length",
            "value": None,
            "unit": None,
            "rationale": "Length from independent design cell",
        },
    }
    result = bridge(report, "e", spec)
    assert result["size"] == pytest.approx(20)
    assert result["second_size"] == pytest.approx(100)
    assert (
        result["second_input_provenance"]["original"]["source"]["measurement"]["cell"]
        == "D5"
    )
    spec["secondary_input"] = {
        "measurement_id": None,
        "value": 100,
        "unit": "ft",
        "rationale": "Explicit hypothetical design length",
    }
    assert (
        bridge(report, "e", spec)["second_input_provenance"]["original"]["source"][
            "status"
        ]
        == "ASSUMED"
    )


def test_pump_flow_head_derivation_and_explicit_gallon_basis():
    from backend.equipment_costing.unit_conversion.bridges.service import (
        evaluate as bridge,
    )
    from backend.tests.test_unit_conversion_bridges import REPORT

    key = model_id("centrifugal_1-stage_1800_HSC_seider_2013")
    spec = {
        "model_id": key,
        "method": "pump_flow_head",
        "measurement_id": "m",
        "inputs": {"density_kg_m3": 1000, "head_m": 30.48},
        "unit_context": {"target_gallon_basis": "US"},
        "rationale": "Synthetic design head, not operating pressure",
    }
    r = bridge(REPORT, "e", spec)
    assert r["size"] == pytest.approx(1 / 0.003785411784 / 60 * 10)
    spec["unit_context"] = {}
    with pytest.raises(ValueError, match="gallon"):
        bridge(REPORT, "e", spec)


def test_monte_carlo_uses_canonical_scoped_costs_without_llm(tmp_path):
    from backend.tests.test_stage_connections import workbook, plan_for
    from backend.orchestration.ingest import parse
    from backend.scenarios_and_uncertainty.monte_carlo.engine import evaluate as run
    from backend.scenarios_and_uncertainty.monte_carlo.scenarios import prepare

    parsed = parse(workbook(), "synthetic-openpytea.xlsx")
    report = parsed["report"]
    plan = plan_for(report)
    row = plan["equipment"][0]
    # Keep existing real finance/operations fixture, change only canonical model/size.
    plan["equipment"] = [
        dict(
            equipment_key=row["equipment_key"],
            curve_id=model_id("fermenter_reactor_turton_2001"),
            size=10,
            size_unit="m3",
            quantity=2,
            rationale="Synthetic fixed per-vessel design volume",
        )
    ]
    plan["cost_translation"] = {**DEFAULT_POLICY, "enabled": True}
    # Monte Carlo evaluate runs the same canonical pipeline, no provider argument.
    a = run(report, "Continuous synthetic water treatment", plan, [])
    b = run(report, "Continuous synthetic water treatment", plan, [])
    assert a == b
    assert a["coverage"]["priced"] == 1
    assert a["equipment_costs"]


def test_published_pressure_limit_is_checked_when_condition_is_supplied():
    m = next(
        m for m in MODELS if m.get("pressure_limits") and m["status"] != "disabled"
    )
    s = representative(m["raw"])
    maximum = m["pressure_limits"]["maximum"]
    with pytest.raises(ValueError, match="MODEL_CONDITION_OUT_OF_RANGE"):
        estimate_cost(
            m["id"],
            s,
            size_unit=m["size_unit"],
            allow_unverified=True,
            unit_context=CONTEXT,
            operating_pressure={
                "value": maximum + 1,
                "unit": "psig",
                "source": {"cell": "E7"},
            },
        )
    c = estimate_cost(
        m["id"],
        s,
        size_unit=m["size_unit"],
        allow_unverified=True,
        unit_context=CONTEXT,
        operating_pressure={"value": maximum, "unit": "psig"},
    )
    assert c.evidence["pressure_applicability"]["status"] == "checked_supplied_pressure"


def test_per_foot_cost_quantity_is_physical_not_item_count():
    m = next(
        m
        for m in MODELS
        if m["cost_scope"] == "unit_price_per_ft" and m["status"] != "disabled"
    )
    row = {
        "equipment_tag": "C-1",
        "curve_id": m["id"],
        "size": representative(m["raw"]),
        "size_unit": m["size_unit"],
        "quantity": 100,
        "quantity_unit": "ft",
        "costing_options": {"allow_unverified": True, "unit_context": CONTEXT},
    }
    r = calculate_total_cost([row])
    line = r.equipment[0]
    assert line.amount and line.equipment_cost == line.amount
    assert line.amount == pytest.approx(line.calculation.estimate.amount * 100)
    row["quantity_unit"] = "item"
    assert calculate_total_cost([row]).equipment[0].amount is None


def test_shaft_and_electrical_power_need_efficiency_conversion():
    from backend.equipment_costing.unit_conversion.bridges.service import (
        evaluate as bridge,
    )
    from backend.tests.test_unit_conversion_bridges import REPORT

    m = next(
        m
        for m in MODELS
        if m["raw"]["units"] == "shaft power, kW" and m["status"] != "disabled"
    )
    report = copy.deepcopy(REPORT)
    report["entities"][1]["values"] = [
        dict(
            id="p",
            property="electrical_power",
            normalized_value=100,
            normalized_unit="kW",
            status="verified",
            sheet="Power",
            cell="C3",
        )
    ]
    spec = {
        "model_id": m["id"],
        "method": "direct",
        "measurement_id": "p",
        "inputs": {},
    }
    with pytest.raises(ValueError, match="POWER_ROLE_MISMATCH"):
        bridge(report, "e", spec)
    spec.update(method="electrical_to_shaft_power", inputs={"motor_efficiency": 0.9})
    assert bridge(report, "e", spec)["size"] == pytest.approx(90)
    spec["inputs"] = {}
    with pytest.raises(ValueError, match="motor_efficiency"):
        bridge(report, "e", spec)


def test_pinned_import_is_idempotent_without_changing_manifest(tmp_path):
    from backend.equipment_costing.indexes.openpytea import import_catalogue as importer
    from unittest.mock import patch
    import hashlib

    source = tmp_path / "source"
    destination = tmp_path / "index"
    source.mkdir()
    destination.mkdir()
    contents = {
        "LICENSE": b"synthetic test notice",
        "cost_correlations.csv": b"synthetic CSV",
        "cepci_values.csv": b"synthetic indices",
        "equipment.py": b"# synthetic reference source",
    }
    manifest = {
        "files": {
            name: hashlib.sha256(data).hexdigest() for name, data in contents.items()
        },
        "commit": "explicit synthetic importer fixture",
    }
    for name, data in contents.items():
        (source / name).write_bytes(data)
    (destination / "sources.json").write_text(json.dumps(manifest))
    before = (destination / "sources.json").read_bytes()
    with patch.object(importer, "ROOT", destination), patch.object(
        importer, "audit", return_value={"counts": {"imported": 1}}
    ):
        changed, _ = importer.import_snapshot(source)
        assert len(changed) == 3
        again, _ = importer.import_snapshot(source)
        assert again == []
    assert (destination / "sources.json").read_bytes() == before


def test_approved_twenty_year_monte_carlo_is_reproducible(tmp_path):
    """1000 identical draws through real stages; no LLM or revenue-authority bypass."""
    from backend.tests.test_stage_connections import workbook, plan_for
    from backend.orchestration.ingest import parse
    from backend.orchestration.service import new_assessment
    from backend.orchestration.store import Store
    from backend.revenue.authority import update
    from backend.scenarios_and_uncertainty.monte_carlo.engine import simulate
    from backend.scenarios_and_uncertainty.monte_carlo.models import Settings

    data = workbook()
    store = Store(tmp_path / "approved-mc.sqlite")
    state = new_assessment(
        store,
        data,
        "synthetic-openpytea-mc.xlsx",
        "Continuous synthetic water treatment",
        "sells treated water",
    )
    parsed = parse(data, state["filename"])
    plan = plan_for(parsed["report"])
    key = plan["equipment"][0]["equipment_key"]
    plan["equipment"] = [
        dict(
            equipment_key=key,
            curve_id=model_id("fermenter_reactor_turton_2001"),
            size=10,
            size_unit="m3",
            quantity=2,
            rationale="Explicit synthetic volume; financial handoff test, not a validated process design",
        )
    ]
    plan["cost_translation"] = {**DEFAULT_POLICY, "enabled": True}
    state.update(parsed=parsed, plan=plan, running=False)
    state = store.put(state, state["revision"])
    state = update(store, state["id"], state["revision"], approve=True)
    original = copy.deepcopy(state)
    settings = Settings(parameters=[], seed=42)
    a = simulate(state, settings)
    b = simulate(state, settings)
    assert a == b
    assert a["summary"]["complete_runs"] == 1000, a["runs"][0].get("issues")
    assert a["summary"]["failed_runs"] == 0
    assert state == original
