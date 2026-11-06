"""Independent thermal reference cases; no private workbook values."""

import copy
import math
import pytest
from backend.equipment_costing.unit_conversion.bridges.heat_exchanger import (
    calculate_basis,
)
from backend.equipment_costing.unit_conversion import convert


def fixture():
    observations = []
    for role, t, h in [
        ("hot_inlet", 150, 100),
        ("hot_outlet", 100, 60),
        ("cold_inlet", 20, 10),
        ("cold_outlet", 60, 50),
    ]:
        for prop, value, unit in [
            ("temperature", t, "degC"),
            ("enthalpy_flow", h, "kW"),
            ("mass_flow", 3600, "kg/h"),
        ]:
            observations.append(
                dict(
                    id=role + prop,
                    entity_key=role,
                    property=prop,
                    value=value,
                    unit=unit,
                    sheet="Balance",
                    cell="A1",
                )
            )
    basis = {
        role + "_stream_key": role
        for role in ["hot_inlet", "hot_outlet", "cold_inlet", "cold_outlet"]
    }
    basis.update(
        duty_side="hot",
        duty_method="enthalpy_difference",
        flow_arrangement="countercurrent",
        phase_change="none",
        duty_conflict_policy="provisional_selected_side",
        common_enthalpy_reference_confirmed=True,
        steady_state_mass_flow_assumed=False,
        rationale="Synthetic thermal balance",
        limitations="Preliminary",
    )
    return observations, basis, dict(overall_u_w_m2_k=500, lmtd_correction=1)


def run(obs, basis, inputs, contexts=None):
    return calculate_basis(
        obs, contexts or [], basis, inputs, lambda v, u, t: convert(v, u, t).value
    )


def test_balanced_duty_lmtd_area_and_cell_lineage():
    obs, b, i = fixture()
    area, unit, d = run(obs, b, i)
    lmtd = (90 - 80) / math.log(90 / 80)
    assert area == pytest.approx(40000 / (500 * lmtd))
    assert unit == "m2"
    assert d["side_enthalpy_duties_kw"] == {"hot": 40, "cold": 40}
    assert d["relative_duty_disagreement"] == 0
    assert all(x["sheet"] == "Balance" for x in d["source_measurements"])
    assert not d["engineering_design_validated"]


def test_conflicting_side_retained_and_strict_policy_rejects():
    obs, b, i = fixture()
    next(x for x in obs if x["id"] == "cold_outletenthalpy_flow")["value"] = 500
    assert run(obs, b, i)[2]["relative_duty_disagreement"] > 0.9
    b["duty_conflict_policy"] = "require_consistency"
    i["duty_balance_tolerance_fraction"] = 0.05
    with pytest.raises(ValueError, match="reconciled"):
        run(obs, b, i)


def test_wrong_sign_not_silently_absoluted():
    obs, b, i = fixture()
    next(x for x in obs if x["id"] == "hot_outletenthalpy_flow")["value"] = 110
    with pytest.raises(ValueError, match="wrong sign"):
        run(obs, b, i)


def test_unknown_roles_and_unconfirmed_enthalpy_rejected():
    obs, b, i = fixture()
    b["hot_inlet_stream_key"] = "invented"
    with pytest.raises(ValueError, match="outside"):
        run(obs, b, i)
    obs, b, i = fixture()
    b["common_enthalpy_reference_confirmed"] = False
    with pytest.raises(ValueError, match="common-reference"):
        run(obs, b, i)


def test_temperature_cross_rejected():
    obs, b, i = fixture()
    next(x for x in obs if x["id"] == "cold_outlettemperature")["value"] = 160
    with pytest.raises(ValueError, match="cross"):
        run(obs, b, i)


def test_equal_terminal_differences_stable():
    obs, b, i = fixture()
    next(x for x in obs if x["id"] == "hot_inlettemperature")["value"] = 140
    assert run(obs, b, i)[2]["resolved_inputs"]["lmtd_k"] == pytest.approx(80)


