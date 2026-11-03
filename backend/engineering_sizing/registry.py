"""Allowlisted functions for AI-selected engineering methods; never execute model code."""

from . import (
    compression,
    dryers,
    filters,
    gases,
    heat_exchangers,
    ion_exchange,
    pumps,
    thermal,
    vessels,
)

METHODS = {
    "ion_exchange_capacity": {
        "input": "volume_flow",
        "unit": "m3/h",
        "calculator": ion_exchange.capacity_sizing,
        "parameters": [
            "ionic_load_mol_equiv_m3",
            "service_cycle_h",
            "working_resin_capacity_mol_equiv_m3",
            "resin_bed_fraction",
        ],
    },
    "vaporizer_area": {
        "input": "heat_duty",
        "unit": "kW",
        "calculator": heat_exchangers.calculate,
        "parameters": [
            "latent_heat_kj_kg",
            "phase_change_fraction",
            "sensible_enthalpy_change_kj_kg",
            "overall_u_w_m2_k",
            "lmtd_k",
            "lmtd_correction",
        ],
    },
    "gas_compression": {
        "input": "mass_flow",
        "unit": "kg/h",
        "calculator": compression.calculate,
        "parameters": [
            "molecular_weight_kg_kmol",
            "temperature_k",
            "absolute_pressure_bar",
            "discharge_pressure_bar",
            "heat_capacity_ratio",
            "efficiency",
            "compressibility_z",
        ],
    },
    "phase_change_duty": {
        "input": "mass_flow",
        "unit": "kg/h",
        "calculator": thermal.phase_change_duty,
        "parameters": [
            "latent_heat_kj_kg",
            "phase_change_fraction",
            "sensible_enthalpy_change_kj_kg",
        ],
    },
    "evaporated_water": {
        "input": "mass_flow",
        "unit": "kg/h",
        "calculator": thermal.evaporated_water,
        "parameters": ["feed_water_mass_fraction", "product_water_mass_fraction"],
    },
    "ion_exchange_ebct": {
        "input": "volume_flow",
        "unit": "m3/h",
        "calculator": ion_exchange.calculate,
        "parameters": ["empty_bed_contact_time_min", "resin_bed_fraction"],
    },
    "vessel_hold_up": {
        "input": "volume_flow",
        "unit": "m3/h",
        "calculator": vessels.calculate,
        "parameters": ["residence_time_h", "working_fraction"],
    },
    "pump_duty": {
        "input": "volume_flow",
        "unit": "m3/h",
        "calculator": pumps.calculate,
        "parameters": ["differential_pressure_bar", "efficiency"],
    },
    "exchanger_area": {
        "input": "heat_duty",
        "unit": "kW",
        "calculator": heat_exchangers.calculate,
        "parameters": ["overall_u_w_m2_k", "lmtd_k", "lmtd_correction"],
    },
    "filter_area": {
        "input": "volume_flow",
        "unit": "m3/h",
        "calculator": filters.calculate,
        "parameters": ["hydraulic_loading_m_h"],
    },
    "gas_volume": {
        "input": "mass_flow",
        "unit": "kg/h",
        "calculator": gases.calculate,
        "parameters": [
            "molecular_weight_kg_kmol",
            "temperature_k",
            "absolute_pressure_bar",
            "compressibility_z",
        ],
    },
    "dryer_chamber": {
        "input": "volume_flow",
        "unit": "m3/h",
        "calculator": dryers.calculate,
        "parameters": ["gas_residence_time_s"],
    },
}


def list_methods():
    return [
        {"id": k, **{n: v for n, v in row.items() if n != "calculator"}}
        for k, row in METHODS.items()
    ]


def calculate(method, value, inputs):
    if method not in METHODS:
        raise ValueError("Unsupported engineering sizing method: " + str(method))
    result = METHODS[method]["calculator"](value, inputs)
    from .common import positive

    positive(result[0], "calculated equipment size")
    return result


PARAMETER_UNITS = {
    "ionic_load_mol_equiv_m3": ("mol_equiv/m3",),
    "service_cycle_h": ("h",),
    "working_resin_capacity_mol_equiv_m3": ("mol_equiv/m3",),
    "discharge_pressure_bar": ("bar_abs", "bara"),
    "heat_capacity_ratio": ("fraction",),
    "latent_heat_kj_kg": ("kJ/kg",),
    "phase_change_fraction": ("fraction",),
    "sensible_enthalpy_change_kj_kg": ("kJ/kg",),
    "feed_water_mass_fraction": ("fraction",),
    "product_water_mass_fraction": ("fraction",),
    "empty_bed_contact_time_min": ("min",),
    "resin_bed_fraction": ("fraction",),
    "density_kg_m3": ("kg/m3", "kg/m^3", "kg/m³"),
    "residence_time_h": ("h", "hr", "hours"),
    "working_fraction": ("fraction",),
    "differential_pressure_bar": ("bar", "bar_delta"),
    "efficiency": ("fraction",),
    "overall_u_w_m2_k": ("W/m2/K", "W/m²/K", "W/(m2 K)"),
    "lmtd_k": ("K",),
    "lmtd_correction": ("fraction",),
    "hydraulic_loading_m_h": ("m3/m2/h", "m/h"),
    "molecular_weight_kg_kmol": ("kg/kmol",),
    "temperature_k": ("K",),
    "absolute_pressure_bar": ("bar_abs", "bara"),
    "atmospheric_pressure_bar": ("bar_abs", "bara"),
    "compressibility_z": ("fraction",),
    "gas_residence_time_s": ("s",),
    "specific_heat_kj_kg_k": ("kJ/kg/K",),
    "temperature_change_k": ("K",),
}
