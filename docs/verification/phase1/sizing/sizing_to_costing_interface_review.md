# Sizing-to-costing interface review

Canonical chain: adapter source measurements and explicit assumptions → registered sizing equation → physical size/unit plus audit → `equipment_costing.registry.estimate_cost` / `resolve_equipment_inputs` → model-specific requirements → unit conversion → cost correlation. Do not bypass the model requirements or equate operating throughput with design capacity. `indexes/garrett/input_requirements.py` and the OpenPyTEA/additional-model adapters define the contracts; a unit match alone does not establish semantic compatibility.

## ion_exchange_capacity

Vessel-volume proxy only; packaged ion-exchange costs G290-104 require original water flow and quality basis, not vessel volume.

## vaporizer_area

Area can feed a compatible vaporizer surface-area model; does not establish mechanical configuration.

## gas_compression

kW converts to horsepower where the selected compressor model requires shaft power; compressor type, stage and pressure limits remain separate.

## phase_change_duty

kW is not heat-transfer area; requires a separate U/LMTD/F stage or a genuinely duty-based model.

## evaporated_water

kg/h water removal cannot directly replace dryer chamber volume or area; latent heat and drying physics still needed.

## ion_exchange_ebct

Volume and packaged water-throughput correlations are different quantities; retain original Q and quality conditions.

## vessel_hold_up

m3 can convert to tank-model capacity (e.g. G303-144), subject to actual service, material, pressure and design allowances.

## pump_duty

G296-122 accepts the flow-pressure coordinate; explicit US gallon basis. Existing canonical costing regression tests this path.

## exchanger_area

m2 to ft2 is dimensionally valid for surface-area models; unit agreement does not prove matching exchanger type.

## filter_area

m2 to ft2 can match G282-076 area coordinate; generic hydraulic loading does not validate a leaf/plate filter design.

## gas_volume

Actual-flow cost models must use compatible T/P/reference and configuration. Not a vessel volume or standard-flow coordinate.

## dryer_chamber

m3 to ft3 is compatible with chamber-volume model G277-062, provisional source basis; incompatible with rotary dryer area G277-061 (tested rejection).

## Executed interface evidence

Existing `test_pump_sizing_flows_into_canonical_cost_model` verifies the pump coordinate reaches G296-122 with an explicit US gallon basis. New tests independently check m2→ft2 and m3→ft3 scale; dryer chamber volume sent to rotary-dryer area model G277-061 is explicitly rejected. The adapter test traces a vessel calculation back to source-Q and rejects residence time labelled kg. Selected alternative flow/mass/duty units are exercised, without claiming full UNIT-001 acceptance.

No cost coefficient, model matching decision or production correlation was modified. IEX packaged-plant flow and resin vessel volume, dryer evaporation and chamber volume, and exchanger duty and surface area require additional physically justified steps. These unsupported direct pairings remain unresolved, not automatic prices. Full field applicability and end-to-end unit acceptance are BLOCKED pending unit verification and model-specific engineering evidence.