def test_sensible_and_latent_routes():
    obs, b, i = fixture()
    b["duty_method"] = "sensible_heat"
    i["specific_heat_kj_kg_k"] = 2
    assert run(obs, b, i)[2]["duty_kw"] == 100
    b["duty_method"] = "phase_change"
    b["phase_change"] = "hot_condensing"
    i.update(
        latent_heat_kj_kg=2000,
        phase_change_fraction=0.5,
        sensible_enthalpy_change_kj_kg=0,
    )
    assert run(obs, b, i)[2]["duty_kw"] == 1000
    i["phase_change_fraction"] = 2
    with pytest.raises(ValueError, match="exceed"):
        run(obs, b, i)


def test_shared_utility_requires_allocation():
    obs, b, i = fixture()
    ctx = [
        {"entity_key": "hot_inlet", "descriptions": [{"text": "Steam HE-101 HE-102"}]}
    ]
    with pytest.raises(ValueError, match="allocation"):
        run(obs, b, i, ctx)
    i["utility_allocation_fraction"] = 0.5
    assert run(obs, b, i, ctx)[2]["duty_kw"] == 20


def test_missing_terminal_requires_explicit_assumption():
    obs, b, i = fixture()
    obs = [x for x in obs if x["id"] != "cold_inlettemperature"]
    with pytest.raises(ValueError, match="Four terminal"):
        run(obs, b, i)
    i["cold_inlet_temperature_k"] = 293.15
    assert run(obs, b, i)[0] > 0


def test_bad_dimensions_and_nonfinite_rejected():
    obs, b, i = fixture()
    next(x for x in obs if x["id"] == "hot_inletenthalpy_flow")["unit"] = "kg/h"
    with pytest.raises(ValueError):
        run(obs, b, i)
    obs, b, i = fixture()
    i["overall_u_w_m2_k"] = float("nan")
    with pytest.raises(ValueError):
        run(obs, b, i)


def test_canonical_model_unit_handoff_and_automatic_resolver(tmp_path):
    from backend.equipment_costing.unit_conversion.bridges.automatic import resolve
    from backend.equipment_costing.unit_conversion.bridges.service import evaluate
    from backend.orchestration.store import Store
    from backend.tests.test_automatic_equipment_inputs import decision
    from backend.blocks.equipment.calculation import calculate_equipment

    obs, b, i = fixture()
    report = {
        "entities": [
            {
                "key": "e",
                "kind": "equipment",
                "identifier": "HX-X",
                "stream_keys": list(
                    b[r + "_stream_key"]
                    for r in ["hot_inlet", "hot_outlet", "cold_inlet", "cold_outlet"]
                ),
                "values": [],
            }
        ]
    }
    for role in ["hot_inlet", "hot_outlet", "cold_inlet", "cold_outlet"]:
        report["entities"].append(
            {
                "key": role,
                "kind": "material",
                "identifier": role,
                "values": [
                    {
                        **v,
                        "normalized_value": v["value"],
                        "normalized_unit": v["unit"],
                        "status": "verified",
                    }
                    for v in obs
                    if v["entity_key"] == role
                ],
            }
        )

    class Provider:
        model = "synthetic-thermal-test"

        def generate(self, **kwargs):
            d = decision()
            d.update(
                model_id="G286-091",
                method="exchanger_area",
                measurement_id=None,
                thermal_basis=b,
                assumptions=[
                    dict(
                        name=n,
                        value=v,
                        unit={
                            "overall_u_w_m2_k": "W/m2/K",
                            "lmtd_correction": "fraction",
                        }[n],
                        rationale="Synthetic screening assumption",
                        limitations="Not a design",
                    )
                    for n, v in i.items()
                ],
            )
            return {"decisions": [d]}

    plan, audit = resolve(
        report,
        {
            "equipment": [
                {"equipment_key": "e", "curve_id": "G286-091", "source": "garrett"}
            ]
        },
        "Heat exchange",
        Store(tmp_path / "thermal.db"),
        Provider(),
        True,
    )
    spec = plan["equipment"][0]["unit_conversion"]
    assert spec["enabled"]
    preview = evaluate(report, "e", spec)
    assert preview["size_unit"] == "1000 ft2"
    assert preview["size"] == pytest.approx(run(obs, b, i)[0] / 92.90304)
    total, _ = calculate_equipment(report, plan)
    assert total.equipment[0].equipment_cost is not None
    assert preview["derived_inputs"]
    # A second deterministic run preserves the proposed basis and recomputes source values.
    again, _ = resolve(report, plan, "", Store(tmp_path / "again.db"), use_ai=False)
    assert again["equipment"][0]["unit_conversion"]["thermal_basis"] == {
        **b,
        "source_choices": [],
    }


