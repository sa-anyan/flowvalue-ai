"""Nottingham CEEDG501 Rev 3, equipment-level methods (not CAPEX factors).

Transcribed from sections 4.1-4.3, PDF page 11; date and GBP basis
retained. No Charlie workbook prices, vendor claims or fabricated correlations.
Installation is NOT provided by these methods.
"""
from math import exp
from pathlib import Path

from backend.equipment_costing.indexes.garrett.installation import InstallationBreakdown
from backend.equipment_costing.indexes.garrett.integrated import CostingResult
from backend.equipment_costing.models import CostEstimate, positive

TITLE = "University of Nottingham CEE Design Consultants, CEEDG501 Rev 3"
FILENAME = "CEEDG501 Cost Estimation Rev 3 (1)(1).pdf"
SHA256 = "9b626ffe656fdde1c857a978393380f971070dcfaca500927626e7c962584b57"
PUMP_FACTORS = {
    "cast_iron": 1.0, "cast_steel": 1.5, "stainless_316": 1.7,
    "api610": 2.5, "monel": 3.3, "nickel": 4.5, "hastelloy": 6.0,
}
STEEL_RATES = {"carbon_steel": 4000., "lined_carbon_steel": 5000., "stainless_steel": 12000.}
PIPE_FACTORS = {"pvc_abs": 1.5, "carbon_steel": 6.5, "stainless_steel": 50.}

def list_models():
    rows = []
    for material, factor in PUMP_FACTORS.items():
        rows.append(dict(id="N501-PUMP-"+material.upper(), source="nottingham",
            category="Pump", configuration="Motor-power pump / "+material,
            size_unit="kW", source_year="2015", currency="GBP",
            inputs=["motor_power_kW"], coefficient=factor,
            input_requirements=[dict(quantity="power", unit="kW", required=True)],
            source_page=11, limitation="Generic power/material pump model; PD slurry service suitability NOT established"))
    for material, rate in STEEL_RATES.items():
        rows.append(dict(id="N501-STEEL-"+material.upper(), source="nottingham",
            category="Fabricated steel / vessel", configuration=material,
            size_unit="t", source_year="2016", currency="GBP",
            inputs=["fabricated_steel_mass_t"], coefficient=rate,
            input_requirements=[dict(quantity="mass", unit="t", required=True)],
            source_page=11, limitation="Fabrication-only component; not a priced complete vessel, tank or bioreactor package"))
    for material, factor in PIPE_FACTORS.items():
        rows.append(dict(id="N501-PIPE-"+material.upper(), source="nottingham",
            category="Pipe supply", configuration=material,
            size_unit="in", source_year="2017", currency="GBP",
            inputs=["nominal_diameter_in", "pipe_length_ft"], coefficient=factor,
            input_requirements=[dict(quantity="diameter", unit="in", required=True)],
            source_page=11, limitation="Supply only, unit price per foot; physical length must be explicitly supplied"))
    return rows

def estimate_cost(curve_id, size, *, size_unit, **options):
    models = {m["id"]: m for m in list_models()}
    if curve_id not in models:
        raise ValueError("Unknown Nottingham equipment model")
    model = models[curve_id]
    if size_unit != model["size_unit"]:
        raise ValueError("Nottingham model requires "+model["size_unit"])
    size = positive(size, "model size")
    if size > 1e9:
        raise ValueError("Implausible model input; verify engineering units")
    family = curve_id.split("-")[1]
    factor = model["coefficient"]
    if family == "PUMP":
        # CEEDG501 p.11: c=F*p*2000*p^-0.3 = 2000 F p^0.7.
        # Page doesn't explicitly print motor-power units; kW assumption is disclosed.
        amount = 2000 * factor * size ** 0.7
        formula = "GBP(2015) = 2000 * material_factor * motor_power**0.7"
        scope = "purchased_equipment"
        issues = ("Motor-power unit assumed kW (source does not explicitly specify units); preliminary pump model, not a positive-displacement-specific quotation.",)
    elif family == "STEEL":
        amount = factor * size
        formula = "GBP(2016) = fabricated_steel_mass_t * GBP_per_t"
        scope = "purchased_equipment"
        issues = ("Fabricated steelwork component ONLY; estimate omits fittings, internals, controls, design/testing and package equipment. Do not interpret as full vessel purchased price.",)
    elif family == "PIPE":
        # Published GBP/m is converted to GBP/ft for shared physical-quantity aggregation.
        amount = factor * exp(0.6 * size) * 0.3048
        formula = "GBP(2017)/ft = material_factor * exp(0.6 * diameter_in) * 0.3048"
        scope = "unit_price_per_ft"
        issues = ("Pipe supply-only, excludes fittings/installation; total requires explicit length in ft.",)
    else:
        raise ValueError("Unsupported Nottingham formula family")
    estimate = CostEstimate(
        model["category"], model["configuration"], amount, "GBP", 1.0,
        model["source_year"], size, size_unit, scope, formula, 11, 11,
        TITLE, FILENAME, SHA256,
        notes=issues + ("Nottingham methodology; historical GBP amount; general inflation escalation is an optional separate stage.",),
        index_series="SOURCE_PRICE_BASIS",
    )
    evidence = dict(source="nottingham", source_filename=FILENAME, source_sha256=SHA256,
        source_page=11, model_id=curve_id, model_metadata=model,
        applied_parameter=size, unit=size_unit, historical_price=amount,
        status="published_equation_preliminary", issues=list(issues))
    installation = InstallationBreakdown(
        amount if scope == "purchased_equipment" else None, None, None,
        None, "not_provided", evidence)
    return CostingResult("provisional", estimate, amount, issues,
                         evidence, installation=installation)
