# Founder-led equipment workflow

Implemented locally 2026-11-03. Preliminary engineering economics, not process/mechanical certification.

## Sequence

1. Retain canonical source stream/property records and source-backed equipment relationships. Identify service from all linked descriptions, including later waste/output mentions. A stream without a tag is not automatically a new asset or a proven plant boundary.
2. Retain existing priced selections. Send unresolved non-alias items to the chemical-engineering design specialist in bounded groups. The handoff carries process context, linked source observations, previous candidates and Python feedback.
3. The specialist chooses an allowlisted Python sizing method and proposes explicit assumptions with units, rationale, source and ranges. There is no generated executable Python, AI arithmetic substituted for formulas, or claim of external research.
4. Python calculates sizes, converts through the canonical unit converter and evaluates the existing Garrett models. One bounded correction pass addresses selected-model calculation failures, including justified preliminary out-of-range scaling. Failed regions remain visible and retry independently; validated responses are cached.
5. Every tag remains priced or explicitly unresolved. Alias proposals do not acquire a duplicate charge. Selected cost models, numerical assumptions, quantities and provisional chart/gallon choices are editable. Saving equipment edits locks that section; Python-only reruns preserve those edits.
6. Existing canonical equipment → CAPEX → operating economics → financial dependencies recalculate from the saved plan. Incomplete upstream inputs still prevent a claim of complete economics.

## New method

`backend/engineering_sizing/ion_exchange.py` implements an EBCT screening envelope:

- Resin bed volume = service volumetric rate × EBCT minutes / 60.
- Vessel envelope = bed volume / resin bed fraction.

The founder's worked example (10 m3/h, 15 min, 70%) gives 2.5 m3 bed and 3.5714 m3 vessel. These example values are independently tested and are **not inserted as Charlie's measured design**. Resin capacity, ionic loading, regeneration and freeboard remain separate design checks.

## Explicit Charlie basis

The founder defines AB as one operating unit plus a full-duty spare. This is saved as a project policy, not inferred universally from tag spelling. Each AB record has quantity 2 without halving per-unit capacity. Alias confirmation remains required. The target 100 kg/h is design intent, not a new workbook observation.

The comparison uses an explicit provisional digitised-chart permission and an editable US-gallon scenario, not a claim that all source charts specify US gallons. Graph reading errors, model/proxy omissions and extrapolation remain disclosed. The previous 9-priced scenario is preserved.

## Engineering-data views

The 2D/3D process map uses only actual registered equipment and unique recorded source/destination stream pairs. Ambiguous directions and untagged streams remain in the register. 3D tilt/OBJ boxes are schematic, not physical CAD, routing or a digital twin. Exports provide SVG and a schematic equipment-box OBJ.

The equipment drawer exposes sizing method, source stream, quantity/duty–standby rationale, numerical parameters, bounds, units and rationale. Save & Run Again uses Python without another AI request. Direct-size editing explicitly switches out of computed sizing.

## Charlie acceptance record

- Baseline: 409ddbe3543c498e99d48b18ac646586 — 9/32 tags priced.
- New scenario: 1cab46f380404928adce1514bfeb7326 — 19/32 tags priced, 13 conditional sizing-cost envelopes.
- Equipment records: 32 before and after. Pricing increased; the parser did not invent more units. Twelve AB records use the founder's duty/spare quantity convention.
- Thirteen records remain unpriced, including two aliases. Missing/ambiguous models and sizing scope remain explicit.
- CAPEX remains partial/provisional. Previously unresolved operating utility demands still block complete OPEX/revenue/finance acceptance; this equipment change does not claim to resolve them.
- Backend suite: 397 passed plus 367 subtests. Frontend production build/TypeScript passed.
- Browser: edited pump pressure 2 → 3 bar_delta in an independent test scenario; Save & Run Again changed price, retained override and locked equipment. Map has 32 nodes; selection and 3D toggle work; no page-width overflow at 390/768/1440 px. No external research invoked.

Private before/after snapshots, run scripts, screenshots, per-tag comparison and test output are in `outputs/charlie-founder-workflow/` (not public source evidence or industrial validation).
