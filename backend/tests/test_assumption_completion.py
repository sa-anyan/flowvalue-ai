import copy
import pytest
from backend.equipment_costing.unit_conversion.bridges.assumption_completion import (
    complete_missing,
)
from backend.equipment_costing.unit_conversion.bridges.automatic import (
    normalize_assumption,
)
from backend.equipment_costing.unit_conversion.bridges.service import PARAMETERS
from backend.equipment_costing.unit_conversion.bridges.heat_exchanger import (
    required_parameters,
)
from tools.audit_fresh_equipment import NoCacheStore


class Provider:
    model = "synthetic"

    def __init__(self, name="sensible_enthalpy_change_kj_kg"):
        self.name = name
        self.calls = 0

    def generate(self, **kwargs):
        self.calls += 1
        assert (
            kwargs["context"]["context"]["accepted_inputs"]["latent_heat_kj_kg"] == 1000
        )
        return {
            "status": "proposed",
            "rationale": "Synthetic latent-only scenario",
            "assumptions": [
                {
                    "name": self.name,
                    "value": 0,
                    "unit": "kJ/kg",
                    "rationale": "Explicit synthetic no-subcooling scenario",
                    "limitations": "Not a measured sensible heat term",
                }
            ],
        }


def test_only_missing_parameter_added_and_accepted_inputs_unchanged(tmp_path):
    context = {
        "accepted_inputs": {"latent_heat_kj_kg": 1000, "phase_change_fraction": 1}
    }
    before = copy.deepcopy(context)
    provider = Provider()
    additions, cached = complete_missing(
        ["sensible_enthalpy_change_kj_kg"],
        context,
        NoCacheStore(tmp_path / "fresh.db"),
        provider,
        normalize_assumption,
        PARAMETERS,
    )
    assert additions[0]["value"] == 0 and not cached
    assert additions[0]["origin"] == "llm_input_contract_completion"
    assert context == before and provider.calls == 1


def test_completion_cannot_override_existing_parameter(tmp_path):
    with pytest.raises(ValueError):
        complete_missing(
            ["sensible_enthalpy_change_kj_kg"],
            {"accepted_inputs": {"latent_heat_kj_kg": 1000}},
            NoCacheStore(tmp_path / "fresh.db"),
            Provider("latent_heat_kj_kg"),
            normalize_assumption,
            PARAMETERS,
        )


def test_no_missing_parameters_makes_no_ai_call(tmp_path):
    provider = Provider()
    assert complete_missing(
        [],
        {},
        NoCacheStore(tmp_path / "fresh.db"),
        provider,
        normalize_assumption,
        PARAMETERS,
    ) == ([], False)
    assert provider.calls == 0


def test_phase_change_contract_requires_explicit_sensible_allowance():
    basis = {
        role + "_stream_key": role
        for role in ["hot_inlet", "hot_outlet", "cold_inlet", "cold_outlet"]
    }
    basis.update(
        duty_method="phase_change",
        flow_arrangement="countercurrent",
        duty_conflict_policy="provisional_selected_side",
    )
    assert required_parameters(basis) == {
        "overall_u_w_m2_k",
        "lmtd_correction",
        "latent_heat_kj_kg",
        "phase_change_fraction",
        "sensible_enthalpy_change_kj_kg",
    }


def test_canonical_resolver_completes_one_parameter_without_reselecting_sources(
    tmp_path,
):
    from backend.tests.test_heat_exchanger_basis import fixture
    from backend.tests.test_automatic_equipment_inputs import decision
    from backend.equipment_costing.unit_conversion.bridges.automatic import resolve
    from backend.equipment_costing.unit_conversion.bridges.service import evaluate

    observations, basis, _ = fixture()
    basis.update(duty_method="phase_change", phase_change="hot_condensing")
    report = {
        "entities": [
            {
                "key": "e",
                "identifier": "HX-7",
                "kind": "equipment",
                "values": [],
                "stream_keys": ["hot_inlet", "hot_outlet", "cold_inlet", "cold_outlet"],
            }
        ]
    }
    for role in report["entities"][0]["stream_keys"]:
        report["entities"].append(
            {
                "key": role,
                "identifier": role,
                "kind": "material",
                "values": [
                    {
                        **v,
                        "normalized_value": v["value"],
                        "normalized_unit": v["unit"],
                        "status": "verified",
                    }
                    for v in observations
                    if v["entity_key"] == role
                ],
            }
        )
    before = copy.deepcopy(report)
    accepted = {
        "overall_u_w_m2_k": 500,
        "lmtd_correction": 1,
        "latent_heat_kj_kg": 1000,
        "phase_change_fraction": 1,
    }

    class CompletingProvider:
        model = "synthetic"
        calls = []

        def generate(self, **kwargs):
            self.calls.append(kwargs["context"]["task"])
            if kwargs["context"]["task"] == "thermal-missing-input-completion-v1":
                assert kwargs["context"]["context"]["accepted_inputs"] == accepted
                return {
                    "status": "proposed",
                    "rationale": "Synthetic allowance",
                    "assumptions": [
                        {
                            "name": "sensible_enthalpy_change_kj_kg",
                            "value": 100,
                            "unit": "kJ/kg",
                            "rationale": "Explicit synthetic subcooling allowance",
                            "limitations": "Illustrative only",
                        }
                    ],
                }
            proposal = decision()
            proposal.update(
                model_id="G286-091",
                method="exchanger_area",
                measurement_id=None,
                thermal_basis=copy.deepcopy(basis),
                assumptions=[
                    {
                        "name": name,
                        "value": value,
                        "unit": PARAMETERS[name],
                        "rationale": "Synthetic scenario",
                        "limitations": "Not a design",
                    }
                    for name, value in accepted.items()
                ],
            )
            return {"decisions": [proposal]}

    provider = CompletingProvider()
    plan, audit = resolve(
        report,
        {
            "equipment": [
                {"equipment_key": "e", "curve_id": "G286-091", "source": "garrett"}
            ]
        },
        "Synthetic heat exchanger",
        NoCacheStore(tmp_path / "fresh.db"),
        provider,
        True,
    )
    specification = plan["equipment"][0]["unit_conversion"]
    assert all(specification["inputs"][n] == v for n, v in accepted.items())
    assert specification["inputs"]["sensible_enthalpy_change_kj_kg"] == 100
    assert (
        specification["input_provenance"]["sensible_enthalpy_change_kj_kg"]["origin"]
        == "llm_input_contract_completion"
    )
    assert len(provider.calls) == 2
    assert report == before
    assert evaluate(report, "e", specification)["size"] > 0
    assert any(a["status"] == "completed_missing_thermal_assumptions" for a in audit)
