# Canonical engineering sizing backbone

Unit conversion is in `equipment_costing/unit_conversion`. This package performs
engineering relationships, which require physical inputs and assumptions. It is
source-independent: Garrett and future cost methodologies use the same results.

## Allowlisted Python methods

| File / method | Relationship | Important basis |
|---|---|---|
| vessels.py / vessel_hold_up | V = Q × time / working fraction | Time is an explicit process/storage assumption unless supported by design data. M&E alone does not prove reaction residence time. |
| pumps.py / pump_duty | Flow × differential pressure; hydraulic/shaft power | Uses differential pressure, explicit liquid density if needed; US definitions come from the shared unit constants. Operating pressure is not pump head. |
| heat_exchangers.py / exchanger_area | A = abs(duty)/(U × LMTD × F) | Source duty or one-side enthalpy difference; sensible Cp/temperature assumptions only for sensible service, not evaporation. |
| filters.py / filter_area | A = volume flow / hydraulic loading | Preliminary loading assumption, not a universal cake/cycle/filter design. |
| gases.py / gas_volume | Q = mass/MW × R × T × Z/Pabs | Actual gas conditions; no automatic actual/standard-gas equivalence or liquid-density substitution. |
| dryers.py / dryer_chamber | Chamber hold-up = actual gas flow × residence seconds | Screening chamber size; evaporation, droplets and vendor performance may govern. |

`registry.py` exposes method IDs, required parameter names and canonical units.
`adapter.py` resolves source observations and explicit assumptions, reads source
conditions, validates units and evaluates the selected method. The LLM selects an
ID; it cannot supply executable Python, module paths or arbitrary expressions.

## Sizing ladder and assumptions

1. Existing direct dimensions remain usable. If a selected model lacks size, a
   unique source-supported equipment dimension of the required quantity is used.
2. Source flow/duty and connected stream observations feed the selected method.
3. Volumetric flow may derive from mass and an explicit density; gas pressure
   needs an absolute basis, including an explicit atmospheric assumption when
   converting a gauge observation.
4. AI proposes missing engineering parameters with value, units, rationale,
   source/assumption label and optional low/high bounds. These are not measured
   facts or literature research unless evidence actually supports them.
5. Python computes the size. Up to eight ranged assumptions form a conditional
   endpoint envelope; it is not a statistical confidence interval. The same cost
   engine calculates low/high cost endpoints where both are supported. Graph/model
   error and omitted scope are outside that envelope.
6. Invalid/missing assumptions remain per-equipment blockers and trigger bounded
   correction or opt-in research, rather than becoming zero cost or invalid unit
   multipliers. Existing assumption editors support deterministic recalculation.

## Matching, scope and research

`orchestration/pricing_status.py` keeps identification, candidates, selected model,
sizing, price status, scope decision and next action separately. `pricing_coverage`
reports priced/unpriced tag records and a review queue. Tag records are not a
certified equipment count. AB/duty/standby quantities must be justified; a proposed
alias is not priced twice and remains a scope-review item.

The equipment detail panel shows candidate/selected models, sizing assumptions,
conditional cost envelope and a research action. External research requires an
explicit checkbox authorisation, invokes the existing sourced-draft workflow and
does not automatically approve a quote or change the baseline. Dedicated model
gaps (e.g. electrolysis packages) remain explicit until suitable evidence exists.

## Specialist reliability

Specialists receive compact columnar canonical observations and concise prior
review decisions. Oversized cases split into equipment-linked regions. Successful
regions are cached separately, failures receive one bounded retry, and partial
coverage is recorded. Applicability (“active worksheet”) is separate from numerical
validation. If no active sheet is selected, a uniquely dominant explicit stream
register can define a provisional, flagged scope; ambiguous multi-sheet scopes are
not silently merged. Full source observations and specialist findings remain saved.

## Historical source correction

Garrett PDF printed p.277 / appendix PDF p.27 was visually inspected. Its fluid-bed/
spray volume axis is **actual ft3 divided by 10**. `source_corrections.json` records
that scale, PDF hash and two approximate spray-curve anchors. The imported workbook
is unchanged; effective models use actual volume. The spray curve is distinct from
the fluid-bed curve. Graph readings and prices remain provisional, not validated
supplier quotations. Centrifuge t/hr still requires an explicit ton interpretation;
unsupported below-range extrapolation still requires a justified exponent or a
researched comparable. No textbook coefficient is invented.

This is a preliminary sizing/economic workflow, not mechanical design, process
safety approval, validated kinetic modelling, a certified estimate or accreditation.
