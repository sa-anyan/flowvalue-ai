from math import log, pi

import pytest
from pydantic import ValidationError

from app.engine.costing import (
    Compressor,
    CostingRequest,
    CostSettings,
    HeatExchanger,
    Pump,
    Vessel,
    build_bom,
    cost_equipment,
    lmtd,
    size_equipment,
)


def exchanger(**kwargs):
    return HeatExchanger(
        unit_id="E1", duty_kw=1000, overall_u_w_m2_k=500, lmtd_k=20, **kwargs
    )


def test_exchanger_hand_calculation():
    result = cost_equipment(exchanger(), CostSettings(cepci_current=397))
    assert result.sizing["area_m2"] == 100
    # log10(100)=2; independently evaluated polynomial.
    cp0 = 10**4.3723
    assert result.base_purchase_cost_usd == pytest.approx(cp0)
    assert result.purchased_equipment_cost_usd == pytest.approx(cp0)
    assert result.bare_module_cost_usd == pytest.approx(cp0 * 3.29)


def test_lmtd():
    assert lmtd(20, 20) == 20
    assert lmtd(40, 20) == pytest.approx(20 / log(2))
    with pytest.raises(ValueError):
        lmtd(-1, 20)


def test_material_pressure_and_index():
    base = cost_equipment(exchanger(), CostSettings(cepci_current=397))
    indexed = cost_equipment(
        exchanger(material="stainless_steel", design_pressure_barg=100), CostSettings()
    )
    assert (
        indexed.indexed_base_purchase_cost_usd / base.base_purchase_cost_usd
        == pytest.approx(800 / 397)
    )
    assert indexed.material_factor == 2.7
    assert indexed.pressure_factor > 1
    assert indexed.bare_module_cost_usd > base.bare_module_cost_usd * 800 / 397


def test_vessel_geometry_and_pressure():
    unit = Vessel(unit_id="V1", volume_m3=30, design_pressure_barg=20)
    size, dimensions = size_equipment(unit)
    d, h = dimensions["diameter_m"], dimensions["cylindrical_height_m"]
    assert pi * d**2 * h / 4 == pytest.approx(30)
    expected_t = 2 * d / (2 * (94.4 * 0.9 - 0.6 * 2)) + 0.00315
    assert dimensions["wall_thickness_mm"] == pytest.approx(expected_t * 1000)
    assert size == 30
    assert cost_equipment(unit, CostSettings()).pressure_factor > 1
    assert cost_equipment(
        Vessel(unit_id="R1", kind="reactor", volume_m3=30), CostSettings()
    ).warnings


def test_pump_power_and_head():
    power, dims = size_equipment(
        Pump(
            unit_id="P1",
            volumetric_flow_m3_h=360,
            density_kg_m3=1000,
            head_m=100,
            efficiency=0.8,
        )
    )
    assert power == pytest.approx(122.583125)
    assert dims["differential_pressure_bar"] == pytest.approx(9.80665)


def test_compressor_ideal_gas_work():
    unit = Compressor(
        unit_id="C1",
        mass_flow_kg_s=10,
        inlet_temperature_k=300,
        inlet_pressure_bar_abs=1,
        outlet_pressure_bar_abs=4,
        molecular_weight_kg_kmol=28,
        heat_capacity_ratio=1.4,
        isentropic_efficiency=0.8,
    )
    power, dims = size_equipment(unit)
    expected = 10 * 3.5 * (8314.462618 / 28) * 300 * (4 ** (2 / 7) - 1) / 1000
    assert power == pytest.approx(expected)
    assert dims["shaft_power_kw"] == pytest.approx(expected / 0.8)
    assert cost_equipment(unit, CostSettings()).bare_module_factor == 2.7


def test_bom_quantity_and_override():
    unit = exchanger(
        quantity=3, material_factor_override=2, pressure_factor_override=1.5
    )
    bom = build_bom(CostingRequest(equipment=[unit]))
    item = bom.items[0]
    assert bom.total_bare_module_cost_usd == pytest.approx(
        3 * item.bare_module_cost_usd
    )
    assert bom.total_purchased_equipment_cost_usd == pytest.approx(
        3 * item.purchased_equipment_cost_usd
    )
    assert item.bare_module_factor == pytest.approx(1.63 + 1.66 * 2 * 1.5)


def test_no_silent_extrapolation():
    unit = HeatExchanger(unit_id="small", duty_kw=1, overall_u_w_m2_k=500, lmtd_k=20)
    with pytest.raises(ValueError, match="outside correlation range"):
        cost_equipment(unit, CostSettings())
    assert cost_equipment(unit, CostSettings(allow_extrapolation=True)).warnings


@pytest.mark.parametrize(
    "changes",
    [
        {"duty_kw": 0},
        {"lmtd_k": -1},
        {"overall_u_w_m2_k": float("nan")},
        {"material": "unobtainium"},
    ],
)
def test_invalid_inputs(changes):
    with pytest.raises(ValidationError):
        HeatExchanger.model_validate(
            {"unit_id": "E1", "duty_kw": 1000, "overall_u_w_m2_k": 500, "lmtd_k": 20}
            | changes
        )


def test_duplicate_ids_and_invalid_design():
    with pytest.raises(ValidationError):
        CostingRequest(equipment=[exchanger(), exchanger()])
    with pytest.raises(ValueError, match="allowable stress"):
        size_equipment(
            Vessel(
                unit_id="bad",
                volume_m3=30,
                design_pressure_barg=100,
                allowable_stress_mpa=1,
            )
        )
    with pytest.raises(ValueError, match="above 140"):
        cost_equipment(exchanger(design_pressure_barg=200), CostSettings())


def test_costing_api_success_and_range_errors():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    payload = {"equipment": [exchanger().model_dump()]}
    result = client.post("/api/costing/bom", json=payload)
    assert result.status_code == 200, result.text
    assert result.json()["total_bare_module_cost_usd"] > 0
    payload["equipment"][0]["duty_kw"] = 1
    assert client.post("/api/costing/bom", json=payload).status_code == 422
    payload["equipment"][0]["kind"] = "unknown"
    assert client.post("/api/costing/bom", json=payload).status_code == 422


def test_pressure_limit_override_and_material_factor_audit():
    result = cost_equipment(
        exchanger(design_pressure_barg=200, pressure_factor_override=2), CostSettings()
    )
    assert result.pressure_factor == 2
    assert "User-supplied factor override applied" in result.warnings
    unit = Pump(
        unit_id="P1",
        volumetric_flow_m3_h=360,
        density_kg_m3=1000,
        head_m=100,
        design_pressure_barg=50,
    )
    result = cost_equipment(unit, CostSettings())
    assert result.pressure_factor > 1


def test_extreme_extrapolation_rejected_cleanly():
    unit = HeatExchanger(
        unit_id="extreme",
        duty_kw=1e12,
        overall_u_w_m2_k=1e-9,
        lmtd_k=1e-9,
        lmtd_correction_factor=1e-100,
    )
    with pytest.raises(ValueError, match="numerical cost limits"):
        cost_equipment(unit, CostSettings(allow_extrapolation=True))
