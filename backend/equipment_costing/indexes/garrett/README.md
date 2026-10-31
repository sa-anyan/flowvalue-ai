# Garrett — formula-bearing equipment methods

Source: Donald E. Garrett, *Chemical Engineering Economics* (1989), Appendix 1, supplied PDF `Chemical Engineering Economics - Appendix 1 - Equipment Cost Estimates (1).pdf`. Original chart basis: early 1987, CE Index 320. Source file identity is retained in `general.py` and in returned estimates. The corresponding original pages were rendered and visually checked locally; OCR text alone was not treated as authoritative.

## Selection and implementation

A printed size exponent counts as usable formula information **only when combined with a known comparable reference cost** and the general cost–size equation. This is not ten standalone equations that independently determine purchase prices. We have not invented graph intercepts, digitized graph prices, or established industrial accuracy.

| Order | Module | Printed page / PDF page | Implemented information |
|---|---|---|---|
| 1 | [activated_carbon_adsorbers.py](activated_carbon_adsorbers.py) | 256 / 6 | Two explicit historical purchase-cost equations |
| 2 | [agitators.py](agitators.py) | 257 / 7 | Turbine 0.23, 0.56, 0.68; propeller 0.42, 0.51, within printed power bands |
| 3 | [agitated_tanks.py](agitated_tanks.py) | 258 / 8 | Size exponent 0.53 |
| 4 | [air_conditioning.py](air_conditioning.py) | 259 / 9 | Size exponent 0.73 |
| 5 | [blenders.py](blenders.py) | 260 / 10 | 0.60 for ribbon/double-arm/sigma/twin-shell; 0.42 for double cone |
| 6 | [blowers.py](blowers.py) | 261 / 11 | 0.52 at 30 psi; 0.79 at 10 psi |
| 7 | [boilers.py](boilers.py) | 262 / 12 | 0.65 package boiler-hp; 0.77 package steam flow; 0.82 field erected |
| 8 | [waste_heat_boilers.py](waste_heat_boilers.py) | 263 / 13 | Size exponent 0.75 |
| 9 | [buildings.py](buildings.py) | 264 / 14 | Office building exponent **0.8**, a capital item rather than process equipment |
| 10 | [chimneys_stacks.py](chimneys_stacks.py) | 266 / 16 | Tall-stack exponent 1.63 |

Centrifuges (printed p. 265 / PDF p. 15) were skipped: installation/material factors are printed, but there is no numerical price equation or printed size exponent. They do not establish a base price. Short stacks and blowers below 3 psi are unsupported because their required exponents are not numerically specified. Alternative building-use/material/pressure/installation/module factors are deliberately not applied in this increment.

## General cost–size equation

[general.py](general.py) implements Garrett's printed p. 255 / PDF p. 5 relationship:

`C2 = C1 * (S2 / S1)**n`

- `C1`: known cost at reference size `S1`.
- `S2`: desired equipment size in the **same units**.
- `n`: the equipment/variant's printed exponent, not a universal 0.6 assumption.
- `C2`: size-adjusted estimate at the reference's original currency/date/index/configuration.

This is size scaling, not price inflation. A size exponent alone cannot determine the original purchase price. A comparable reference price must come from a documented source (for example, a reviewed quotation or an explicitly reviewed graph reading supplied separately). No reference price is bundled for the nine scaling-only modules.

## Explicit inputs and conservative limits

The small shared `ReferenceCost` type in `../models.py` requires equipment/variant, known amount and size, units, currency, index, period, price source, a caller-declared permitted scaling interval and explicit comparable-configuration confirmation. The price scope must match the method. These inputs do not themselves prove service suitability or supplier comparability.

The reference size must fit the caller-declared scaling interval and any printed source range. For a target outside the usable interval, the shared helper computes the nearest boundary cost and scales from that anchor, explicitly flagging extrapolation. Caller-declared limits are **not textbook-validated ranges**. Printed agitator band changes still require a reviewed piecewise method. Scaling across agitator exponent bands is rejected; a piecewise continuity assumption has not been implemented. Neither a chart's entire axis span nor a guessed minimum/maximum has been substituted for a reviewed applicability range.

Units are explicit and not automatically converted:

