# Shared engineering unit conversion

The conversion engine is shared. Equipment/source definitions declare required physical quantities and native chart units beside the costing source (`garrett/input_requirements.py`). There is no copy of kg/lb/pressure conversion logic in each equipment module.

## Files and responsibilities

- `unit_conversion.py`: identification, dimensional conversion and explicit-field input resolution.
- `unit_aliases.py`: finite supported units, spelling aliases and constants.
- `models.py`: measurements, conversion context, equipment requirements and results.
- `garrett/input_requirements.py`: contracts for all 154 current curve configurations; no conversion arithmetic.
- `registry.py`: converts non-native size units before routing through the unchanged numerical cost models. Parsed/context adapter preserves source evidence.

The catalogue covers common mass, mass flow, length, area, volume, volume flow, pressure, absolute temperature and temperature difference, energy/power, density, molar amount/flow, and selected explicitly defined compound coordinates. It does not claim every possible engineering unit. SI symbol case matters: MW and mW are different. Unknown symbols, number strings and unsupported dimensions return issues; no Python expression is evaluated.

## Basic conversion

```python
from backend.equipment_costing.unit_conversion import convert, ConversionContext

result = convert(1000, "kg/hour", "lb/h", source={"worksheet": "Streams", "cell": "D8"})
assert result.status == "converted"
print(result.value, result.original, result.assumptions)

pressure = convert(
    0,
    "psig",
    "psia",
    context=ConversionContext(atmospheric_pressure_pa=101325),
)
```

101325 Pa in the example is explicitly supplied, not a default local atmospheric pressure. Conversion preserves a stated pressure basis unless a gauge/absolute change is explicitly requested. Unknown pressure basis remains unknown and is recorded in assumptions. Unit normalization is not validation of a vessel pressure rating.

## Costing with converted inputs

```python
from backend.equipment_costing.registry import estimate_cost
from backend.equipment_costing.unit_conversion import ConversionContext

result = estimate_cost(
    "G258-004",
    0.3785411784,
    size_unit="m3",
    unit_context=ConversionContext(target_gallon_basis="US"),
    input_provenance={"worksheet": "Equipment", "cell": "C2"},
    allow_unverified=True,
)
# Equivalent to 100 US gallons: roughly $47,070 equipment, $28,242 installation,
# $75,312 combined, historical 1987 USD. Source gallon interpretation is explicit.
```

The original source-coordinate API remains compatible. Passing exactly the model's existing unit label without conversion context retains its original source-coordinate meaning; it does not assert a newly verified SI/gallon/ton basis. Non-native units are normalized through the shared converter; ambiguous source targets require explicit interpretation. The new parsed adapter always resolves units, even when the input and target labels appear identical.

For ambiguous labels, context distinguishes **input** and **target** meanings: `input_gallon_basis` / `target_gallon_basis` (US or Imperial) and `input_ton_basis` / `target_ton_basis` (metric, short, long or refrigeration). This prevents silently asserting the workbook's source-gallon or ton definition.

```python
from backend.equipment_costing.registry import estimate_from_parsed_inputs
from backend.equipment_costing.unit_conversion import Measurement

result = estimate_from_parsed_inputs(
    "G287-092",
    {
        "size": Measurement(200, "ft2", {"worksheet": "Equipment", "cell": "D5"}),
        "design_pressure": Measurement(10, "barg", {"cell": "E5"}),
        "temperature": Measurement(25, "degC", {"cell": "F5"}),
    },
)
```

Only `size` drives the explicitly selected curve. Pressure and temperature are normalized context and do not automatically choose another curve or apply a correction factor. Operating pressure never fills a missing design-pressure field. `resolve_equipment_inputs()` returns structured unresolved issues for clarification without calculating a price; the costing adapter raises `UnitResolutionError` when those inputs are unresolved. Parser adapters must map their explicit semantic fields to the declared requirements; there is no LLM inference or automatic extraction from arbitrary prose in this module.

## Totals and quantities

`total_cost.calculate_total_cost()` inherits size conversion through the registry. Per-foot/area/volume/tray quantities also use the shared converter when the supplied physical unit differs from the model's quantity unit. For example, 100 m of duct is converted to feet before equipment, installation and combined unit prices are each extended. Quantity conversion and original source values are retained on the line. Incompatible or ambiguous quantities remain blocked.

