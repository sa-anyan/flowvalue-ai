# UNIT-C01 — NumPy Boolean admission in native sizing inputs

Owner: Engineer 1. Priority: HIGH. Status: OPEN; discovered by FV-P1-UNIT-001. **No production correction authorised or applied in this acceptance ticket.**

## Confirmed observations

`equipment_costing.unit_conversion.convert` rejects Python/NumPy Booleans. However, `engineering_sizing.common.positive` checks only Python bool, then calls float(value). A NumPy bool_ therefore becomes0/1. The sizing adapter also converts non-heat observations with float() after checking only Python bool. SIZE-C02 protects the heat-duty value, not every other property or sizing assumption.

Thirteen unchanged-expectation negative tests in `backend/tests/test_unit_acceptance.py` fail:

- One explicit NumPy-Boolean assumption for each of12 methods is accepted instead of rejected.
- A NumPy True volumetric-flow observation reaches pump sizing as1 m³/h.

Examples: exchanger duty100 kW with U=NumPy True, LMTD20 K and F1 produces5000 m²; pump efficiency NumPy True is treated as1; dryer gas residence NumPy True is treated as1 second. For evaporated_water, NumPy False in the product-moisture fraction becomes0, which is a valid number but not a valid interpretation of a Boolean measurement.

Exact per-method assumption names and observed unsafe outputs are in `unit_conversion_acceptance_register.csv` TYPE-* rows. These are not accepted results or invented engineering estimates. The test assumptions are deliberately invalid types.

## Required correction scope for a separately authorised ticket

Reject Python and NumPy/equivalent Boolean representations before any abs/float coercion at shared sizing input/assumption and source-observation boundaries. Keep the canonical sizing library dependency-free. Preserve supported valid Decimal/Fraction/NumPy numerical behaviour at native functions, signed heat duties, zero where permitted and all existing equations. Do not broaden the stricter converter's numeric-type API merely to hide the distinction.

Use these13 assertions unchanged, the original304 native checks, C01/C02/C03 regressions and targeted converter tests. Add direct/shared-boundary coverage as needed. A value-based filter is inappropriate: real0/1 measurements must remain distinguishable from Booleans.

This is **separate from Engineer 2's XLS Boolean cell-type loss** and L/s ingestion gap. Fixing native guards cannot recover a Boolean already converted into an ordinary integer by the XLS reader. Preserve both ownership tracks and source evidence.


## Resolution addendum — 11 November 2026

UNIT-C01 is now resolved within the tested native sizing boundary scope. A shared dependency-free guard is applied before common float coercion, observation conversion, heat-duty magnitude and ranged-assumption comparisons. The original13 assertions pass unchanged, and targeted native/input-type regressions pass. See `../corrections/UNIT-C01_resolution.md` for completed regression results. The initial OPEN finding above is retained as historical evidence; Engineer2 XLS/L/s issues remain separate and open.