| Module | Canonical size unit | Variants |
|---|---|---|
| Agitators | `hp` | `turbine`, `propeller` |
| Agitated tanks | `US_gal` | `standard` (reference must match pressure/construction) |
| Air conditioning | `refrigeration_ton` | `standard` |
| Blenders | `ft3` | `ribbon`, `double_arm`, `sigma`, `twin_shell`, `double_cone` |
| Blowers | `cfm` | `30_psi`, `10_psi` |
| Boilers | `boiler_hp` or `lb_per_h_steam` | `package_hp`, `package_steam`, `field_erected` |
| Waste-heat boilers | `1000_scfm` | `standard` |
| Buildings | `ft2` | `office`, with `cost_scope="building_cost"` |
| Chimneys/stacks | `ft` | `tall` |

The boiler steam range is 6–600 × 10³ lb/h, represented as 6,000–600,000 lb/h. No boiler horsepower, refrigeration-ton or Btu conversion is derived from ambiguous/abbreviated footnotes. The building exponent was visually confirmed as 0.8; text extraction misread it as 0.5.

Adsorber input is actual pounds of activated carbon, not thousands of pounds. The source prints `250 < Wc < 10000` and `10000 < Wc < 200000`; exact 10,000 lb is unassigned and is still rejected. At/beyond the outer limits, the corresponding equation is evaluated at the limiting 250 or 200,000 lb boundary solely to establish an extrapolation anchor. The default extrapolation exponent is the branch power (0.481 or 1.2), explicitly an assumption rather than a source-validated overall cost elasticity because the equations include additive intercepts. An explicit positive `extrapolation_exponent` override is supported. No formula smoothing or resolution of the internal branch discontinuity is assumed.

## Usage

```python
from backend.equipment_costing.indexes.garrett.activated_carbon_adsorbers import estimate_cost

result = estimate_cost(carbon_weight_lb=1000)
print(result.amount)  # about USD 45,706.52 at early-1987 CE Index 320
```

```python
from backend.equipment_costing.models import ReferenceCost
from backend.equipment_costing.indexes.garrett.agitated_tanks import estimate_cost

# Synthetic demonstration only: this is NOT a price extracted from the textbook.
reference = ReferenceCost(
    equipment="agitated_tanks",
    variant="standard",
    amount=100000,
    size=1000,
    size_unit="US_gal",
    currency="USD",
    cost_index=320,
    period="early 1987",
    source="Synthetic example, replace with documented reference",
    valid_size_range=(500, 2000),
    same_configuration_confirmed=True,
)
result = estimate_cost(target_size=2000, reference=reference)
# C2 = 100000 * (2000 / 1000)**0.53; still at the supplied reference's date/index.
```

## Verification and boundaries

Run from the repository root: `python3 -m unittest discover -s backend/tests -v`.

Eleven automated tests cover both explicit adsorber equations against independent high-precision Decimal evaluations, all nine scaling modules, subtype/power bands, unit and source requirements, unchanged currency/index, explicit boundaries, unsupported variants and invalid/non-finite inputs. They establish transcription/arithmetic/validation behaviour, not industrial cost accuracy. These estimates remain preliminary and require independent applicability review. There is no frontend, CAPEX summation, index escalation, uncertainty distribution, restored legacy calculation or new dependency in this increment. Other existing placeholders remain empty.

## Boundary-anchored extrapolation

Founder-requested extension: for a target larger than the upper usable bound, evaluate a boundary anchor cost and use `C_target = C_anchor * (S_target / S_anchor)**n`. For targets below the lower bound, use the lower anchor. The source equation is never evaluated directly at an out-of-range target.

For adsorbers above 200,000 lb: `C_anchor = 76200 + 0.422 * 200000**1.2`, followed by the scaling equation. At 400,000 lb the ratio is 2. The default `n=1.2` is a disclosed extrapolation assumption inferred from the branch power; it is not independently calibrated outside the source range. The returned `exponent_basis` states this explicitly.

For the nine reference-price methods, compute the boundary cost from the documented reference and printed exponent, then scale from that boundary. For a single unchanged exponent this is mathematically equivalent to reference-to-target scaling; the intermediate anchor makes the extrapolation traceable. The usable interval is the intersection of the caller-declared reference interval and any explicit source range. Invalid reference inputs, incompatible units/configurations, unknown/variable exponents and unsupported agitator band crossings remain errors.

Returned results include `extrapolated`, `anchor_size`, `anchor_cost`, `exponent` and `exponent_basis`; extrapolation notes explicitly state that accuracy is unvalidated. Extrapolation does not perform engineering sizing, prove feasibility, quantify uncertainty, change materials or escalate the price date. Original period/index/currency remain unchanged. The historical 10,000 lb adsorber branch gap remains unresolved rather than being disguised as an outer-bound extrapolation.

