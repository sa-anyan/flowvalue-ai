# Equipment edits and deterministic recalculation

This correction preserves the existing extraction, matching and cost engines.
No LLM matching prompt, costing correlation or engineering default was changed.

## Faults confirmed

- The sizing drawer displayed `value.quantity ?? 1`, whereas the canonical
  equipment calculator already inferred two units for AB tags. It could display
  one while the purchasing line was actually extended for two.
- Saving equipment edits marked output stale by replacing its visible result
  with null. Existing pricing/sizing inputs remained in the saved plan, but the
  directory fell back to an unpriced engineering register. An interrupted or
  rejected rerun left that empty-looking state on screen.
- Conversion-field edits disabled the selected conversion equation; a later
  Python run could therefore miss the previous conversion path for that item.

## Current behaviour

Equipment PATCH requests upsert by equipment_key and recursively merge mappings.
Untouched records/fields remain. Explicit null clears a field; lists supplied
inside a record deliberately replace that list (e.g. removing one derivation
binding). Invalid record shapes and duplicate edit keys are rejected.

The Equipment runner records effective quantity and its convention in the saved
plan. The drawer can also display the effective result quantity for historical
plans without a stored quantity. Explicit user quantities take precedence.

Editing an already enabled conversion preserves that equation and the remaining
inputs. Changing to a separate explicit sizing pathway suspends the old conversion
without deleting it. All changed equations remain subject to Python validation.

Previous Equipment results stay visible as stale while edited inputs await
recalculation, and after a failed stage attempt. The UI labels that state. Old
hidden outputs can be recovered from the edit baseline or saved canonical cost
output. Freshness checks still block downstream use of stale Equipment results;
retaining visible old prices does not make them valid for new CAPEX.

Python-only execution does not rematch equipment or regenerate LLM assumptions.
Saved numerical assumptions, unit bases and source bindings are reused. Derived
quantities can be recalculated from their saved equations and source references.
New valid output replaces the stale display; invalid individual items remain
explicitly unpriced and do not erase unrelated saved assumptions.

## Verification

61 focused preservation, manual override, quantity, duplicate, isolated-stage,
automatic-input and conversion tests passed. Frontend production build passed.
Tests include a one-out-of-100 assumption patch, explicit clearing, stale-view
recovery, failed-rerun retention and forbidden-provider assertions.

On a separate Charlie clone, BL-201AB quantity 2 -> 3 retained 23 priced records;
only its extended cost changed, and every saved conversion input remained equal.
The browser then edited 3 -> 2 and saved/reran Python: 23 priced records remained,
BL-201AB showed 3871.46 for two units, saved conversion inputs stayed unchanged,
and the stage receipt recorded use_ai=false.

The older affected saved assessment was version-backed-up and recalculated with
Python only: its 21 prior prices and saved conversion inputs were preserved.
Private run details remain under ignored outputs/equipment-edit-preservation/.
These checks verify data preservation and calculation propagation, not industrial
accuracy of the underlying engineering assumptions or cost models.

## Immediate equipment sensitivity previews

Saving equipment edits now runs the canonical Python conversion/sizing/cost path
for changed equipment records only. It reuses saved assumptions, retains other
line results, and never invokes matching, an LLM, CAPEX, OPEX or finance.
The saved stage output/receipt remains the prior reconciled snapshot; the UI
marks totals and coverage stale until an explicit all-equipment run. Preview
lines carry `saved_edit_preview`. Missing/invalid inputs remain unpriced rather
than becoming fabricated costs. These previews are not fresh downstream inputs.
