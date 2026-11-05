"""Allowlisted M&E arithmetic; an LLM selects evidence, never supplies its result."""

import math
from .. import convert, ConversionContext, identify_unit

METHODS = {
    "source_value",
    "mixture_molecular_weight",
    "density_from_flows",
    "temperature_kelvin",
    "absolute_pressure",
    "pressure_difference",
    "lmtd_countercurrent",
    "lmtd_parallel",
}
TARGETS = {
    "density_kg_m3": "kg/m3",
    "temperature_k": "K",
    "absolute_pressure_bar": "bar_abs",
    "differential_pressure_bar": "bar",
}


def derive(bindings, observations, inputs, unit_context):
    out = dict(inputs)
    audit = []
    by = {v["id"]: v for v in observations}
    context = ConversionContext(**(unit_context or {}))

    def cv(v, unit):
        result = convert(v["value"], v["unit"], unit, context=context)
        if result.value is None:
            raise ValueError("; ".join(result.issues))
        return result.value

    seen = set()
    for b in bindings:
        name, method = b["name"], b["method"]
        if name in seen or method not in METHODS:
            raise ValueError("Duplicate or unsupported M&E derivation")
        seen.add(name)
        try:
            values = [by[i] for i in b["measurement_ids"]]
        except KeyError as exc:
            raise ValueError(
                "Derivation references unlinked or unresolved source data"
            ) from exc
        if len({v["id"] for v in values}) != len(values):
            raise ValueError("Derivation source repeated")
        if method == "source_value":
            if len(values) != 1 or name not in TARGETS:
                raise ValueError("Unsupported direct parameter binding")
            answer = cv(values[0], TARGETS[name])
            formula = "canonical same-dimension conversion"
        elif method in {"mixture_molecular_weight", "density_from_flows"}:
            expected = (
                "molecular_weight_kg_kmol"
                if method == "mixture_molecular_weight"
                else "density_kg_m3"
            )
            if (
                name != expected
                or len(values) != 2
                or values[0]["entity_key"] != values[1]["entity_key"]
            ):
                raise ValueError("Ratio needs totals from the same stream")
            expected_props = (
                {"mass_flow", "molar_flow"}
                if method == "mixture_molecular_weight"
                else {"mass_flow", "volume_flow"}
            )
            if {v["property"] for v in values} != expected_props:
                raise ValueError("Use total mass and matching total molar/volume flow")
            mass = next(v for v in values if v["property"] == "mass_flow")
            other = next(v for v in values if v["property"] != "mass_flow")
            denominator = cv(
                other, "kmol/h" if method == "mixture_molecular_weight" else "m3/h"
            )
            if denominator <= 0:
                raise ValueError("Nonpositive ratio denominator")
            answer = cv(mass, "kg/h") / denominator
            formula = "mass flow / same-stream molar or volumetric flow"
        elif method == "temperature_kelvin":
            if (
                name != "temperature_k"
                or len(values) != 1
                or values[0]["property"] != "temperature"
            ):
                raise ValueError("Temperature observation required")
            answer = cv(values[0], "K")
            formula = "source temperature -> kelvin"
        elif method == "absolute_pressure":
            if (
                name != "absolute_pressure_bar"
                or len(values) != 1
                or values[0]["property"] != "pressure"
            ):
                raise ValueError("Pressure observation required")
            answer = cv(values[0], "bar_abs")
            formula = "source pressure -> absolute bar; explicit atmosphere if gauge"
        elif method == "pressure_difference":
            if (
                name != "differential_pressure_bar"
                or len(values) != 2
                or any(v["property"] != "pressure" for v in values)
            ):
                raise ValueError("Ordered inlet/outlet pressures required")
            bases = [
                identify_unit(v["unit"], context=context).pressure_basis for v in values
            ]
            if bases[0] == bases[1] and bases[0] is not None:
                answer = cv(values[1], "bar") - cv(values[0], "bar")
            else:
                answer = cv(values[1], "bar_abs") - cv(values[0], "bar_abs")
            formula = "outlet absolute pressure - inlet absolute pressure"
        else:
            if (
                name != "lmtd_k"
                or len(values) != 4
                or any(v["property"] != "temperature" for v in values)
            ):
                raise ValueError(
                    "Ordered hot-in/hot-out/cold-in/cold-out temperatures required"
                )
            hi, ho, ci, co = [cv(v, "K") for v in values]
            if hi < ho or co < ci:
                raise ValueError("Temperature roles inconsistent with heating/cooling")
            a, bb = (
                (hi - co, ho - ci)
                if method == "lmtd_countercurrent"
                else (hi - ci, ho - co)
            )
            if a <= 0 or bb <= 0:
                raise ValueError("Temperature cross/zero driving force is unsupported")
            answer = (
                a if math.isclose(a, bb, rel_tol=1e-10) else (a - bb) / math.log(a / bb)
            )
            formula = (
                "LMTD = (deltaT1-deltaT2)/ln(deltaT1/deltaT2) for selected arrangement"
            )
        if not math.isfinite(answer) or answer <= 0:
            raise ValueError("Derived physical input must be finite and positive")
        out[name] = answer
        audit.append(
            {
                "name": name,
                "value": answer,
                "method": method,
                "formula": formula,
                "status": "derived_from_meb",
                "source_measurements": values,
            }
        )
    return out, audit


def discover(observations, measurement_id, method, unit_context):
    """Safe same-stream candidates; equipment duty and connection roles remain explicit."""
    source = next((v for v in observations if v["id"] == measurement_id), None)
    if source is None:
        return []
    group = [v for v in observations if v["entity_key"] == source["entity_key"]]

    def one(prop):
        vals = [v for v in group if v["property"] == prop]
        return vals[0] if len(vals) == 1 else None

    def binding(name, route, values):
        return {
            "name": name,
            "method": route,
            "measurement_ids": [v["id"] for v in values],
        }

    found = []
    mass, molar, volume = one("mass_flow"), one("molar_flow"), one("volume_flow")
    if method in {"gas_flow", "dryer_volume"}:
        if mass and molar:
            found.append(
                binding(
                    "molecular_weight_kg_kmol",
                    "mixture_molecular_weight",
                    [mass, molar],
                )
            )
        temp, pressure = one("temperature"), one("pressure")
        if temp:
            found.append(binding("temperature_k", "temperature_kelvin", [temp]))
        if pressure:
            try:
                result = convert(
                    pressure["value"],
                    pressure["unit"],
                    "bar_abs",
                    context=ConversionContext(**(unit_context or {})),
                )
                if result.value is not None:
                    found.append(
                        binding(
                            "absolute_pressure_bar", "absolute_pressure", [pressure]
                        )
                    )
            except (ValueError, TypeError):
                pass
    elif method in {
        "liquid_flow",
        "vessel_volume",
        "filter_area",
        "pump_coordinate",
        "pump_power",
        "mixing_power",
    }:
        if mass and volume:
            found.append(binding("density_kg_m3", "density_from_flows", [mass, volume]))
        density = one("density")
        if density and not any(b["name"] == "density_kg_m3" for b in found):
            found.append(binding("density_kg_m3", "source_value", [density]))
    return found
