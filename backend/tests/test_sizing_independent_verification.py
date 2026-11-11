"""FV-P1-SIZE-001: independent native-unit references; known defects deliberately fail.
Expected values are static hand/Decimal calculations, never production-generated.
See docs/verification/phase1/sizing/independent_equation_references.md.
"""

import copy
import json
import math
from decimal import Decimal, localcontext
from pathlib import Path
import pytest
from backend.engineering_sizing import calculate
from backend.engineering_sizing.registry import METHODS
from backend.equipment_costing.unit_conversion import convert, UnitResolutionError

REFERENCES = json.loads(
    (Path(__file__).parent / "fixtures/sizing_verification/references.json").read_text()
)


def test_inventory_has_exactly_independent_references():
    assert set(METHODS) == {r["method"] for r in REFERENCES}
    assert len(REFERENCES) == 12


@pytest.mark.parametrize("reference", REFERENCES, ids=lambda r: r["method"])
@pytest.mark.parametrize("scale", [0.01, 1, 100], ids=["low", "nominal", "high"])
def test_independent_reference(reference, scale):
    r = reference
    actual, unit, _ = calculate(r["method"], r["value"] * scale, r["parameters"])
    assert unit == r["unit"]
    assert actual == pytest.approx(
        float(r["expected"]) * scale,
        rel=r["relative_tolerance"],
        abs=r["absolute_tolerance"],
    )


@pytest.mark.parametrize("r", REFERENCES, ids=lambda r: r["method"])
def test_reproducibility_and_input_preservation(r):
    params = copy.deepcopy(r["parameters"])
    first = calculate(r["method"], r["value"], params)
    assert first == calculate(r["method"], r["value"], params)
    assert params == r["parameters"]


@pytest.mark.parametrize("r", REFERENCES, ids=lambda r: r["method"])
@pytest.mark.parametrize("value", [0, float("inf"), float("nan")])
def test_invalid_main_input(r, value):
    with pytest.raises((ValueError, TypeError, OverflowError)):
        calculate(r["method"], value, r["parameters"])


@pytest.mark.parametrize("r", REFERENCES, ids=lambda r: r["method"])
def test_missing_required_parameter(r):
    with pytest.raises((ValueError, TypeError)):
        calculate(r["method"], r["value"], {})


@pytest.mark.parametrize("r", REFERENCES, ids=lambda r: r["method"])
def test_negative_inputs_or_signed_heat(r):
    if r["method"] in {"exchanger_area", "vaporizer_area"}:
        assert (
            calculate(r["method"], -r["value"], r["parameters"])[0]
            == calculate(r["method"], r["value"], r["parameters"])[0]
        )
    else:
        with pytest.raises(ValueError):
            calculate(r["method"], -r["value"], r["parameters"])


@pytest.mark.parametrize("r", REFERENCES, ids=lambda r: r["method"])
@pytest.mark.parametrize("scale", [1e-100, 1e100])
def test_extreme_primary_output_finite_or_rejected(r, scale):
    try:
        value, _, _ = calculate(r["method"], r["value"] * scale, r["parameters"])
    except (ValueError, OverflowError):
        return
    assert math.isfinite(value) and value > 0


@pytest.mark.parametrize("r", REFERENCES, ids=lambda r: r["method"])
def test_dimension_mismatch_at_unit_boundary(r):
    wrong = "kg" if r["unit"] != "kg" else "m3"
    result = convert(1, wrong, r["unit"])
    assert result.status != "resolved" and result.value is None and result.issues


@pytest.mark.parametrize(
    "source,target,value,expected",
    [
        ("L/h", "m3/h", 1000, 1),
        ("kg/s", "kg/h", 1, 3600),
        ("W", "kW", 1000, 1),
        ("m2", "ft2", 1, 1 / (0.3048**2)),
        ("m3", "ft3", 1, 1 / (0.3048**3)),
    ],
)
def test_selected_alternative_units(source, target, value, expected):
    result = convert(value, source, target)
    assert result.value == pytest.approx(expected, rel=1e-12)


@pytest.mark.parametrize("method", ["exchanger_area", "vaporizer_area"])
def test_required_boolean_heat_duty_rejection(method):
    with pytest.raises(ValueError):
        calculate(
            method, True, {"overall_u_w_m2_k": 500, "lmtd_k": 20, "lmtd_correction": 1}
        )


