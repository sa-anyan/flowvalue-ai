"""Equipment utility demand and annual energy cost from explicit M&E/scenario inputs.

Electrical input, shaft work, hydraulic work and thermal duty have distinct bases.
No absent duty is manufactured from stream temperature or pressure alone.
"""

from decimal import localcontext

from .consumption import decimal, observation


def equipment_energy_cost(spec, report, *, operating_hours, throughput_fraction=1):
    """Return kW, kWh/year and cost from supported deterministic methods.

    Any assumed motor duty, efficiency, load, pressure difference, specific energy
    or power density is passed explicitly by the engineer/LLM and retained.
    """
    with localcontext() as context:
        context.prec = 40
        hours = decimal(operating_hours, maximum=8784)
        ramp = (
            decimal(throughput_fraction, maximum=1)
            if spec.get("behavior", "variable") == "variable"
            else decimal(1)
        )
        load = decimal(spec["load_fraction"], maximum=1)
        efficiency = decimal(spec["efficiency"], minimum=None)
        if not 0 < efficiency <= 1:
            raise ValueError("Energy conversion efficiency must be (0,1]")
        method = spec["method"]
        evidence = []
        if method == "measured_electrical":
            v = observation(report, spec["source_key"], "power")
            if v["normalized_unit"] != "kW":
                raise ValueError("Electrical power must normalise to kW")
            kw = decimal(v["normalized_value"])
            evidence.append(v["id"])
        elif method == "electrical_assumption":
            kw = decimal(spec["power_kw"])
        elif method in {"shaft_power", "thermal_duty"}:
            kw = decimal(spec["power_kw"]) / efficiency
        elif method == "hydraulic":
            v = observation(report, spec["source_key"], "volume_flow")
            if v["normalized_unit"] != "m3/h":
                raise ValueError("Hydraulic demand requires actual volumetric flow")
            kw = (
                decimal(v["normalized_value"])
                / 3600
                * decimal(spec["pressure_difference_bar"])
                * 100000
                / efficiency
                / 1000
            )
            evidence.append(v["id"])
        elif method == "specific_energy":
            v = observation(report, spec["source_key"], "mass_flow")
            if v["normalized_unit"] != "kg/h":
                raise ValueError("Specific energy requires mass flow in kg/h")
            kw = decimal(v["normalized_value"]) * decimal(spec["specific_kwh_per_kg"])
            evidence.append(v["id"])
        elif method == "power_density":
            kw = (
                decimal(spec["volume_m3"])
                * decimal(spec["power_density_w_m3"])
                / 1000
                / efficiency
            )
        else:
            raise ValueError("No deterministic energy method: " + str(method))
        energy = kw * load * hours * ramp
        return {
            "id": spec["id"],
            "equipment_key": spec["equipment_key"],
            "name": spec["name"],
            "method": method,
            "utility": spec["utility"],
            "input_kw": kw,
            "load_fraction": load,
            "annual_energy_kwh": energy,
            "tariff_per_kwh": decimal(spec["tariff_per_kwh"]),
            "annual_cost": energy * decimal(spec["tariff_per_kwh"]),
            "source_evidence": evidence,
            "assumptions": spec,
            "basis": "Scenario input demand × load × common operating hours × applicable production ramp × tariff",
        }
