"""Source-backed inputs, explicit assumptions, deterministic sizing and bounds."""

from itertools import product

from .common import positive
from .gases import calculate as gas_volume
from .registry import METHODS, PARAMETER_UNITS, calculate


def observation(report, key, prop):
    stream = next((e for e in report["entities"] if e["key"] == key), None)
    if stream is None:
        raise ValueError("Sizing stream is absent from register")
    rows = [
        v
        for v in stream["values"]
        if v["property"] == prop
        and not v.get("component")
        and v.get("status") != "unresolved"
        and v.get("normalized_value") is not None
    ]
    unique = {(str(v["normalized_value"]), v.get("normalized_unit")) for v in rows}
    if len(unique) != 1:
        raise ValueError("An unambiguous source " + prop + " is required")
    if isinstance(rows[0]["normalized_value"], bool):
        raise ValueError("A boolean cannot be a physical observation")  # noqa: TRY004 -- per-item engineering validation
    return float(rows[0]["normalized_value"]), rows[0]["normalized_unit"], rows[0]["id"]


def derive(sizing, report):
    method = sizing["method"]
    params = sizing.get("parameters", {})
    inputs = {k: v["value"] if isinstance(v, dict) else v for k, v in params.items()}
    for key, record in params.items():
        if key not in PARAMETER_UNITS:
            raise ValueError("Unknown sizing parameter: " + key)
        if isinstance(record, dict) and record.get("unit") not in PARAMETER_UNITS[key]:
            raise ValueError("Sizing parameter unit mismatch: " + key)
        positive(
            inputs[key],
            key,
            zero=key
            in {"sensible_enthalpy_change_kj_kg", "product_water_mass_fraction"},
        )
    sources = []
    definition = METHODS[method]

    def read(prop, key=None):
        value, unit, eid = observation(report, key or sizing.get("stream_key"), prop)
        sources.append(eid)
        return value, unit

    def gas_inputs(values):
        values = dict(values)
        if values.get("temperature_k") is None:
            t, unit = read("temperature")
            if unit != "degC":
                raise ValueError("Gas temperature needs canonical degC or explicit K")
            values["temperature_k"] = t + 273.15
        if values.get("absolute_pressure_bar") is None:
            pressure, unit = read("pressure")
            if unit == "bar_abs":
                values["absolute_pressure_bar"] = pressure
            elif unit == "bar_gauge":
                values["absolute_pressure_bar"] = pressure + positive(
                    values.get("atmospheric_pressure_bar"), "explicit atmosphere bar"
                )
            else:
                raise ValueError("Absolute gas pressure basis unresolved")
        return values

    def compute(values):
        thermal_basis = None
        alternatives = []
        if (
            definition["input"] == "heat_duty"
            and method == "vaporizer_area"
            and values.get("latent_heat_kj_kg") is not None
            and sizing.get("duty_basis", "phase_change") == "phase_change"
        ):
            from .thermal import phase_change_duty

            mass, mass_unit = read("mass_flow")
            if mass_unit != "kg/h":
                raise ValueError("Phase change requires canonical mass flow kg/h")
            value, _, thermal_basis = phase_change_duty(mass, values)
            thermal_basis = {
                **thermal_basis,
                "selected_basis": "explicit_phase_change_assumptions",
                "heat_duty_kw": value,
                "status": "assumption_based_not_verified",
            }
            for basis in ("source_duty", "enthalpy_difference"):
                try:
                    if basis == "source_duty":
                        observed, unit = read("heat_duty")
                    else:
                        if not sizing.get("outlet_stream_key"):
                            continue
                        a, unit = read("enthalpy_flow")
                        b, other_unit = read(
                            "enthalpy_flow", sizing["outlet_stream_key"]
                        )
                        if other_unit != unit:
                            continue
                        observed = b - a
                    if unit == "kW":
                        alternatives.append(
                            {
                                "basis": basis,
                                "heat_duty_kw": abs(observed),
                                "difference_from_selected_kw": abs(observed) - value,
                                "status": "unreconciled_alternative; common-reference/phase/pressure applicability requires review",
                            }
                        )
                except ValueError:
                    pass
        elif definition["input"] == "heat_duty":
            try:
                value, unit = read("heat_duty")
                if unit != "kW":
                    raise ValueError("Heat duty must normalize to kW")
            except ValueError:
                if sizing.get("outlet_stream_key"):
                    a, ua = read("enthalpy_flow")
                    b, ub = read("enthalpy_flow", sizing["outlet_stream_key"])
                    if ua != "kW" or ub != "kW":
                        raise ValueError("Enthalpy rates must share kW basis")
                    value = abs(b - a)
                else:
                    mass, unit = read("mass_flow")
                    if unit != "kg/h":
                        raise ValueError("Sensible duty needs mass flow kg/h")
                    if values.get("latent_heat_kj_kg") is not None:
                        from .thermal import phase_change_duty

                        value = phase_change_duty(mass, values)[0]
                    else:
                        if method == "vaporizer_area":
                            raise ValueError(
                                "Vaporiser requires common-reference enthalpy flow difference or explicit latent heat and phase fraction; sensible Cp alone is insufficient"
                            )
                        value = (
                            mass
                            * positive(
                                values.get("specific_heat_kj_kg_k"),
                                "explicit sensible Cp",
                            )
                            * positive(
                                values.get("temperature_change_k"),
                                "explicit temperature change",
                            )
                            / 3600
                        )
        elif definition["input"] == "mass_flow":
            value, unit = read("mass_flow")
            if unit != "kg/h":
                raise ValueError("Mass flow must normalize to kg/h")
        else:
            try:
                value, unit = read("volume_flow")
                if unit != "m3/h":
                    raise ValueError("Volume flow must normalize to m3/h")
            except ValueError:
                mass, unit = read("mass_flow")
                if unit != "kg/h":
                    raise ValueError("Mass flow must normalize to kg/h")
                if values.get("density_kg_m3") is not None:
                    value = mass / positive(values["density_kg_m3"], "density kg/m3")
                elif method == "dryer_chamber":
                    value, _, _ = gas_volume(mass, gas_inputs(values))
                else:
                    raise ValueError(
                        "Volumetric sizing needs source volume flow or explicit density"
                    )
        size, unit, details = calculate(
            method,
            value,
            gas_inputs(values)
            if method in {"gas_volume", "gas_compression"}
            else values,
        )
        if thermal_basis:
            details = {
                **details,
                "thermal_basis": thermal_basis,
                "unreconciled_alternative_duties": alternatives,
            }
        return size, unit, details

    size, unit, details = compute(inputs)
    ranges = [
        (k, v)
        for k, v in params.items()
        if isinstance(v, dict)
        and v.get("low") is not None
        and v.get("high") is not None
    ]
    if len(ranges) > 8:
        raise ValueError("At most eight ranged sizing assumptions per calculation")
    bounds = []
    for choices in product((0, 1), repeat=len(ranges)) if ranges else []:
        varied = dict(inputs)
        for (key, value), choice in zip(ranges, choices):
            if not value["low"] <= value["value"] <= value["high"]:
                raise ValueError("Sizing bounds must contain selected value")
            varied[key] = value["high"] if choice else value["low"]
        bounds.append(compute(varied)[0])
    return (
        size,
        unit,
        {
            "method": method,
            "source_evidence": list(dict.fromkeys(sources)),
            "assumptions": sizing,
            "status": "preliminary engineering scenario",
            "calculation": details,
            "size_range": {
                "low": min(bounds),
                "high": max(bounds),
                "unit": unit,
                "basis": "Independent assumption endpoints; conditional envelope, not a statistical confidence interval",
            }
            if bounds
            else None,
        },
    )
