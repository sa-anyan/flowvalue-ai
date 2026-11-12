# G4 gate review pack — 12 November 2026

**Prepared by:** Engineer 1 · **For:** an independent reviewer, Engineer 2 and the founder · **Code basis:** branch `e1/p4-audit` (PR #29, stacked on #25) · **Authority:** official roadmap rev 1.1, Phase 4

## Exit gate

> **G4:** FlowValue can produce a complete, reproducible multi-year financial model for a supported reference project, with commercial assumptions and financial calculations fully traceable.

## Decision

**G4: READY FOR INDEPENDENT REVIEW. Engineer 1 recommends PASS within G4's scope.** Every Phase 4 milestone, acceptance criterion and roadmap test passes. A private reference study has been run end to end, and it is complete, reproducible and reconciled.

**Not passed yet:** the gate needs an independent reviewer and the sign-offs below.

**Scope caveat:** G4 is about completeness, reproducibility and traceability, not accuracy. The reference model's capital cost carries G3's open items: G3 is not yet passed, the OpenPyTEA sources are unchecked, and escalation uses a CPI proxy. Its discount and tax rates are labelled planning defaults, not reviewed values.

**Reproduce:**

```bash
python docs/verification/phase4/g4_review/reproduce_g4.py [--study DB --assessment KEY]
```

The script runs the G4 test groups. Given a study, it re-runs every stage twice without AI on a temporary copy, compares the output fingerprints, and builds the financial workbook. It prints statuses and counts only.

## 1. Milestones

| Milestone | Status | Evidence |
|---|---|---|
| M4.1 Source-linked fixed and variable OPEX ledger | **PASS** | Each line records quantity, rate, units, fixed or variable, scope, source, rationale, uncertainty and price basis. **New:** `payment_owner` (project, customer or third party; default project) and `escalation_basis` on every user line. A cost paid by others needs a basis, is listed under `paid_by_others`, and never enters project OPEX. A category paid entirely by others becomes an explicit zero. Annual timing comes from the cash-flow schedule |
| M4.2 Revenue Box authority and payment validation | **PASS** | No revenue without Revenue Box authority or an approved edit; unique payment IDs; unit checks; unknown values never become zero; shared-stream and avoided-cost reviews |
| M4.3 Multi-year operating and contract schedules | **PASS** | Explicit annual schedules, plus `contract_term` with renewals. The calendar mapping is a tracked revenue input when terms exist |
| M4.4 Avoided-cost accounting and double-counting controls | **PASS** | One target OPEX line per saving; over-reduction and repeat application are rejected; a required overlap review when revenue exists |
| M4.5 Integrated financial calculation engine | **PASS** | One annual ledger from CAPEX, OPEX and revenue: project and equity cash flows, tax with losses, debt, depreciation, working capital, NPV, IRR, MIRR, payback, profitability index, DSCR, levelised cost and break-even. Undefined metrics are labelled `undefined`, never zero |
| M4.6 Reconciled financial workbook and reporting outputs | **PASS** | `GET /api/assessments/{key}/financial-workbook`. Sheets: Summary, Cash flow, Revenue, OPEX, OPEX lines (with payment owner and escalation basis), Reconciliation, Assumptions, Sources. Decimal reconciliation plus a read-back check of every number. Also: the HTML TEA report and the JSON model |

## 2. Acceptance criteria

| Criterion | Status | Test |
|---|---|---|
| No revenue source without Revenue Box authority or an approved user edit | PASS | `test_revenue_authority.py` |
| Every commercial payment is uniquely identified | PASS | `test_phase4_acceptance.py`, `test_revenue_mece.py` |
| Payments on the same physical stream reviewed for double counting | PASS | `test_payments_sharing_a_stream_need_a_double_count_review`, `test_revenue_preflight.py` |
| Contracts do not extend beyond supported dates without an explicit assumption | PASS for lines with a `contract_term` | `test_contract_expiry_2027_blocks_unsupported_2028_payment`, `test_renewal_2028_needs_an_explicit_basis_and_is_labelled`. A line without a term treats each listed year as an explicit annual assumption |
| Avoided costs not both OPEX savings and independent revenue | PASS (required review) | `test_avoided_cost_beside_revenue_needs_an_overlap_review`, `test_savings_only_reduces_target_not_revenue` |
| Python, exports and dashboard reconcile within tolerances | PASS | `test_financial_workbook.py`: relative tolerance 1e-9 and full read-back. The dashboard and report read the same saved result |

## 3. Roadmap testing list

| Roadmap test | Result |
|---|---|
| Wastewater fixture: treatment fee, capacity reservation, pipeline usage, certificates, licensing and avoided treatment cost distinguished | PASS (synthetic figures) |
| More treated volume changes volume revenue but not the fixed capacity reservation | PASS; the finance ledger matches every year |
| Contract expiry 2027 and renewal 2028 | PASS |
| Partial-year operation and zero production | PASS |
| Unsold products | PASS (existing test) |
| Conflicting billing units | PASS |

## 4. Reference project run (private study; counts only)

The founder's reference study was run on 12 November 2026. The founder supplied the Revenue Box and schedule. The AI proposed the OPEX assumptions; the founder reviewed them and raised the staffing. The study's values stay on the founder's machine.

| Check | Result |
|---|---|
| Stages | Equipment, CAPEX, revenue, OPEX and finance all ready; 0 finance issues |
| Revenue checked by hand | Exact for each year checked |
| Reproducible without AI | Yes: two full re-runs give identical output fingerprints for all five stages |
| Workbook | 46 of 46 reconciliation checks pass; 960 numbers read back with 0 mismatches |
| Metrics | 89 calculated; 31 labelled `undefined`. The 31 are per-unit metrics in the six periods with no production, and minimum DSCR with no debt |
| OPEX traceability | 23 of 23 user-entered lines record payment owner and escalation basis |
| Edits recalculate | A changed input marks downstream stages stale, and a re-run updates the metrics (checked on a copy) |

**Fixed during the run:** the revenue output stored unrelated configuration, so its fingerprint depended on run order (F1). It now stores revenue inputs only.

## 5. Open items (do not block G4's scope)

1. **UI.** `contract_term`, `shared_stream_review`, `revenue_overlap_review`, `payment_owner` and `escalation_basis` are editable through the structured editor, with no dedicated form controls yet.
2. **Escalation basis is recorded, not computed.** A line-specific escalation rate is not applied; escalation follows the study's financial policy.
3. **The running app server predates this branch.** Restart it after merging to expose the workbook and the Basis of Estimate.
4. **G3 dependency.** The reference model's CAPEX accuracy rests on G3's open items.

## 6. Sign-off

| Role | Name | Decision | Date |
|---|---|---|---|
| Engineer 1 | | Prepared; recommends PASS within G4's scope | 12 Nov 2026 |
| Engineer 2 | | | |
| Independent reviewer | | | |
| Founder | | | |
