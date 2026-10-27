"""Run a fixed, trusted BioSTEAM template locally. No uploaded code is executed.

Usage: python -m app.integrations.biosteam_runner --output water-heating.json
Install the isolated requirements-biosteam.txt environment first.
"""

import argparse
import json
import subprocess
import sys
import warnings
from importlib.metadata import version
from pathlib import Path

from pydantic import Field

from app.engine.costing import Model
from app.integrations.libraries import BioSTEAMSnapshot, ExternalUnit
from app.parsers.stream_parser import Stream


class WaterHeatingInputs(Model):
    mass_flow_kg_h: float = Field(default=10000, ge=1000, le=100000)
    outlet_temperature_c: float = Field(default=80, ge=35, le=90)
    discharge_pressure_bar_abs: float = Field(default=3, ge=2, le=10)
    operating_hours_per_year: float = Field(default=8000, gt=0, le=8760)
    feed_price_usd_kg: float = Field(default=0.001, ge=0, le=10)
    product_price_usd_kg: float = Field(default=0.01, ge=0, le=10)
    electricity_price_usd_kwh: float = Field(default=0.08, ge=0, le=10)
    fixed_opex_usd_per_year: float = Field(default=100000, ge=0, le=1e12)
    reference_cepci: float = Field(default=800, gt=0, le=1e6)


def export_system(
    system,
    product,
    *,
    fixed_opex_usd_per_year,
    reference_cepci,
    provenance,
    is_demo=False,
):
    """Export an already simulated, trusted single-product System in kg/USD units."""
    if len(system.products) != 1 or not any(product is p for p in system.products):
        raise ValueError(
            "Only a single boundary product is supported; coproduct revenue needs explicit reconciliation"
        )
    hours = system.operating_hours
    if hours is None or hours <= 0 or hours > 8760:
        raise ValueError(
            "Set valid system operating_hours before exporting annual quantities"
        )
    if system.utility_cost < 0:
        raise ValueError(
            "Net utility credits require explicit financial treatment; negative utility OPEX is unsupported"
        )
    units = list(system.units)
    equipment = [
        ExternalUnit(
            unit_id=u.ID,
            purchased_cost_usd=float(u.purchase_cost),
            installed_cost_usd=float(u.installed_cost),
        )
        for u in units
        if u.purchase_cost > 0 and u.installed_cost > 0
    ]
    excluded = [u.ID for u in units if u.purchase_cost <= 0 or u.installed_cost <= 0]
    priced_ids = {u.ID for u in units}
    streams = []
    for stream in system.streams:
        if stream.F_mass <= 0:
            continue
        phase = (
            "mixed"
            if len(stream.phases) > 1
            else {"l": "liquid", "L": "liquid", "g": "gas", "s": "solid"}.get(
                stream.phase, "mixed"
            )
        )
        streams.append(
            Stream(
                stream_id=stream.ID,
                mass_flow_kg_h=float(stream.F_mass),
                temperature_c=float(stream.T) - 273.15,
                pressure_bar_abs=float(stream.P) / 1e5,
                phase=phase,
                source_unit=stream.source.ID
                if stream.source and stream.source.ID in priced_ids
                else None,
                destination_unit=stream.sink.ID
                if stream.sink and stream.sink.ID in priced_ids
                else None,
            )
        )
    notes = [
        f"Annualization: {hours:g} operating hours/year. Single boundary product, mass basis kg. System was simulated in a trusted local environment."
    ]
    if excluded:
        notes.append(
            "INCOMPLETE EQUIPMENT SCOPE: "
            + ", ".join(excluded)
            + " have no positive exported costs; confirm whether costing is required."
        )
    return BioSTEAMSnapshot(
        schema_version="flowvalue-biosteam-v1",
        project_name=system.ID,
        process_classification="general",
        is_demo=is_demo,
        library_version=version("biosteam"),
        reference_cepci=reference_cepci,
        provenance=provenance,
        equipment=equipment,
        streams=streams,
        assumptions=notes,
        fixed_opex_usd_per_year=fixed_opex_usd_per_year,
        variable_opex_usd_per_year=float(system.material_cost + system.utility_cost),
        feedstock_opex_usd_per_year=float(system.material_cost),
        utility_opex_usd_per_year=float(system.utility_cost),
        production_units_per_year=float(product.F_mass * hours),
        selling_price_usd_per_unit=float(product.price),
    ).model_dump(mode="json")


