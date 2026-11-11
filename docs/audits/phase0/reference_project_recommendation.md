# Initial reference project

**PROPOSED — REQUIRES ENGINEER AGREEMENT**

Recommend a small wastewater-treatment study as the first engineering reference, using a permission-cleared Team8 M&E workbook plus an independently prepared numerical reference pack. Begin with the four tracked synthetic equipment-input workbooks for deterministic parser regression; they are suitable test fixtures, not an industrial reference.

| Candidate | Availability/evidence | Strength | Missing gate |
|---|---|---|---|
| `backend/tests/fixtures/equipment_inputs/{row_table,column_table,multiple_sheets,repeated_nottingham}.xlsx` | Tracked with fixture README | Reproducible layout/orientation/source-cell tests, safe synthetic data | No independently validated plant, operating prices or industrial outcome |
| Team8 wastewater study | Mentioned in development history; no complete permission-cleared committed reference pack confirmed | Compact diverse process, service fee plus clean-water sale can test two legitimate mechanisms | Original M&E/design, independent balance/sizing/cost sources, permissions, current commercial/site inputs, and approved yearly ledger |
| Charlie protein-from-air | Private legacy filenames and optional tests exist; real-workbook/snapshot tests skipped | More diverse equipment, utilities and multi-year economics | Missing distributable files, acknowledged human-study uncertainty, scope and commercial data; no use of legacy workbook prices/formulas as independent truth |

This audit did not open confidential OneDrive files or embed their contents. The canonical product specification/roadmap prohibits importing legacy workbook formulas/coefficients/results as implementation or validation sources. Use those studies for workflow/provenance review only unless the owners explicitly resolve any source-policy conflict. No automatic reference-project approval is implied by previous successful demonstration runs.

## Required agreed reference pack

1. Source workbook, version/hash, owner permission and confidentiality classification.
2. Independent stream balance and cell-level truth set, equipment identities/quantity/aliases.
3. Hand-reviewed sizing equations, design assumptions and applicability envelopes.
4. Licensed source cost references and historical/year/currency/installation bases; electrolyser/vendor gaps remain explicit.
5. Documented operating hours/ramp, raw materials, utility tariffs, staffing and waste expenses.
6. Explicit user-approved revenue mechanisms, stream rate/price/billing units and evidence.
7. Independent annual CAPEX/OPEX/revenue/tax/WC/cash-flow ledger and NPV/IRR/payback checks with tolerance.
8. Baseline, edit, reversal and export reconciliation plus review signatures from both engineers.

Industrial validation remains a later P9 activity; a university study or a passed software test does not establish industrial validation.
