"""Traceable thermal sizing adapter. AI selects a basis; Python computes duty/LMTD/area.

Conflicting measurements are retained, not corrected. Provisional side selection
never certifies an energy balance or a mechanical exchanger design.
"""

import math
import re
from backend.engineering_sizing.common import positive
from backend.engineering_sizing.registry import calculate

ROLES = ("hot_inlet", "hot_outlet", "cold_inlet", "cold_outlet")
TEMPERATURES = {role: role + "_temperature_k" for role in ROLES}
DUTY_METHODS = ("enthalpy_difference", "sensible_heat", "phase_change", "assumed_duty")


def signed_enthalpy_duty(inlet_kw, outlet_kw, side):
    """Signed heat release/absorption; no abs(), allocation or reference inference."""
    if side not in {"hot", "cold"}:
        raise ValueError("Choose hot or cold side")
    for value in (inlet_kw, outlet_kw):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError("Enthalpy flows must be finite numbers")
    return inlet_kw - outlet_kw if side == "hot" else outlet_kw - inlet_kw


def required_parameters(basis):
    """Numerical contract only; values must come from sources or explicit assumptions."""
    required = {"overall_u_w_m2_k", "lmtd_correction"}
    required.update(
        {
            "phase_change": {
                "latent_heat_kj_kg",
                "phase_change_fraction",
                "sensible_enthalpy_change_kj_kg",
            },
            "sensible_heat": {"specific_heat_kj_kg_k"},
            "assumed_duty": {"heat_duty_kw"},
        }.get(basis.get("duty_method"), set())
    )
    if basis.get("flow_arrangement") == "explicit_lmtd":
        required.add("lmtd_k")
    else:
        required.update(
            TEMPERATURES[r] for r in ROLES if not basis.get(r + "_stream_key")
        )
    if basis.get("duty_conflict_policy") == "require_consistency":
        required.add("duty_balance_tolerance_fraction")
    return required