## Next ten entries

The following ten chart groups continue after chimneys/stacks. Column trays (printed 269 / PDF 19) are skipped because correction factors and graphs do not establish a base-price equation. These are not ten standalone absolute-price equations: nine methods require a documented comparable reference price; coolers/quenchers provide explicit price equations.

| Module | Printed / PDF page | Printed formula information |
|---|---|---|
| `classifiers.py` | 267 / 17 | Rake and spiral: n=1.32 |
| `columns.py` | 268 / 18 | Weight basis: n=0.78; 100,000–1,000,000 lb |
| `column_packing.py` | 270 / 20 | Variant exponents −1.16, −0.64, −0.95, −0.4 and −0.5 |
| `compressors_medium_low_pressure.py` | 271 / 21 | Straight lobe 0.51; sliding vane 0.79; helical screw 0.87; reciprocating air 0.34 |
| `compressors_high_capacity_pressure.py` | 272 / 22 | Centrifugal and reciprocating: 0.80 |
| `conveyors.py` | 273 / 23 | Screw 0.78; belt 0.76; bucket/roll 0.5; pneumatic 0.37; vibrating 1 |
| `coolers_quenchers.py` | 274 / 24 | Spray chamber C=358Q+65,000; quencher C=335Q+12,200 |
| `cooling_towers.py` | 275 / 25 | n=0.79 |
| `crystallizers.py` | 276 / 26 | Cooling/evaporative 0.68; growth/forced circulation/DTB 0.63; vapor recompression 0.75 |
| `dryers.py` | 277 / 27 | Rotary 0.45; fluid bed 0.48; spray 0.29 |

Packing returns **price per cubic foot of packing**, scaled by nominal packing-piece size in inches. It is not a total equipment cost and must not be summed directly into CAPEX. Its negative exponents are intentional. The explicit cost scope `packing_unit_price_per_ft3` prevents substitution of a total purchase-cost reference.

Classifier/crystallizer flow uses `source_ton_per_h`: the source ton definition remains unresolved. Medium/low-pressure compressor flow uses `scf_per_min`; high-capacity compressor input is horsepower. Conveyors use length in feet with unchanged cross-section/configuration. Cooling towers use thousands of gpm. Rotary dryers use peripheral area in square feet; fluid-bed/spray dryers use actual cubic-foot volume. The graph's volume-divided-by-ten plotting convention is not applied to volume inputs; the constant cancels in a size ratio.

Cooler/quencher Q is thousands of inlet cfm, with no automatic standard/actual flow conversion. Their direct prices retain early-1987 USD / CE Index 320. A caller-reviewed flow interval is mandatory because no explicit validity interval is supplied alongside these equations. Above/below it, the equation is evaluated at the upper/lower boundary and the general scaling equation is applied. Default n=1 is a disclosed linear-term extrapolation assumption, not the exact elasticity of an equation with an intercept; callers can supply another positive exponent. Cascade coolers and dilution-air-port graph-only variants remain unsupported.

All nine new reference methods use the same boundary-anchored extrapolation and source metadata as the earlier methods. No material, pressure, thermal-duty or installation adjustment is inferred. Nineteen automated tests now cover the first and next ten groups, including both boundary directions, variant exponents, unit-price scope, explicit equations, invalid inputs and unchanged reference date/index. Passing these tests demonstrates code arithmetic and transcription checks, not industrial validation.

## Third ten entries (21–30)

Source pages were rendered and visually checked. Dust collectors (279 / PDF 29), fans (281 / PDF 31), and insulation (289 / PDF 39) are skipped: they provide graphs and/or adjustment factors without a usable base-price equation or numerical size exponent. They are not implemented by assuming a universal exponent.