def test_required_compression_stability_near_unity_gamma():
    k = math.nextafter(1.0, 2.0)
    with localcontext() as ctx:
        ctx.prec = 100
        gamma = Decimal.from_float(k)
        r = Decimal("1.380649e-23") * Decimal("6.02214076e23")
        # Independent high-precision ideal enthalpy change, evaluated with exp/ln.
        t2 = Decimal(300) * (Decimal(2).ln() * ((gamma - 1) / gamma)).exp()
        cp = r / 28 * gamma / (gamma - 1)
        expected = float(cp * (t2 - 300) / Decimal(".75"))
    p = dict(
        molecular_weight_kg_kmol=28,
        temperature_k=300,
        absolute_pressure_bar=1,
        discharge_pressure_bar=2,
        heat_capacity_ratio=k,
        efficiency=0.75,
        compressibility_z=1,
    )
    assert calculate("gas_compression", 3600, p)[0] == pytest.approx(
        expected, rel=5e-12
    )


def test_required_finite_pump_auxiliary_outputs():
    try:
        _, _, details = calculate(
            "pump_duty", 3.6, {"differential_pressure_bar": 1, "efficiency": 1e-320}
        )
    except ValueError:
        return
    assert math.isfinite(details["shaft_power_kw"])


INVALID_PARAMETERS = [
    (r, key, value)
    for r in REFERENCES
    for key in r["parameters"]
    for value in [None, -1, float("inf"), float("nan")]
]


@pytest.mark.parametrize(
    "r,key,value",
    INVALID_PARAMETERS,
    ids=[
        f"{r['method']}-{key}-{i}" for i, (r, key, _) in enumerate(INVALID_PARAMETERS)
    ],
)
def test_invalid_parameters(r, key, value):
    # Pump efficiency is explicitly optional; omission/None is a supported contract.
    if r["method"] == "pump_duty" and key == "efficiency" and value is None:
        assert (
            "shaft_power_kw"
            not in calculate(r["method"], r["value"], {**r["parameters"], key: value})[
                2
            ]
        )
        return
    with pytest.raises((ValueError, TypeError, OverflowError)):
        calculate(r["method"], r["value"], {**r["parameters"], key: value})


@pytest.mark.parametrize(
    "method,key,value",
    [
        ("vessel_hold_up", "working_fraction", 1.01),
        ("ion_exchange_capacity", "resin_bed_fraction", 1.01),
        ("ion_exchange_ebct", "resin_bed_fraction", 1.01),
        ("exchanger_area", "lmtd_correction", 1.01),
        ("vaporizer_area", "lmtd_correction", 1.01),
        ("gas_compression", "heat_capacity_ratio", 1),
        ("gas_compression", "heat_capacity_ratio", 2.01),
        ("gas_compression", "discharge_pressure_bar", 1),
        ("gas_compression", "efficiency", 1.01),
        ("pump_duty", "efficiency", 1.01),
        ("phase_change_duty", "phase_change_fraction", 1.01),
        ("evaporated_water", "product_water_mass_fraction", 0.8),
    ],
)
def test_declared_applicability_guards(method, key, value):
    r = next(r for r in REFERENCES if r["method"] == method)
    with pytest.raises(ValueError):
        calculate(method, r["value"], {**r["parameters"], key: value})


def test_adapter_source_lineage_and_wrong_parameter_units():
    from backend.engineering_sizing.adapter import derive

    report = {
        "entities": [
            {
                "key": "s",
                "values": [
                    {
                        "id": "source-Q",
                        "property": "volume_flow",
                        "normalized_value": 10,
                        "normalized_unit": "m3/h",
                        "status": "verified",
                    }
                ],
            }
        ]
    }
    sizing = {
        "method": "vessel_hold_up",
        "stream_key": "s",
        "parameters": {
            "residence_time_h": {"value": 2, "unit": "h"},
            "working_fraction": {"value": 0.8, "unit": "fraction"},
        },
    }
    size, unit, audit = derive(sizing, report)
    assert (size, unit) == (25, "m3")
    assert audit["source_evidence"] == ["source-Q"]
    sizing["parameters"]["residence_time_h"]["unit"] = "kg"
    with pytest.raises(ValueError, match="unit mismatch"):
        derive(sizing, report)


def test_sizing_to_costing_dryer_dimension_rejection():
    from backend.equipment_costing.registry import estimate_cost

    size, unit, _ = calculate("dryer_chamber", 3600, {"gas_residence_time_s": 10})
    with pytest.raises(UnitResolutionError, match="Incompatible quantities"):
        estimate_cost("G277-061", size, size_unit=unit, allow_unverified=True)