def calculate_basis(observations, stream_context, basis, inputs, convert):
    inputs = dict(inputs)
    evidence = []
    derived = []
    warnings = []
    source_selections = {}
    if basis.get("duty_method") not in DUTY_METHODS:
        raise ValueError("Choose a supported thermal duty method")
    if basis.get("duty_side") not in {"hot", "cold"}:
        raise ValueError("Choose hot or cold side as the provisional duty basis")
    if basis.get("phase_change") not in {
        "none",
        "hot_condensing",
        "cold_boiling",
        "both",
    }:
        raise ValueError("Declare the exchanger phase-change basis")
    if not str(basis.get("rationale", "")).strip():
        raise ValueError("Thermal basis requires an engineering rationale")
    known = {v["entity_key"] for v in observations}
    roles = {role: basis.get(role + "_stream_key") for role in ROLES}
    if any(key and key not in known for key in roles.values()):
        raise ValueError(
            "Thermal role references a stream outside this equipment register"
        )
    nonempty = [key for key in roles.values() if key]
    if len(nonempty) != len(set(nonempty)):
        duplicates = {
            key: [role for role, stream in roles.items() if stream == key]
            for key in nonempty
            if nonempty.count(key) > 1
        }
        raise ValueError(
            "Inlet/outlet and hot/cold roles must use distinct streams; repeated assignments: "
            + str(duplicates)
        )
    contexts = {v["entity_key"]: v for v in stream_context}
    choices = {}
    source_choices = basis.get("source_choices", [])
    if not isinstance(source_choices, list) or len(source_choices) > 12:
        raise ValueError(
            "Thermal source choices must be a list of at most 12 selections"
        )
    for choice in source_choices:
        if not isinstance(choice, dict):
            raise ValueError(
                "Each thermal source choice must be a structured selection"
            )
        coordinate = (choice.get("role"), choice.get("property"))
        if (
            coordinate in choices
            or coordinate[0] not in ROLES
            or coordinate[1] not in {"temperature", "enthalpy_flow", "mass_flow"}
        ):
            raise ValueError("Duplicate or unsupported thermal source choice")
        if not str(choice.get("rationale", "")).strip() or not any(
            v["id"] == choice.get("measurement_id")
            and v["entity_key"] == roles[coordinate[0]]
            and v["property"] == coordinate[1]
            for v in observations
        ):
            allowed = [
                v["id"]
                for v in observations
                if v["entity_key"] == roles[coordinate[0]]
                and v["property"] == coordinate[1]
            ]
            raise ValueError(
                "Thermal source choice "
                + str(coordinate)
                + " selected "
                + str(choice.get("measurement_id"))
                + " must match role stream "
                + str(roles[coordinate[0]])
                + " and property, with rationale; allowed measurement IDs: "
                + str(allowed)
            )
        choices[coordinate] = choice

    def one(role, prop):
        if not roles[role]:
            return None
        candidates = [
            v
            for v in observations
            if v["entity_key"] == roles[role] and v["property"] == prop
        ]
        from .observation_selection import select_observation

        target = {"temperature": "K", "enthalpy_flow": "kW", "mass_flow": "kg/h"}[prop]
        try:
            selected, selection = select_observation(
                candidates, target, convert, choices.get((role, prop))
            )
        except ValueError as exc:
            raise ValueError(
                "Conflicting " + prop + " observations for " + role + "; " + str(exc)
            ) from None
        if selection:
            source_selections[role + ":" + prop] = selection
            warning = (
                "Source basis for "
                + role
                + " "
                + prop
                + ": "
                + selection["policy"]
                + "; alternative observations retained"
            )
            if warning not in warnings:
                warnings.append(warning)
        return selected

    def numeric(v, unit):
        result = convert(v["value"], v["unit"], unit)
        if result is None:
            raise ValueError("Cannot convert thermal observation to " + unit)
        if not any(x["id"] == v["id"] for x in evidence):
            evidence.append(v)
        return result

    def record(name, value, sources, formula, status="derived_from_meb"):
        inputs[name] = value
        derived.append(
            {
                "name": name,
                "unit": "kW" if name == "heat_duty_kw" else "K",
                "value": value,
                "status": status,
                "formula": formula,
                "source_measurements": sources,
            }
        )

    temps = {}
    for role, name in TEMPERATURES.items():
        v = one(role, "temperature")
        if v:
            temps[role] = numeric(v, "K")
            record(name, temps[role], [v], "source temperature -> kelvin")
        elif inputs.get(name) is not None:
            temps[role] = positive(inputs[name], name)
            warnings.append(
                role
                + " temperature is an explicit assumption, not a source observation"
            )
    phase = basis["phase_change"]
    arrangement = basis.get("flow_arrangement")
    if arrangement == "explicit_lmtd":
        lmtd = positive(inputs.get("lmtd_k"), "explicit LMTD K")
        warnings.append(
            "LMTD is explicitly assumed; terminal-temperature feasibility is incomplete"
        )
    else:
        if arrangement not in {"countercurrent", "parallel"}:
            raise ValueError(
                "Choose countercurrent/parallel flow or an explicit LMTD assumption"
            )
        if set(temps) != set(ROLES):
            raise ValueError(
                "Four terminal temperatures required; use source roles or explicit temperature assumptions"
            )
        hi, ho, ci, co = [temps[x] for x in ROLES]
        if min(hi, ho, ci, co) <= 0 or hi < ho or co < ci:
            raise ValueError(
                "Thermal terminal temperatures contradict heating/cooling roles"
            )
        a, b = (
            (hi - co, ho - ci)
            if arrangement == "countercurrent"
            else (hi - ci, ho - co)
        )
        if a <= 0 or b <= 0:
            raise ValueError(
                "Thermal temperature cross/zero approach: no positive LMTD for selected arrangement"
            )
        lmtd = a if math.isclose(a, b, rel_tol=1e-10) else (a - b) / math.log(a / b)
        if "lmtd_k" in inputs and not math.isclose(
            float(inputs["lmtd_k"]), lmtd, rel_tol=1e-6
        ):
            warnings.append(
                "Terminal-temperature LMTD replaces a different provisional LMTD input; original assumption remains in the plan provenance"
            )
        record(
            "lmtd_k",
            lmtd,
            [v for v in evidence if v["property"] == "temperature"],
            "LMTD = (dT1-dT2)/ln(dT1/dT2), " + arrangement,
            (
                "derived_from_sources_and_assumptions"
                if any(one(role, "temperature") is None for role in ROLES)
                else "derived_from_meb"
            ),
        )

    def shared(role):
        texts = " ".join(
            str(d.get("text", ""))
            for d in contexts.get(roles[role], {}).get("descriptions", [])
        )
        return len(set(re.findall(r"\bHE[- ]?\d+\b", texts, re.I))) > 1

    side_duties = {}
    side_sources = {}
    for side in ("hot", "cold"):
        inlet, outlet = one(side + "_inlet", "enthalpy_flow"), one(
            side + "_outlet", "enthalpy_flow"
        )
        if not inlet or not outlet:
            continue
        if basis.get("common_enthalpy_reference_confirmed") is not True:
            warnings.append(
                side
                + " enthalpy reference has not been confirmed; no enthalpy duty calculated"
            )
            continue
        q = signed_enthalpy_duty(numeric(inlet, "kW"), numeric(outlet, "kW"), side)
        if shared(side + "_inlet") or shared(side + "_outlet"):
            allocation = inputs.get("utility_allocation_fraction")
            if allocation is None:
                warnings.append(
                    side
                    + " enthalpy streams serve multiple exchangers; duty unavailable without explicit allocation"
                )
                continue
            allocation = positive(allocation, "utility allocation fraction")
            if allocation > 1:
                raise ValueError("Utility allocation fraction cannot exceed one")
            q *= allocation
            warnings.append(
                "Shared utility duty allocated using an explicit assumption"
            )
        side_duties[side] = q
        side_sources[side] = [inlet, outlet]
    selected = basis["duty_side"]
    method = basis["duty_method"]
    if method == "enthalpy_difference":
        if selected not in side_duties:
            raise ValueError(
                "Enthalpy-difference duty requires selected-side inlet/outlet, a common-reference confirmation, and allocation if shared"
            )
        duty = side_duties[selected]
        if duty <= 0:
            raise ValueError(
                "Selected "
                + selected
                + " enthalpy difference has the wrong sign for the stated duty; choose a defensible alternative basis, do not take absolute value silently"
            )
        record(
            "heat_duty_kw",
            duty,
            side_sources[selected],
            "Q = " + ("H_in-H_out" if selected == "hot" else "H_out-H_in"),
        )
    elif method == "assumed_duty":
        duty = positive(inputs.get("heat_duty_kw"), "explicit heat duty kW")
        warnings.append(
            "Heat duty is an explicit preliminary assumption, not a measured balance"
        )
    else:
        source = one(selected + "_inlet", "mass_flow")
        if source is None:
            if basis.get("steady_state_mass_flow_assumed") is not True:
                raise ValueError(
                    "Missing inlet flow requires an explicit steady same-side mass-flow assumption"
                )
            source = one(selected + "_outlet", "mass_flow")
            warnings.append(
                "Outlet mass flow used under explicit steady same-side mass-flow assumption"
            )
        if source is None:
            raise ValueError("Selected side needs a measured total mass-flow rate")
        mass = numeric(source, "kg/h")
        if method == "sensible_heat":
            if (
                phase == "both"
                or (selected == "hot" and phase == "hot_condensing")
                or (selected == "cold" and phase == "cold_boiling")
            ):
                raise ValueError(
                    "Sensible-only duty cannot represent the selected side phase change; use enthalpy or latent-heat basis"
                )
            if selected + "_inlet" not in temps or selected + "_outlet" not in temps:
                raise ValueError("Sensible duty needs inlet/outlet temperatures")
            cp = positive(inputs.get("specific_heat_kj_kg_k"), "specific heat kJ/kg/K")
            delta = (
                temps[selected + "_inlet"] - temps[selected + "_outlet"]
                if selected == "hot"
                else temps[selected + "_outlet"] - temps[selected + "_inlet"]
            )
            duty = mass / 3600 * cp * positive(delta, "sensible temperature change")
            formula = "Q_kW = mass_kg_h / 3600 * Cp_kJ_kg_K * deltaT_K"
        else:
            latent = positive(inputs.get("latent_heat_kj_kg"), "latent heat kJ/kg")
            fraction = positive(
                inputs.get("phase_change_fraction"), "phase-change fraction"
            )
            if fraction > 1:
                raise ValueError("Phase-change fraction cannot exceed one")
            sensible = positive(
                inputs.get("sensible_enthalpy_change_kj_kg"),
                "explicit sensible enthalpy allowance kJ/kg",
                zero=True,
            )
            duty = mass / 3600 * (latent * fraction + sensible)
            formula = "Q_kW = mass_kg_h / 3600 * (latent_heat * phase_fraction + sensible_enthalpy_change)"
            warnings.append(
                "Latent heat/phase fraction are explicit thermophysical assumptions; pressure/composition applicability needs review"
            )
        record(
            "heat_duty_kw",
            duty,
            [source] + [v for v in evidence if v["property"] == "temperature"],
            formula,
            "derived_from_sources_and_assumptions",
        )
    for side, q in side_duties.items():
        if q <= 0:
            warnings.append(
                side
                + " enthalpy duty contradicts expected heat-flow direction; retained as conflicting evidence"
            )
    mismatch = None
    if "hot" in side_duties and "cold" in side_duties:
        hot, cold = side_duties["hot"], side_duties["cold"]
        mismatch = abs(hot - cold) / max(abs(hot), abs(cold), 1e-12)
        if mismatch > 1e-6:
            warnings.append(
                "Hot/cold enthalpy duties disagree; neither is silently corrected"
            )
    policy = basis.get("duty_conflict_policy")
    if policy == "require_consistency":
        tolerance = positive(
            inputs.get("duty_balance_tolerance_fraction"),
            "explicit duty-balance tolerance",
        )
        if tolerance > 1:
            raise ValueError("Duty-balance tolerance must be <=1")
        if (
            mismatch is None
            or mismatch > tolerance
            or any(q <= 0 for q in side_duties.values())
        ):
            raise ValueError(
                "Thermal duty cannot be reconciled within the selected tolerance"
            )
    elif policy != "provisional_selected_side":
        raise ValueError(
            "Select strict reconciliation or an explicit provisional duty-side policy"
        )
    inputs["lmtd_k"] = lmtd
    area, unit, details = calculate("exchanger_area", duty, inputs)
    return (
        area,
        unit,
        {
            **details,
            "thermal_basis": basis,
            "duty_kw": duty,
            "side_enthalpy_duties_kw": side_duties,
            "relative_duty_disagreement": mismatch,
            "warnings": warnings,
            "source_measurements": evidence,
            "source_selections": list(source_selections.values()),
            "resolved_inputs": inputs,
            "derived_inputs": derived,
            "engineering_design_validated": False,
            "scope": "Preliminary thermal area; no mechanical design, phase-equilibrium validation or complete energy-balance certification",
        },
    )
