"""FV-P1-UNIT-001 bounded independent unit contracts; no production changes.
Expected values are independent dimensional definitions in static fixtures.
Known NumPy-Boolean assumption failures stay red for a separate correction.
"""

import copy
import json
from pathlib import Path
from decimal import Decimal
from fractions import Fraction

import numpy as np
import pytest

from backend.equipment_costing.unit_conversion import (
    convert,
    identify_unit,
    ConversionContext,
)
from backend.equipment_costing.unit_conversion.bridges import liquid, gas
from backend.engineering_sizing.registry import calculate, METHODS
from backend.engineering_sizing.adapter import derive

ROOT = Path(__file__).parent / "fixtures/unit_acceptance"
REFERENCES = json.loads((ROOT / "references.json").read_text())
ALIASES = json.loads((ROOT / "aliases.json").read_text())
NATIVE = json.loads(
    (Path(__file__).parent / "fixtures/sizing_verification/references.json").read_text()
)


@pytest.mark.parametrize("r", REFERENCES, ids=lambda r: r["id"] + "-" + r["source"])
def test_independent_supported_unit(r):
    result = convert(
        r["value"],
        r["source"],
        r["destination"],
        context=ConversionContext(**r["context"]),
    )
    assert result.value is not None, result.issues
    assert result.value == pytest.approx(
        float(r["expected"]), rel=r["relative_tolerance"], abs=r["absolute_tolerance"]
    )


@pytest.mark.parametrize("r", ALIASES, ids=lambda r: r["id"] + "-" + r["source"])
def test_explicit_alias_semantics(r):
    result = convert(1, r["source"], r["destination"])
    assert result.value is not None, result.issues
    assert result.value == pytest.approx(float(r["expected"]), rel=1e-12, abs=1e-14)


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        np.bool_(True),
        np.bool_(False),
        None,
        float("nan"),
        float("inf"),
        -float("inf"),
        "1",
        "1,000",
        "not numeric",
        Decimal("1"),
        Fraction(1),
        np.int64(1),
        np.float32(1),
    ],
)
def test_non_supported_numeric_representations_are_not_silently_coerced(value):
    result = convert(value, "kg", "g")
    assert result.value is None and result.status == "unresolved"


@pytest.mark.parametrize("value", [1, 1.0, np.float64(1), -1, -1.0, np.float64(-1)])
def test_supported_numeric_representations_and_signed_duty(value):
    assert convert(value, "kW", "W").value == float(value) * 1000


@pytest.mark.parametrize(
    "src,dst,expected",
    [
        ("m/s", "ft/s", 1 / Decimal("0.3048")),
        ("cP", "Pa*s", None),
        ("cSt", "m2/s", None),
        (
            "Btu_IT/(h*ft2*delta_degF)",
            "W/m2/K",
            Decimal("1055.05585262")
            / (3600 * Decimal("0.3048") ** 2 * (Decimal(5) / 9)),
        ),
        ("min", "h", Decimal(1) / 60),
        ("specific_gravity", "kg/m3", None),
    ],
)
def test_active_and_optional_conversion_families_have_explicit_outcomes(
    src, dst, expected
):
    # UNIT-003 implements three formerly absent active families. Preserve all
    # six cases: strengthen these three to independent numeric/reverse checks;
    # the three optional-family rejection assertions remain unchanged.
    result = convert(1, src, dst)
    if expected is None:
        assert result.value is None and result.issues
    else:
        assert result.status == "converted" and not result.issues
        assert result.value == pytest.approx(float(expected), rel=1e-12, abs=1e-14)
        assert convert(result.value, dst, src).value == pytest.approx(1, rel=1e-12)


@pytest.mark.parametrize(
    "src,dst",
    [
        ("kg/h", "m3/h"),
        ("kWh", "kW"),
        ("delta_degC", "degF"),
        ("psig", "psia"),
        ("gal", "L"),
        ("ton", "kg"),
        ("scfm", "m3/h"),
    ],
)
def test_required_context_or_dimensions_not_invented(src, dst):
    assert convert(1, src, dst).value is None


def cv(value, unit, target=None):
    if value == "quantity":
        return identify_unit(unit).quantity
    result = convert(value, unit, target)
    if result.value is None:
        raise ValueError("; ".join(result.issues))
    return result.value


