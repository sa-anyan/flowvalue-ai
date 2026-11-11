"""METHOD-LEGACY01: legacy orchestration sizing routes reject invalid flows.

Negative examples are the recorded counterexamples in
docs/verification/phase1/method_acceptance/evidence/legacy_boundary_results.json.
Valid examples are independently computed: V = Q * t / f, Q = m / rho.
"""

import pytest

from backend.orchestration.sizing import derive_size


def report(prop, value, unit):
    return {
        "entities": [
            {
                "key": "s",
                "values": [
                    {
                        "id": "legacy",
                        "property": prop,
                        "normalized_value": value,
                        "normalized_unit": unit,
                        "status": "verified",
                    }
                ],
            }
        ]
    }


VOLUME = {"method": "volume_residence", "stream_key": "s",
          "residence_time_h": 2, "working_fraction": 0.8}
MASS = {"method": "mass_residence", "stream_key": "s", "density_kg_m3": 800,
        "residence_time_h": 2, "working_fraction": 0.8}


@pytest.mark.parametrize("flow", [-10, 0, float("nan"), float("inf")])
def test_volume_residence_rejects_non_positive_or_non_finite_flow(flow):
    with pytest.raises(ValueError):
        derive_size({"sizing": VOLUME}, report("volume_flow", flow, "m3/h"))


@pytest.mark.parametrize("flow", [-1000, 0])
def test_mass_residence_rejects_non_positive_flow(flow):
    with pytest.raises(ValueError):
        derive_size({"sizing": MASS}, report("mass_flow", flow, "kg/h"))


@pytest.mark.parametrize("flow", [-1000, 0])
def test_mass_to_volume_flow_rejects_non_positive_flow(flow):
    sizing = {**MASS, "method": "mass_to_volume_flow"}
    with pytest.raises(ValueError):
        derive_size({"sizing": sizing}, report("mass_flow", flow, "kg/h"))


@pytest.mark.parametrize("value", [-5, 0, True])
def test_stream_property_rejects_invalid_size(value):
    sizing = {"method": "stream_property", "stream_key": "s", "property": "volume"}
    with pytest.raises(ValueError):
        derive_size({"sizing": sizing}, report("volume", value, "m3"))


def test_valid_legacy_routes_use_registered_versioned_method():
    size, unit, evidence = derive_size(
        {"sizing": VOLUME}, report("volume_flow", 10, "m3/h")
    )
    assert (unit, size) == ("m3", pytest.approx(25.0, rel=1e-15))
    assert evidence["engineering_method"]["method_id"] == "vessel_hold_up"
    assert evidence["source_evidence"] == "legacy"

    size, unit, evidence = derive_size(
        {"sizing": MASS}, report("mass_flow", 1000, "kg/h")
    )
    # 1000 kg/h / 800 kg/m3 = 1.25 m3/h; 1.25 * 2 / 0.8 = 3.125 m3
    assert (unit, size) == ("m3", pytest.approx(3.125, rel=1e-15))
    assert evidence["engineering_method"]["method_id"] == "vessel_hold_up"