def run_water_heating(inputs: WaterHeatingInputs) -> dict:
    import biosteam as bst

    bst.main_flowsheet.set_flowsheet(bst.Flowsheet("flowvalue_water_heating"))
    bst.settings.set_thermo(["Water"])
    bst.settings.CEPCI = inputs.reference_cepci
    bst.settings.electricity_price = inputs.electricity_price_usd_kwh
    feed = bst.Stream(
        "feed",
        Water=inputs.mass_flow_kg_h,
        units="kg/hr",
        T=298.15,
        P=101325,
        price=inputs.feed_price_usd_kg,
    )
    pump = bst.Pump(
        "P101", ins=feed, outs="pressurized", P=inputs.discharge_pressure_bar_abs * 1e5
    )
    heater = bst.HXutility(
        "E101", ins=pump - 0, outs="product", T=inputs.outlet_temperature_c + 273.15
    )
    system = bst.System(
        "water_heating_demo",
        path=(pump, heater),
        operating_hours=inputs.operating_hours_per_year,
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        system.simulate()
    product = heater.outs[0]
    product.price = inputs.product_price_usd_kg
    snapshot = export_system(
        system,
        product,
        fixed_opex_usd_per_year=inputs.fixed_opex_usd_per_year,
        reference_cepci=inputs.reference_cepci,
        provenance="Supported water-heating template: liquid water at 25 C, pump then utility heater. Illustrative prices/fixed OPEX; no validated commercial product economics.",
        is_demo=True,
    )
    # Independent screening check: liquid-water Cp ~4.18 kJ/kg/K over this range.
    expected_duty = inputs.mass_flow_kg_h * 4.18 * (inputs.outlet_temperature_c - 25)
    actual_duty = float(heater.Hnet)
    diagnostics = {
        "mass_balance_error_kg_h": float(product.F_mass - feed.F_mass),
        "heater_duty_kj_h": actual_duty,
        "constant_cp_reference_kj_h": expected_duty,
        "constant_cp_relative_error": abs(actual_duty - expected_duty) / expected_duty,
    }
    if (
        abs(diagnostics["mass_balance_error_kg_h"]) > 1e-6
        or diagnostics["constant_cp_relative_error"] > 0.03
    ):
        raise ValueError("Supported template failed mass/energy reference checks")
    snapshot["assumptions"] += [str(w.message)[:400] for w in caught][:20]
    snapshot["assumptions"].append(
        f"Illustrative assumptions: electricity {inputs.electricity_price_usd_kwh:g} USD/kWh, fixed OPEX {inputs.fixed_opex_usd_per_year:g} USD/year, CEPCI {inputs.reference_cepci:g}. Steam/cooling prices are BioSTEAM defaults, not current market quotations."
    )
    snapshot["assumptions"].append(
        "Template checks: mass balance within 1e-6 kg/h; duty within 3% of constant-Cp water reference. These checks do not independently validate library cost correlations."
    )
    return {
        "snapshot": BioSTEAMSnapshot.model_validate(snapshot).model_dump(mode="json"),
        "diagnostics": diagnostics,
        "inputs": inputs.model_dump(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inputs",
        type=Path,
        help="Optional WaterHeatingInputs JSON; no code or import paths accepted",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.worker:
        command = [
            sys.executable,
            "-m",
            "app.integrations.biosteam_runner",
            "--worker",
            "--output",
            str(args.output),
        ]
        if args.inputs:
            command += ["--inputs", str(args.inputs)]
        try:
            subprocess.run(command, check=True, timeout=300)
        except subprocess.TimeoutExpired:
            raise SystemExit(
                "BioSTEAM exceeded the 300-second limit. No new output was saved; check isolated dependency compatibility."
            ) from None
        except subprocess.CalledProcessError:
            raise SystemExit(
                "BioSTEAM worker failed. No new output was saved; check the diagnostic above."
            ) from None
        return
    inputs = (
        WaterHeatingInputs.model_validate_json(args.inputs.read_text())
        if args.inputs
        else WaterHeatingInputs()
    )
    result = run_water_heating(inputs)
    args.output.write_text(json.dumps(result["snapshot"], indent=2) + "\n")
    args.output.with_suffix(".checks.json").write_text(
        json.dumps({k: v for k, v in result.items() if k != "snapshot"}, indent=2)
        + "\n"
    )
    print(
        f"Saved validated snapshot to {args.output}; checks in {args.output.with_suffix('.checks.json')}"
    )


if __name__ == "__main__":
    main()