## Engineering boundaries

- Mass does not become mass flow without a time basis. Flow does not become vessel volume without sizing/residence-time information.
- Mass and molar flow are not interconverted without composition/molecular-weight information.
- Refrigeration tons are thermal capacity, not mass. Conversion of kW to refrigeration tons does not establish that electrical consumption equals cooling duty or assume a COP.
- US and Imperial gallons and metric/short/long tons are separate. Ambiguous labels require context.
- Btu_IT and thermochemical Btu differ. Bare Btu needs an explicitly supplied `btu_basis`.
- Boiler horsepower is an identity-only quantity here: the source footnote is unresolved, so it is not converted to mechanical horsepower or watts.
- Actual versus standard gas flow is not automatically converted. Standard/normal gas unit conversion requires explicitly identical reference conditions; changing conditions requires a separate thermodynamic calculation. No atmospheric pressure, reference temperature, compressibility or gas density is invented.
- Absolute temperatures cannot be below zero kelvin. Temperature differences use separate units. Signed energy/power and stream-flow values are preserved by conversion; costing models retain their own positive-size checks.
- Unresolved dryer plot scaling, vacuum multiplication/division and grouped-pump source conflicts remain blocked by the equipment contract. Their existence is not solved by dimensional conversion.
- No units are read from images or graph pressures here. Source reading, equipment classification, mechanical design and calibration remain separate responsibilities.

## Sources and verification

Constants and conventional definitions were checked against [NIST SP 811, Appendix B.8](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b8) and [B.9](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b9). Exact international inch/foot and avoirdupois pound definitions are used to derive US gallon and psi; Imperial gallon is 0.00454609 m3. Thermal constants distinguish the stated Btu conventions. Floating-point implementation does not imply more engineering accuracy than source data. No third-party conversion code or new dependency is incorporated.

Run `python3 -m unittest discover -s backend/tests -v`. All 85 test methods pass: 18 new conversion/adapter/round-trip/quantity tests plus previous costing, factor, installation and totals checks. Tests include independent constants, ambiguity, pressure references, dimensional mismatches, source lineage, absolute zero, prefix case and equality of native/converted costing results. This is backend verification, not an upload-to-browser UI test; the clean rebuild has no active parser/frontend integration.

## UNIT-003 active parameter units (11 November 2026)

Velocity (`m/s`, `m/h`, `ft/s`, `ft/min`; hydraulic loading `m3/m2/h`),
standalone time (`s`, `min`, `h`, `day` and bounded word spellings), and
heat-transfer coefficient (`W/m2/K`, `kW/m2/K`, explicit IT/thermochemical
`Btu/(h*ft2*delta_degF)`) now use the canonical converter. Bare Btu in the
supported coefficient spellings needs `ConversionContext.btu_basis`. The
Fahrenheit term is an interval; it never receives an absolute-temperature offset.
This finite vocabulary is not a general dimensional expression parser.

`sizing_parameters.normalize_parameters` converts typed `value/unit` records,
including supplied `low/high` endpoints, for the six existing native time,
hydraulic-loading and U parameters. The sizing adapter and equipment bridge
service use it before calling the unchanged native equations. Source values,
units and source-cell references are retained in `parameter_unit_conversions`;
original assumptions remain separate. Bare numbers retain the existing explicit
native-unit API. Other parameter families keep their existing native allowlists.
No UI, parser or API schema was changed; callers must supply typed backend records
for these alternative units. This does not enable arbitrary unit entry in a UI.

`relationships.average_power(energy, duration)` and
`relationships.residence_time(working_volume, actual_volume_flow)` explicitly
perform E/time and V/Q with typed source-linked measurements and output lineage.
They require positive denominators and never infer duration, working fraction,
phase or common-state applicability. They are reusable backend helpers, not new
LLM tools or automatic inference recipes. Average power is not peak/driver power.
Existing mass/density and actual/reference gas bridges remain separate and require
their supplied density or positive absolute T/P/Z assumptions.

The original 191 definitions and 562 alias bindings remain unchanged. Optional
viscosity/SG conversions, opaque gas-reference validation, source-specific boiler
hp-to-W, and the eleven blocked source-coordinate contracts are not unlocked by
these additions. Current evidence and limits are recorded in
`docs/verification/phase1/units/UNIT-003/`; earlier reports remain historical.