def test_direct_cell_temperature_survives_competing_ai_interpretation_with_audit():
    obs, basis, inputs = fixture()
    direct = next(v for v in obs if v["id"] == "hot_inlettemperature")
    direct["status"] = "verified"
    obs.append(
        {
            **direct,
            "id": "ai-evidence:other-cell",
            "value": 5,
            "cell": "D20",
            "status": "inferred",
        }
    )
    before = copy.deepcopy(obs)
    area, unit, details = run(obs, basis, inputs)
    assert area > 0 and unit == "m2"
    audit = next(
        a for a in details["source_selections"] if a["selected"]["id"] == direct["id"]
    )
    assert audit["alternatives_retained"][0]["cell"] == "D20"
    assert any(
        "direct_cell_over_inferred" in warning for warning in details["warnings"]
    )
    assert obs == before


def test_explicit_thermal_cell_choice_resolves_conflicting_direct_sources_without_editing_them():
    obs, basis, inputs = fixture()
    original = next(v for v in obs if v["id"] == "cold_inlettemperature")
    original["status"] = "verified"
    obs.append({**original, "id": "alternative-temp", "value": 25, "cell": "C12"})
    before = copy.deepcopy(obs)
    with pytest.raises(ValueError, match="Conflicting equally supported"):
        run(obs, basis, inputs)
    basis["source_choices"] = [
        {
            "role": "cold_inlet",
            "property": "temperature",
            "measurement_id": original["id"],
            "rationale": "Provisional selection of original M&E temperature; alternative retained.",
        }
    ]
    area, _, details = run(obs, basis, inputs)
    assert area > 0
    selection = next(
        v
        for v in details["source_selections"]
        if v["policy"] == "explicit_provisional_source_choice"
    )
    assert selection["selected"]["id"] == original["id"]
    assert selection["alternatives_retained"][0]["id"] == "alternative-temp"
    assert obs == before


@pytest.mark.parametrize(
    "choice",
    [
        {
            "role": "hot_inlet",
            "property": "temperature",
            "measurement_id": "cold_inlettemperature",
            "rationale": "Wrong side",
        },
        {
            "role": "hot_inlet",
            "property": "temperature",
            "measurement_id": "hot_inletmass_flow",
            "rationale": "Wrong property",
        },
        {
            "role": "hot_inlet",
            "property": "temperature",
            "measurement_id": "hot_inlettemperature",
            "rationale": "",
        },
    ],
)
def test_thermal_source_choices_cannot_cross_streams_properties_or_omit_rationale(
    choice,
):
    obs, basis, inputs = fixture()
    basis["source_choices"] = [choice]
    with pytest.raises(ValueError, match="source choice"):
        run(obs, basis, inputs)


@pytest.mark.parametrize("choices", ["not-a-list", {}, [None], ["not-a-selection"]])
def test_malformed_thermal_source_choices_return_validation_errors(choices):
    obs, basis, inputs = fixture()
    basis["source_choices"] = choices
    with pytest.raises(ValueError, match="source choice"):
        run(obs, basis, inputs)
