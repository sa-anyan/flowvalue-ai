# Independent financial sensitivity

The guided Financial scenario controls use the immutable FinancialInputs saved
with the last successful financial calculation. They do not save changes to the
assessment's operating plan or invoke CAPEX, Revenue, OPEX, or AI stages.

`backend/scenarios_and_uncertainty/financial_sensitivity.py` validates the six
existing controls (discount, tax, depreciation life, salvage, working-capital
recovery, and closure), copies the typed inputs, and invokes the existing
canonical Python financial engine. Capital amounts, operating cash costs,
revenue, and their source snapshots remain the original calculation's values.
A new financial baseline is required if none has ever been calculated.

The authenticated assessment sensitivity endpoint returns the original policy
and accepts overrides tied to its snapshot fingerprint. Each completed preview
is stored through the existing version interface with its own result, ledger,
inputs, and source snapshots; the original assessment and revision are untouched.
Cloud version writes retain caller ownership checks. No database migration or
external research is introduced.

The UI debounces changes, ignores aborted/superseded responses, and updates
scenario KPIs and financial charts from the returned ledger. Reset to original
clears local overrides and displays the original calculated inputs and results.
It does not write to the baseline or delete previous scenario versions. The
Results tab continues to show the original financial result. Equipment edits
still require explicitly opening a separate scenario copy.

Verification covers stale upstream receipts, all six controls, invalid values,
snapshot mismatch, separate version persistence, cloud ownership, baseline
identity, and the guided controls. Local browser verification also checks tax
and discount edits and resetting during an in-flight calculation.