def test_mass_to_volume_uses_explicit_density():
    assert liquid.evaluate("liquid_flow", 2, "kg/s", {"density_kg_m3": 1000}, cv)[
        0
    ] == pytest.approx(7.2)
    with pytest.raises(ValueError):
        liquid.evaluate("liquid_flow", 2, "kg/s", {}, cv)


def test_actual_to_reference_volume_requires_explicit_states():
    inputs = dict(
        molecular_weight_kg_kmol=28,
        temperature_k=300,
        absolute_pressure_bar=1,
        compressibility_z=1,
        reference_temperature_k=300,
        reference_pressure_bar=2,
        reference_compressibility_z=1,
    )
    value, unit, _ = gas.evaluate("standard_gas_flow", 100, "m3/h", inputs, cv)
    assert value == pytest.approx(50, rel=5e-12, abs=0)
    assert unit == "Sm3/h"
    with pytest.raises(ValueError):
        gas.evaluate("standard_gas_flow", 100, "m3/h", {}, cv)


def test_pressure_role_is_not_inferred_from_symbol():
    result = convert(1, "bar", "Pa")
    assert result.value == 100000 and result.pressure_basis is None
    assert convert(1, "bar", "bara").value is None


SOURCE_UNITS = {
    "mass_flow": [(1, "kg/s", 3600), (1, "tonne/h", 1000)],
    "volume_flow": [(1, "L/s", 3.6), (60, "L/min", 3.6)],
    "heat_duty": [(100000, "W", 100), (1, "MW", 1000)],
}


@pytest.mark.parametrize("r", NATIVE, ids=lambda r: r["method"])
@pytest.mark.parametrize("choice", [0, 1])
def test_complete_bounded_source_to_native_dispatch(r, choice):
    method = METHODS[r["method"]]
    value, unit, native = SOURCE_UNITS[method["input"]][choice]
    converted = convert(value, unit, method["unit"])
    assert converted.value == pytest.approx(native, rel=1e-12, abs=0)
    result = calculate(r["method"], converted.value, r["parameters"])
    expected = float(r["expected"]) * native / r["value"]
    assert result[0] == pytest.approx(
        expected, rel=r["relative_tolerance"], abs=r["absolute_tolerance"]
    )
    assert result[1] == r["unit"]


BOOL_PARAMETER = {
    "ion_exchange_capacity": ("ionic_load_mol_equiv_m3", True),
    "ion_exchange_ebct": ("empty_bed_contact_time_min", True),
    "vessel_hold_up": ("residence_time_h", True),
    "exchanger_area": ("overall_u_w_m2_k", True),
    "vaporizer_area": ("overall_u_w_m2_k", True),
    "gas_compression": ("molecular_weight_kg_kmol", True),
    "gas_volume": ("molecular_weight_kg_kmol", True),
    "pump_duty": ("efficiency", True),
    "filter_area": ("hydraulic_loading_m_h", True),
    "dryer_chamber": ("gas_residence_time_s", True),
    "phase_change_duty": ("latent_heat_kj_kg", True),
    "evaporated_water": ("product_water_mass_fraction", False),
}


@pytest.mark.parametrize("r", NATIVE, ids=lambda r: r["method"])
def test_required_numpy_boolean_assumptions_rejected(r):
    key, value = BOOL_PARAMETER[r["method"]]
    params = {**r["parameters"], key: np.bool_(value)}
    definition = METHODS[r["method"]]
    report = {
        "entities": [
            {
                "key": "s",
                "values": [
                    {
                        "id": "source",
                        "property": definition["input"],
                        "normalized_value": r["value"],
                        "normalized_unit": definition["unit"],
                        "status": "verified",
                    }
                ],
            }
        ]
    }
    with pytest.raises(ValueError):
        derive({"method": r["method"], "stream_key": "s", "parameters": params}, report)


def test_required_numpy_boolean_source_observation_rejected():
    report = {
        "entities": [
            {
                "key": "s",
                "values": [
                    {
                        "id": "source",
                        "property": "volume_flow",
                        "normalized_value": np.bool_(True),
                        "normalized_unit": "m3/h",
                        "status": "verified",
                    }
                ],
            }
        ]
    }
    spec = {
        "method": "pump_duty",
        "stream_key": "s",
        "parameters": {"differential_pressure_bar": 1, "efficiency": 0.5},
    }
    with pytest.raises(ValueError):
        derive(spec, report)
