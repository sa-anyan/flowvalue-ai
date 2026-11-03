"""Independent dimensional examples and conditional engineering envelopes."""

import pytest

from backend.engineering_sizing import calculate
from backend.engineering_sizing.adapter import derive


def test_equipment_equations_and_units():
    assert calculate(
        "vessel_hold_up", 10, {"residence_time_h": 2, "working_fraction": 0.8}
    )[:2] == (25, "m3")
    assert calculate(
        "exchanger_area",
        100,
        {"overall_u_w_m2_k": 500, "lmtd_k": 20, "lmtd_correction": 1},
    )[:2] == (10, "m2")
    assert calculate("filter_area", 20, {"hydraulic_loading_m_h": 5})[:2] == (4, "m2")
    assert calculate("dryer_chamber", 3600, {"gas_residence_time_s": 10})[:2] == (
        10,
        "m3",
    )
    value, unit, details = calculate(
        "pump_duty", 3.6, {"differential_pressure_bar": 1, "efficiency": 0.5}
    )
    assert details["hydraulic_power_kw"] == pytest.approx(0.1)
    assert details["shaft_power_kw"] == pytest.approx(0.2)
    assert unit == "1000 US_gpm_psi" and value > 0
    gas = calculate(
        "gas_volume",
        28.97,
        {
            "molecular_weight_kg_kmol": 28.97,
            "temperature_k": 273.15,
            "absolute_pressure_bar": 1.01325,
            "compressibility_z": 1,
        },
    )
    assert gas[0] == pytest.approx(22.4139695, rel=1e-6)


def test_source_and_assumption_ranges_are_traceable():
    report = {
        "entities": [
            {
                "key": "s",
                "values": [
                    {
                        "id": "v1",
                        "property": "mass_flow",
                        "normalized_value": 1000,
                        "normalized_unit": "kg/h",
                        "status": "inferred",
                    }
                ],
            }
        ]
    }
    params = {
        "density_kg_m3": {"value": 1000, "unit": "kg/m3", "low": 900, "high": 1100},
        "residence_time_h": {"value": 2, "unit": "h", "low": 1, "high": 3},
        "working_fraction": {"value": 0.8, "unit": "fraction", "low": 0.7, "high": 0.9},
    }
    size, unit, audit = derive(
        {"method": "vessel_hold_up", "stream_key": "s", "parameters": params}, report
    )
    assert size == pytest.approx(2.5) and unit == "m3"
    assert audit["size_range"]["low"] == pytest.approx(1000 / 1100 / 0.9)
    assert audit["size_range"]["high"] == pytest.approx(1000 / 900 * 3 / 0.7)
    assert audit["source_evidence"] == ["v1"]
    params["density_kg_m3"]["unit"] = "lb/ft3"
    with pytest.raises(ValueError, match="unit mismatch"):
        derive(
            {"method": "vessel_hold_up", "stream_key": "s", "parameters": params},
            report,
        )


@pytest.mark.parametrize(
    "method,flow,params",
    [
        ("pump_duty", 1, {"differential_pressure_bar": -1}),
        (
            "exchanger_area",
            100,
            {"overall_u_w_m2_k": 0, "lmtd_k": 10, "lmtd_correction": 1},
        ),
        (
            "gas_volume",
            1,
            {
                "molecular_weight_kg_kmol": 29,
                "temperature_k": 300,
                "absolute_pressure_bar": 0,
                "compressibility_z": 1,
            },
        ),
    ],
)
def test_invalid_physical_assumptions_rejected(method, flow, params):
    with pytest.raises(ValueError):
        calculate(method, flow, params)


def test_source_corrected_dryer_coordinates_remain_provisional():
    from backend.equipment_costing.registry import estimate_cost

    # Source chart x=10000 means actual volume=100000 ft3.
    result = estimate_cost("G277-062", 100000, size_unit="ft3", allow_unverified=True)
    assert result.estimate is not None
    assert result.estimate.amount == pytest.approx(200000, rel=0.02)
    assert result.status == "provisional"
    assert result.evidence["source_correction"]["source"]["printed_page"] == 277


def test_pump_sizing_flows_into_canonical_cost_model():
    from backend.equipment_costing.registry import estimate_cost
    from backend.equipment_costing.unit_conversion import ConversionContext

    value, unit, _ = calculate("pump_duty", 36, {"differential_pressure_bar": 5})
    result = estimate_cost(
        "G296-122",
        value,
        size_unit=unit,
        unit_context=ConversionContext(target_gallon_basis="US"),
        allow_unverified=True,
    )
    assert result.estimate and result.estimate.amount > 0


def test_preliminary_alias_is_not_costed_twice():
    from backend.orchestration.pricing_status import annotate
    result={'equipment':[{'equipment_tag':'T-1','curve_id':None,'equipment_cost':None,'issues':['Alias not priced'],'parsed_source':{'equipment_key':'alias'}}]}
    annotate(result,{}, {'equipment':[{'equipment_key':'alias','scope_decision':'alias','alias_of':'real','rationale':'Same tank tag variant'}]})
    assert result['pricing_coverage']['alias_proposals']==1
    assert not result['pricing_coverage']['complete']
    assert result['equipment'][0]['decision']['next_action']=='confirm_alias'


def test_candidate_without_size_is_reinvestigated():
    from backend.orchestration.feedback import equipment_feedback
    result={'stages':{'equipment':{'result':{'equipment':[{'equipment_tag':'F-1','curve_id':None,'equipment_cost':None,'issues':['Area missing'],'decision':{'candidate_curve_ids':['G282-076'],'scope_decision':'include'}}]}},'capex':{'status':'unresolved'}}}
    assert equipment_feedback(result)['engineering_errors'][0]['equipment_tag']=='F-1'
