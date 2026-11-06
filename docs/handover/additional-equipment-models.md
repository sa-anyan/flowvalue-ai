# Additional published equipment cost models

Implemented 6 November 2026 in the canonical costing engine. No new dependency,
parallel financial engine, workbook-specific values or Garrett correlation changes.

## Models and source verification

| Model ID | Required per-unit size | Native scope/year | Equation |
|---|---|---|---|
| `epa_ph_adjustment_1989` | US million gallons/day | Unit capital, USD1989 | `exp(11.721 + .543 ln Q + .000139 (ln Q)^2)` |
| `fermenter_reactor_turton_2001` | design volume, m³ | Purchased cost, USD2001 | `10^(4.1052 + .532 log10 V - .0005 (log10 V)^2)` |
| `watertap_circular_clarifier_2011` | surface area, ft² | Native construction polynomial, USD2011 | `-.0006 A² + 98.952 A + 191806` |
| `watertap_rectangular_clarifier_2011` | surface area, ft² | Native construction polynomial, USD2011 | `-.0029 A² + 169.19 A + 94365` |

EPA: [EPA-821-R-95-002](https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=200031RR.TXT),
Eq3-16 and Table3-22, printed pp3-30–3-32. Includes tank, agitator, acid-feed
system and installation/piping/control/engineering/contingency allowances.
Five-minute detention is the source design basis, not a measurement from a user
workbook. Table flows 0.00001–5 US MGD bound our conservative evaluation domain;
this is a tabulated interval, not a certified applicability range. Upstream rapid
mixing, clarification and chemical OPEX are separate. Included auxiliaries must be
reviewed against separately registered units; no inferred physical relationships
or silent deletions are made.

Turton coefficients/range were checked against the published
[OpenPyTEA documentation/dataset](https://openpytea.readthedocs.io/en/latest/user_guide/cost_correlations.html).
The metadata directory pins the downloaded dataset hash and exact parameter row.
This is dataset verification, not a visual verification of the textbook page.
Carbon steel, ambient pressure; 0.1–35m³ per vessel. Auxiliary scope is not fully
itemised in that dataset. Fungal/sterile/pressurised service is not automatically
validated by choosing the model. Both boundaries are enforced. No extrapolation,
clamping or automatic vessel multiplication to bypass the limit.

[WaterTAP 1.8.0](https://watertap.readthedocs.io/en/1.8.0/technical_reference/costing/clarifier.html)
references Sharma, Najafi and Qasim (2013), DOI10.1061/(ASCE)IS.1943-555X.0000155.
Native polynomials were verified against the versioned documentation/source.
WaterTAP's separate TIC factor and built-in currency escalation are NOT imported.
Published size limits could not be verified from accessible sources. These models
require explicit `allow_unverified=True` and remain provisional. Positive area,
positive cost and positive polynomial derivative are guards, not validated ranges.
Simple settling vessels are not automatically equivalent to mechanical clarifiers.

## Canonical handoff

- Registry/source routing exposes all four models to existing conceptual matching
  and input resolution. Names/aliases and function take precedence over tags.
  `P-001` alone is never proof of a pump. Qualitative conceptual support and required
  inputs are retained; no calibrated probability is invented.
- Existing deterministic unit engine now includes explicit `US_MGD`; ambiguous
  gallons are not assumed US gallons. Existing density, gas and pressure routines
  remain shared, including explicit atmosphere for gauge/absolute changes.
- `liquid_flow` converts mass flow using an explicit/derived density.
  `clarifier_area` delegates existing hydraulic-loading arithmetic: Q/overflow rate.
  `vessel_volume` delegates existing Q × residence / working-fraction arithmetic.
  Fermenter flow-derived volume requires `operating_mode=continuous`; batch/unknown
  requires documented vessel volume or future supported batch sizing. Flow is not
  itself a reactor capacity. Existing source IDs, cells and assumption provenance
  remain attached. No density/residence/loading is silently defaulted.
- Scope-aware totals keep unit capital separate from purchased and installation
  subtotals. `UnitCapitalCost` enters a separate CAPEX bucket, excluded from
  purchased/direct factorial bases and added once to direct/plant capital after
  factorial calculations. Startup and working capital retain their separate bases.
  Duplicate purchased/capital tags and mixed monetary bases are rejected. Whole-
  project TOTAL_CAPITAL without decomposition is not accepted as unit capital.
- Existing equipment drawer shows scope, native cost/year, source/range and
  escalation notice. Conversion assumptions and operating mode can be saved and
  recalculated through the existing Python edit path. Clarifier acceptance is explicit.
- LLM interprets/selects/proposes; Python validates/converts/sizes/costs/escalates.
  Live AI behaviour is not proven by the deterministic selection tests.

## Escalation

Model metadata carries 1989/2001/2011, never inferred from tags. No new CEPCI values
are invented. Existing pinned CPI proxy observations were extended with official
[BLS historical annual CPI](https://www.bls.gov/cpi/tables/historical-cpi-u-201708.pdf)
1989=124.0, 2001=177.1, 2011=224.939. Existing default target is **2026-09**, not a
2026 annual average. Proxy use requires the existing explicit policy consent and
is labelled general consumer inflation, not an equipment-price validation.

For a sourced equipment index, policy can provide
`source_index_overrides[method_id][source_year] = {series, value, source}` and the
same named series must contain a sourced target observation in the index catalogue.
Native same-series adjustment takes priority. Missing data produces an explicit
requirement. No implicit FX. Historical results/audit remain unchanged; replaying
an already translated result does not escalate twice. Other target years require
explicit observations.

## Verification and limitations

The exact `Mass Balance Team 8(6).xlsm` fixture was not found. No claim of running
that original workbook is made. Reference flows were used only in labelled synthetic
observations with explicit density, residence/working-fraction or overflow inputs.
They are not validated engineering designs. Deterministic tests cover source
arithmetic independently using Decimal, units, invalid inputs/ranges, quantities,
registry/matching hints, scope, escalation, CAPEX and the existing 20-year ledger.
The end-to-end test invokes real canonical stages with AI disabled and asserts
numerical reconciliation. No paid AI requests or response cache are needed.

Actual live model-selection quality, clarifier published validity range,
project-specific materials/sterility and auxiliary completeness still require
engineering review. A CPI-adjusted estimate is provisional, not a supplier price.

## Primary changed areas

- `backend/equipment_costing/indexes/additional_models/`: equations, metadata and licences.
- Canonical registry, unit aliases, conversion bridges and matching catalogue.
- Existing cost translation catalogue and explicit source-index override support.
- Equipment aggregation/status and CAPEX scope-aware connectors/contracts.
- Existing equipment drawer/assumption editor and shared card mapper.
- `backend/tests/test_additional_models.py`: focused and connected regression tests.

## Recorded verification results

- 219 selected backend tests passed (new models, automatic input resolution, units,
  Garrett regression, CAPEX, escalation, matching, stage connections/isolation and finance).
- `npm run build` passed compilation, TypeScript and all routes.
- Local backend health, frontend catalogue proxy and equipment page returned HTTP200.
- Catalogue proxy exposes all four new configurations. No paid AI calls were made.
- Browser interaction/visual inspection and original Team8(6) workbook regression
  were not performed for this build.
