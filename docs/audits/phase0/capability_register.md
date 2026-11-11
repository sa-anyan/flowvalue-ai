# Capability register

Baseline `74f364d`, 10 November 2026. Categories follow the request; the available roadmap uses A–I, not P0–P9. “Implemented” describes executable code with identified tests, not industrial fitness. No implementation has been classified deprecated without an explicit deprecation record.

| ID | Capability | Status | Owner | Limitations |
|---|---|---|---|---|
|CAP-01|Excel ingestion and M&E registers|Partially implemented|Engineer 2|Cached formula values; bounded layouts, no universal compatibility|
|CAP-02|Other simulator/import dropdown methods|Unverified|Engineer 2|Current checkout is Excel-only upload endpoint; old backend/app parser scaffold paths in AGENTS absent|
|CAP-03|AI workbook review, equipment matching and input selection|Partially implemented|Engineer 2|Mocked providers; no live consistency/physical correctness study during audit|
|CAP-04|Canonical unit conversion|Implemented|Engineer 1|Finite allowlist; context required for ambiguous gallons/tons, pressure, gas basis; parser has separate normalizer|
|CAP-05|Preliminary sizing registry (12 methods)|Implemented|Engineer 1|Screening estimates, not detailed design; independent complete method validation pending|
|CAP-06|Equipment costing catalogue (594 rows)|Partially implemented|Engineer 1|Disabled/unverified rows included; cannot infer actual workbook pricing coverage|
|CAP-07|Equipment quantity, aliases, overrides and installation|Implemented|Engineer 1 / Engineer 2|Semantic aliases and package scope still require review; missing installation factors remain explicit|
|CAP-08|Escalation and shared FX|Implemented|Engineer 1|Pinned sources; consumer inflation proxy is not equipment-index validation|
|CAP-09|CAPEX three methods|Implemented|Engineer 1|Detailed/overall alternatives; entered factors/site completeness not industrially verified|
|CAP-10|OPEX categories, drivers and dependent factors|Implemented|Engineer 1|Prices/staffing/efficiency and applicability remain assumptions; known subtotal differs from complete total|
|CAP-11|Six-category Revenue Box and approval|Implemented|Engineer 1 / Engineer 2|CommercialLine has 15 dataclass fields; requested 13-field contract needs explicit mapping|
|CAP-12|Revenue rate assistant and research suggestions|Partially implemented|Engineer 2|Research is opt-in draft evidence, not guaranteed contracts or validated local prices|
|CAP-13|Annual financial ledger and metrics|Implemented|Engineer 1|Synthetic numeric cases; source-table transcription not independently source-checked; jurisdiction policies preliminary|
|CAP-14|Monte Carlo simulation|Partially implemented|Engineer 1 / Engineer 2|Shared deterministic pipeline, no per-iteration AI; uncertain input model completeness not solved by sampling|
|CAP-15|Scenario & sensitivity workspace|Planned|Engineer 2|Navigation/tab scaffold, not a complete interactive scenario study|
|CAP-16|Reports, dashboards and currency views|Partially implemented|Engineer 1 / Engineer 2|API/model tests/build; browser-to-export numerical reconciliation not audited|
|CAP-17|Versions, revisions, source lineage and stale stage detection|Implemented|Engineer 2|Synthetic SQLite checks only; no production database mutation or live cloud version restore|
|CAP-18|Cloud authentication and tenant isolation|Unverified|Engineer 2|Cloud authorization/RLS/backup/restore require separate permitted infrastructure audit|
|CAP-19|Industrial validation and accreditation|Planned|Shared P9|Documentation of intent is not validation evidence|

CSV carries exact source/test locations. Test names are discovery links, not proof every capability passed independently. See baseline_test_report.md for actual run outcomes. Numerical register rows include helpers and delegates; they must not be counted as independent physical models.
