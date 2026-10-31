# Complete Garrett Appendix 1 equipment coverage

All 51 chart groups on printed pages 256–306 (PDF pages 6–56) are catalogued. Four groups have direct-price equations; 39 have reference-price scaling; eight are graph-only and have no implemented cost calculation. Counts refer to page/chart groups, not individual variants. Buildings, insulation and piping are retained as capital items even though not discrete process equipment.

Reference scaling requires a documented price, compatible configuration and reviewed size interval. Graph-only entries are inventory records, not working calculators. No curve fits, graph prices, or borrowed exponents were invented.

| Equipment group | Printed page | Category | Module |
|---|---|---|---|
| Activated-carbon adsorbers | 256 | direct_price | activated_carbon_adsorbers |
| Agitators | 257 | reference_scaling | agitators |
| Agitated tanks | 258 | reference_scaling | agitated_tanks |
| Air conditioning | 259 | reference_scaling | air_conditioning |
| Blenders | 260 | reference_scaling | blenders |
| Blowers | 261 | reference_scaling | blowers |
| Boilers | 262 | reference_scaling | boilers |
| Waste-heat boilers | 263 | reference_scaling | waste_heat_boilers |
| Buildings | 264 | reference_scaling | buildings |
| Centrifuges | 265 | graph_only | Not implemented |
| Chimneys/stacks | 266 | reference_scaling | chimneys_stacks |
| Classifiers | 267 | reference_scaling | classifiers |
| Columns | 268 | reference_scaling | columns |
| Column trays | 269 | graph_only | Not implemented |
| Column packing | 270 | reference_scaling | column_packing |
| Medium/low-pressure compressors | 271 | reference_scaling | compressors_medium_low_pressure |
| High-capacity/pressure compressors | 272 | reference_scaling | compressors_high_capacity_pressure |
| Conveyors | 273 | reference_scaling | conveyors |
| Coolers/quenchers | 274 | direct_price | coolers_quenchers |
| Cooling towers | 275 | reference_scaling | cooling_towers |
| Crystallizers | 276 | reference_scaling | crystallizers |
| Dryers | 277 | reference_scaling | dryers |
| Ducts | 278 | direct_price | ducts |
| Dust collectors | 279 | graph_only | Not implemented |
| Evaporators | 280 | reference_scaling | evaporators |
| Fans | 281 | graph_only | Not implemented |
| Filters | 282 | reference_scaling | filters |
| Flares | 283 | reference_scaling | flares |
| Furnaces | 284 | reference_scaling | furnaces |
| Electric generators | 285 | reference_scaling | electric_generators |
| Shell-and-tube/double-pipe/air-cooled exchangers | 286 | reference_scaling | heat_exchangers_shell_tube |
| Spiral/plate-and-frame exchangers | 287 | direct_price | heat_exchangers_spiral_plate |
| Incinerators | 288 | reference_scaling | incinerators |
| Insulation | 289 | graph_only | Not implemented |
| Ion exchange | 290 | reference_scaling | ion_exchange |
| Hammer/jaw/gyratory/roll mills and crushers | 291 | graph_only | Not implemented |
| Ball/rod/pebble/jet/rubbish mills and shredders | 292 | reference_scaling | grinding_mills |
| Motors/drives | 293 | reference_scaling | motors_drives |
| Pipe/pipelines | 294 | reference_scaling | pipe_pipelines |
| Roll/screw presses | 295 | graph_only | Not implemented |
| Centrifugal pumps | 296 | reference_scaling | pumps_centrifugal |
| Miscellaneous pumps | 297 | reference_scaling | pumps_miscellaneous |
| Pressure vessels | 298 | reference_scaling | pressure_vessels |
| Reactors | 299 | graph_only | Not implemented |
| Refrigeration | 300 | reference_scaling | refrigeration |
| Vibrating screens | 301 | reference_scaling | vibrating_screens |
| Size enlargement | 302 | reference_scaling | size_enlargement |
| Storage tanks | 303 | reference_scaling | storage_tanks |
| Small stainless tanks | 304 | reference_scaling | small_stainless_tanks |
| Thickeners/clarifiers | 305 | reference_scaling | thickeners_clarifiers |
| Vacuum equipment | 306 | reference_scaling | vacuum_equipment |

## Partial coverage and skipped variants

- **Activated-carbon adsorbers (p. 256):** Exact 10,000 lb carbon branch boundary remains unassigned and rejected; no smoothing or invented branch selection.

- **Agitators (p. 257):** Agitator reference-to-target scaling across exponent bands is blocked.
- **Blowers (p. 261):** Below-3-psi variable-exponent blower curve.
- **Chimneys/stacks (p. 266):** Short stacks: no numerical exponent.
- **Columns (p. 268):** Diameter/per-height column graph is not the weight-based cost method.
- **Coolers/quenchers (p. 274):** Cascade cooler and dilution-air-port graph-only variants.
- **Motors/drives (p. 293):** Large electric motors and variable-speed drives: no separately specified base-price exponent.
- **Pipe/pipelines (p. 294):** Bare pipe, slurry pipeline and submarine pipeline curves: no separately specified exponent. Fittings/valves are factors only.
- **Centrifugal pumps (p. 296):** Conventional and inline centrifugal pumps: exponent cells are blank.
- **Miscellaneous pumps (p. 297):** Sliding-vane curve: no distinct printed exponent. Chemical-injection flow unit unresolved: identical documented source basis required.
- **Pressure vessels (p. 298):** 250-psi volume and horizontal/vertical weight curves: no printed exponent.
- **Size enlargement (p. 302):** Screw extrusion and disk/drum granulation: factors only; no separate base-price method.

## Scope and unresolved basis

This completes the formula/exponent implementation and coverage inventory for **Garrett Appendix 1**, not every source or a production-ready CAPEX engine. Appendix 2 begins at printed page 309 and concerns whole-plant costs; it is excluded. Bibliography pages 307–308, installation/material/pressure-factor automation, graph digitization, current-price escalation, equipment sizing, and frontend integration are outside this increment. Turton and price-escalation placeholders remain unchanged. The earlier empty `pumps.py` scaffold remains unused; the two explicit pump modules contain the implementations.

Pipeline prices are installed price per foot, scaled against pipe diameter. They cannot be added directly as total equipment prices. Mills distinguish purchased and installed scopes. Gear pumps use flow; chemical injection retains unresolved source-flow units and requires the identical documented basis. Other pump products use raw gpm×psi, not a claimed horsepower equivalence. Vacuum-pump/ejector size is equivalent-air flow divided by absolute mmHg; condenser size is thousands of source-gpm water. Source gallon/ton definitions are not silently converted.

Applicable material/service/pressure/temperature/reduction-ratio constraints remain in each module and reference. All out-of-range calculations use boundary anchors and are labelled unvalidated extrapolations. No numerical uncertainty distribution or industrial calibration is implied.
