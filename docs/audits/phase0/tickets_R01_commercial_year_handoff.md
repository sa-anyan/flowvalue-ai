# FV-G0-R01 — Reconcile Monte Carlo study horizon and authorised commercial years

Status: **OPEN — documentation ticket only; no repair implemented**. Severity High integration defect/test-contract discrepancy. Owners Engineer2 adapter/orchestration; Engineer1 calculation-contract approver. Phase P0 baseline repair, P2/P4 interfaces, P7 regression. No GitHub issue was created externally.

## Original and current evidence

Original `74f364d` full suite:1717 passed,1 failed,2 skipped,367 passing subtests. Exact failing test: `backend/tests/test_equipment_resolution.py::test_manual_price_monte_carlo_reconciles_same_canonical_run`, assertion at375 expects complete and receives partial. Targeted reconciliation rerun reproduced it unchanged.

`complete_state()` from `backend/tests/test_monte_carlo.py:30` calls the Revenue authority fixture; `backend/tests/test_operating_economics.py:131` specifies3 operating years. Its commercial line contains3 annual rows. The failing test creates `Settings(parameters=[p], seed=15)` without an explicit horizon. `backend/scenarios_and_uncertainty/monte_carlo/models.py:95` defaults operating_years to20. `scenarios.py:31–38` overwrites copied financial.operating_years with20 and deliberately does not extend shorter commercial schedules. `revenue/connectors/commercial.py:30–33` requires rows for all operating years and rejects the3-row schedule.

Consequences: equipment remains priced; revenue cannot complete; revenue-dependent administration, packaging/storage, R&D and royalties remain unresolved; finance waits. Thus the first confirmed boundary is **horizon selection/copy preparation**, not equipment units, equipment-model availability or failed arithmetic. The refusal to invent17 contract years is appropriate. This evidence does not establish whether the correct repair belongs in fixture construction, settings defaults, or caller preparation; investigate those contracts before selecting code changes.

## Engineer1 contract to approve

- Identical approved study horizon and commercial schedules must permit the existing completeness assertion and canonical metric reconciliation.
- An explicitly extended study with unsupported contract years must remain partial until separately authorised renewal/replacement/zero-income assumptions exist; no automatic contract extension.
- Operating-year and calendar-year conversion must be explicit; construction years are not operating revenue years.
- Source-bound approval, prices, quantities, billing periods and existing baseline inputs remain unchanged on scenario copies.
- Equipment/known expense cells remain visible when complete finance is pending; no implicit zero, no invented sale or renewal.

## Engineer2 investigation and proposed deliverable

Trace initial Settings, API/UI-supplied horizon, discovery defaults and prepare/evaluate round trips. Decide with Engineer1 whether this fixture intended a3-year run or a20-year authorised schedule. Repair the responsible adapter/default/fixture contract without changing costing/economic equations or weakening `complete` to `partial` in the existing success test. If the intended success fixture must explicitly set its already-approved horizon, document why that is fixture correctness; keep an additional extended-horizon negative test.

## Closure evidence

1. Existing exact failure passes with the agreed intended horizon and its complete assertion intact.
2. Separate3-year and fully authorised20-year studies reconcile against the existing deterministic pipeline.
3. A3-year contract in an explicit20-year study remains visibly unresolved, with no invented years.
4. Construction offsets, missing/zero, expiry/renewal, approved assumptions and copy immutability are tested.
5. Full clean backend suite records all passes/skips/failures; original failure history is retained.
6. E1 approves numeric/schedule expectations; E2 records adapter ownership and migration impact.

Do not implement this ticket during gate reconciliation. No prices, coefficients, source years, equations or assertions were modified.
