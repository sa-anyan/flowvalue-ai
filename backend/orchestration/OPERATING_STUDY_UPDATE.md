# Coupled Garrett operating study — 31 October 2026

The existing equipment/CAPEX results now feed one saved operating-economics proposal. The connected LLM proposes Garrett factor selections, process-specific consumables, equipment energy assumptions, staffing, explicit product sales and financial policies. Deterministic Python calculates all annual quantities, costs, revenue and the existing canonical financial ledger. No legacy workbook formulas or numerical assumptions were imported.

## Canonical ownership

- `operating_advisor.py`: typed AI proposal, with rationale and uncertainty; no external market research.
- `operating_economics.py`: coupled annual OPEX/revenue calculation, shared schedule and deduction ownership.
- `backend/opex/consumption.py`: source-linked annual consumption and shared unit conversion.
- `backend/opex/energy_costs.py`: electrical, shaft, hydraulic, specific-energy, thermal-duty and power-density methods.
- `backend/financial_modelling/connectors/operating_economics.py`: construction, revenue and annual cash OPEX handoff into the existing financial engine.
- `backend/dashboard_reporting/study_report.py`: printable saved-result report; snapshot endpoint preserves the complete calculation and assumption state.

Garrett is the operating methodology. Detailed staffing or other itemization replaces a corresponding blanket factor. Revenue freight/packaging deductions cannot also be charged through the matching blanket operating factor. Sales-dependent expenses and a cost-plus price are solved algebraically, rather than with an uncontrolled circular iteration. Cost-plus is a required-price scenario, not evidence of a market price or buyer commitment.

## Sample run

The Nottingham workbook was reviewed previously using the connected LLM. This run reused that source register and capital result and made one live operating-model proposal. Its explicitly supplied scenario sells treated water from stream 13; biomass is not sold. The sample uses 314 days × 24 hours = 7,536 annual operating hours as an editable planning assumption, not a physical maximum. A two-year construction schedule and 20 operating years include a 50%, 80%, 100% ramp. Revenue and variable consumption are ramped once.

The saved case is named `Nottingham — complete Garrett TEA · 314-day scenario`. Its money basis remains USD, early 1987, consistent with the capital basis; no present-day escalation was implied. One settler remains excluded from equipment CAPEX due to missing sizing. The resulting negative NPV, negative IRR and unrecovered payback are calculated outcomes, not workflow failures.

## Verification and limits

245 backend tests passed, including independent quantity/energy checks, cost-plus coupling, source-linked sales, invalid assumptions, shared edits/save/reload, deduction ownership, report escaping and financial reconciliation. Frontend production build passed. Report and snapshot endpoints returned HTTP 200 through the frontend proxy.

This is a working preliminary workflow, not an industrially validated estimate. Unverified prices, staffing, duties, quality acceptance, product demand, capital exclusions and planning tax policy remain editable assumptions. No current market research or jurisdiction-specific tax verification was performed. Only supported, unambiguous workbook measurements enter deterministic source-based calculations; missing equipment duty may be explicitly estimated with a stated method. Some configurations still require clarification, and contradictory or dimensionally invalid inputs remain rejected. No new Excel export was added in this update.