| Module | Printed / PDF page | Formula information and size basis |
|---|---|---|
| `ducts.py` | 278 / 28 | Price/ft: mild steel −2.22+1.66D; stainless −6.43+5.84D; water cooled 79+6.78D. D in inches; printed n=1.08 |
| `evaporators.py` | 280 / 30 | Forced circulation n=0.70; falling film / long tube / short tube n=0.53; area in ft² |
| `filters.py` | 282 / 32 | Rotary vacuum drum/leaf n=0.39; table/tilting pan/belt n=0.50; pressure leaf/plate-and-frame n=0.61; filter area in ft² |
| `flares.py` | 283 / 33 | Elevated n=0.59; ground n=0.39; waste gas lb/h |
| `furnaces.py` | 284 / 34 | Hershoff n=0.48; box n=0.70; cylindrical n=0.78; transferred heat in million Btu/h |
| `electric_generators.py` | 285 / 35 | Diesel drive n=0.71; turbine drive n=0.76; generating capacity in kW |
| `heat_exchangers_shell_tube.py` | 286 / 36 | Shell-and-tube/double-pipe n=0.68; air-cooled n=0.39; actual outside area in ft² |
| `heat_exchangers_spiral_plate.py` | 287 / 37 | Spiral plate C=660A^0.59; plate-and-frame C=100A^0.78; actual area A in ft² |
| `incinerators.py` | 288 / 38 | Rotary kiln n=0.48; hearth n=0.64; catalytic n=0.75; direct flame n=0.39; heat input in million Btu/h |
| `ion_exchange.py` | 290 / 40 | n=0.97; water treated in source-basis gpm, 465 ppm removed |

Eight modules require documented comparable reference prices. The two direct-equation modules retain historical early-1987 USD, CE Index 320. No modern prices, installation factors, material factors, pressure factors, concentration corrections or equipment sizing are introduced.

Duct equations yield **unit price per foot**, scope `duct_unit_price_per_ft`, on a 1/8-inch wall basis. Total length is deliberately not assumed. The caller must supply `valid_diameter_range`; both endpoints must yield positive prices. A small target outside that interval is estimated from its lower anchor, rather than evaluating the affine equation at a nonphysical diameter. Extrapolation uses the printed 1.08 exponent; extension beyond reviewed bounds remains unvalidated.

Spiral/plate exchanger equations yield total purchase price, on a 304 stainless / no-insulation basis. Callers supply `valid_area_range`. Direct equations are in dollars: the graph's thousands-of-dollars axis is not an extra multiplier. Their power exponents are used for boundary extrapolation. No source validity interval has been fabricated from chart axes.

Shell-and-tube and double-pipe graph coordinates use different area multipliers. Reference scaling takes actual ft² for both; constant plot multipliers cancel in size ratios. Furnace transferred heat and incinerator heat input remain separate units. Gpm is kept on the source/reference gallon basis rather than silently converted to SI.

All 26 test methods pass, including variant subcases, independent Decimal equation/scaling checks, upper/lower anchors, source lineage, price scopes, preserved reference dates/indices, nonpositive duct anchors and invalid inputs. Review artifacts and the test log are retained locally under `outputs/garrett-third-ten-review/` (ignored by Git). These checks establish implementation behaviour, not industrial accuracy.

## Appendix 1 implementation complete — final inventory

See [COVERAGE.md](COVERAGE.md) for all 51 chart groups and explicit exclusions; [catalogue.json](catalogue.json) provides the same category/page/module inventory in structured form. This is completeness of the supplied Appendix 1 inventory and formula/exponent implementation, not completeness of every graph-only costing method or the overall CAPEX product.

The final 13 modules cover grinding mills, motors/drives, pipelines, centrifugal pumps, miscellaneous pumps, pressure vessels, refrigeration, vibrating screens, size enlargement, storage tanks, small stainless tanks, thickeners/clarifiers, and vacuum equipment. Each retains a separate module, scope and explicit variant/unit selection. All require documented comparable prices. Installed mill pricing cannot accept a purchase-price reference; pipeline per-foot installed prices cannot accept total purchase-cost references. Conventional/inline centrifugal pumps, high-pressure/weight-based vessel curves and other unsupported variants fail rather than borrowing an exponent.

New graph-only groups are hammer/jaw/gyratory/roll mills/crushers (291), roll/screw presses (295), and reactors (299). Together with the earlier five, eight chart groups remain unpriced. Their metadata remains visible in the catalogue; no formula is fabricated and no graph-only calculator is registered.

Source-basis units must be respected, especially miscellaneous-pump flow coordinates, vacuum absolute pressure, source gallons/tons and per-foot pipeline prices. See module notes and coverage limitations. No new package dependency, frontend, inflation engine or graph digitization was added. The 31 automated test methods pass, with multiple variant/boundary/invalid-input subcases and catalogue reconciliation over every page 256–306. Final review images and test log are retained locally in `outputs/garrett-final-review/` (ignored by Git).

## Provisional workbook integration (30 October 2026)

The shared registry now includes graph-based estimates alongside these formula methods. See [INTEGRATION.md](INTEGRATION.md) for usage, all 154 configurations, scoped factors, source traceability, index adjustment and blocked cases. Earlier formula-only coverage counts remain historical; they do not describe the new provisional graph-fitting path.
