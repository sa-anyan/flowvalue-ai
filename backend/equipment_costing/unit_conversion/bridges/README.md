# User-input conversion and sizing bridges

This package connects extracted measurements to canonical model coordinates. It
reuses the shared dimensional converter and `engineering_sizing` equations. It
never calls an LLM, chooses numerical assumptions, changes observations or adds a
cost correlation.

- `service.py`: canonical model contracts, linked-source allowlist, recipe metadata,
  dimensional checks, preview result and audit trail.
- `liquid.py`: liquid flow, vessel hold-up, filter area, pump coordinate/shaft power,
  and explicit volume-loading mixing-power estimate.
- `gas.py`: actual gas flow from mass/molar flow and explicit state; dryer chamber
  hold-up. No default molecular weight, compressibility or residence time.
- `thermal.py`: heat-duty or confirmed same-side enthalpy-flow difference to area.
- `mechanical.py`: supplied cylinder geometry/thickness/material density plus
  supplied heads/auxiliary mass to weight. Not pressure-code mechanical design.

Use `describe(report, equipment_key, model_id)` for blank user-input fields and
available source-cell references; `evaluate(report, equipment_key, specification)`
for an auditable preview. The drawer calls assessment-scoped API routes. Only
measurements belonging to that equipment or linked streams are accepted. Unknown
source IDs, dimensions, models and unresolved model definitions are rejected.

Save `plan.equipment[].unit_conversion` with `enabled: true` after preview. The
existing Equipment calculator reevaluates that specification on every run; a
stored preview number is never the calculation input. Changing the model requires
review. Approved manual prices and quotes retain precedence. Without an enabled
specification the previous calculation path remains unchanged. Existing save,
revision and stage-freshness controls apply.

All assumptions are explicit user inputs in displayed SI units. Pure conversions
use the canonical unit definitions. Gallon/ton and pressure conventions remain
explicit. Pressure/temperature conversions are operating context, not design
ratings. Standard/actual gas conversion across unknown reference states remains
unsupported. Filter flux, U/LMTD, residence times, densities, pressure rise,
efficiencies and mixing power densities are not derived merely from unit labels.

A recipe being dimensionally compatible is not proof it is the correct sizing
method for a service. User source/phase/duty selection and engineering rationale
remain necessary. The package does not resolve aliases, validate complete process
balances, design a bioreactor, or create an electrolyser cost model.

## Automatic post-matching input ladder

`automatic.resolve` is called by the shared Equipment runner after matching and
scope expansion. It is independent of workbook filenames, sheet layouts and
project tags. Explicit user sizes, quotes, scope and conversion inputs retain
precedence. Highest comparable explicit equipment dimensions are selected only
when they convert to the model's actual sizing dimension; a linked stream's
largest flow or pressure is never treated as vessel size.

When inputs are absent and AI is enabled/unlocked, a bounded cached planner chooses
from already accepted candidate models and allowlisted equations. It proposes
editable screening assumptions; Python validates units and computes the size.
`derivations.py` calculates same-stream molecular weight/density, temperature,
absolute pressure, pressure rise and arrangement-specific LMTD from cited source
IDs. Known same-stream quantities are preferred over estimated values. Derivation
bindings are reevaluated on subsequent runs, rather than reading saved result
numbers. Actual heat duty is obtained by the existing confirmed enthalpy-difference
route. No LLM arithmetic or generated code is executed.

The planner can explicitly permit provisional graph readings and propose a
justified extrapolation exponent. Neither bypasses the canonical costing model's
source/validity restrictions. Source gaps, missing correlations, invalid inputs,
provider failures and incomplete decisions remain per-equipment exceptions.

`input_resolution` records routing decisions and failures. The drawer displays
populated assumptions, derived-source references and editable values. Editing a
derived field detaches its binding and makes it an explicit user assumption.

Validation covers row/column tables, multi-sheet workbooks and repeated Nottingham
blocks, using controlled model responses and actual Python cost models. This
checks plumbing and numerical handoff, not arbitrary LLM judgement or universal
parser compatibility. Saved real-workbook checks are separately identified in
`outputs/automatic-input-validation`; no existing project baseline is overwritten.

Automatic mode permits provisional digitised-graph costs as disclosed screening
estimates, consistent with the requested rough-estimate workflow. Set
`equipment_input_policy.allow_provisional_graph_estimates=false` or an explicit
per-item `costing_options.allow_unverified=false` to retain the verification block.
It never converts unsupported graph/correlation structure into a supported model.
The graph permission is a deterministic policy, not an LLM confidence judgement.
Input repair is bounded to one additional pass; AI-generated extrapolation failures
can receive one further pricing-specific repair. User overrides are excluded.
See the saved validation report for actual outcomes and remaining gaps.

### Conversion-matching reasoning contract (version 3)

The LLM prompt explicitly requires, in order: (1) exact parameter/unit matching,
(2) context-sensitive semantic equivalence, (3) chemical-engineering relationships,
(4) equipment/stream/condition context, and (5) dimensional and basic engineering
plausibility review. Existing same-dimension measurements take precedence over
assumption-based sizing. A capacity label alone cannot equate storage volume with
throughput. Python still performs all arithmetic and checks recognized units,
positive physical quantities, fraction bounds, gauge/absolute pressure changes,
LMTD driving forces, source references and model dimensions.

Preview validation records observed chart range separately from model/design
validity. It explicitly reports `engineering_design_validated=false`. Canonical
costing retains its capacity/extrapolation restrictions. A standalone stream
enthalpy flow cannot be passed directly as motor power or equipment heat duty.
The prompt/schema contract and tests do not guarantee correct LLM judgement.

Version 4 forwards stream descriptions, source cells, phase descriptions and
explicit connection roles alongside numerical measurements. Model contracts list
required gallon/ton conventions. Candidate families marked ambiguous may receive
a provisional configuration/assumption proposal; incompatible component-only or
no-suitable-model decisions remain excluded. The original matching decision is
retained, so a provisional selection is not silently relabelled as a verified match.
