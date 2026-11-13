# P2 / G2 evidence matrix and execution handoff

Status: **pre-acceptance, not a G2 sign-off**. Prepared against Engineer 2 development baseline `9514494314fe84885363e812673e105b59f4e243`. Draft PRs below are separate branches, not integrated. Engineer 1 owns acceptance, integration order and numerical policy.

## Current test-only evidence

| Requirement | Existing evidence | Remaining acceptance work |
| --- | --- | --- |
| M2.1 canonical stream identity and source trace | PR #28: `backend/tests/test_p2_m21_stream_contract.py` | Three structurally different real M&E workbooks; one manually defined process; unit conflicts beyond normalized kg/h projection; original workbook byte comparison |
| M2.2 distinct physical assets and aliases | PR #21 B07, pending Engineer 1 review; PR #30 synthetic distinct keys with same T-104 display tag | Independent 10k + 5k = 15k costing parity, approved alias reconciliation, browser and XLSX export QA |
| M2.3 source and assumption register | PR #26: `backend/tests/test_p2_m23_provenance_contract.py` | Trace every critical engineering/commercial value from original workbook cell or explicit approved assumption to financial output; review locked assumptions |
| M2.4 dependency graph and recalculation | PR #27: `backend/tests/test_p2_m24_dependency_mutations.py`; PR #30: `backend/tests/test_p2_g2_preflight.py` | Execute actual sizing, CAPEX, OPEX, revenue and financial engines with independent expected values; verify no implicit run, stale outputs or approval overwrite |
| M2.5 migration/version compatibility | PR #31: `backend/tests/test_p2_m25_version_isolation.py`; B09 PR #10 test-only prototypes | Historical schema migration, failed migration rollback, recovery, legacy unknown labels, cloud transaction parity, receipt integration authorization |
| G2 exit: one approved engineering change propagates without duplicate assets, stale results or hidden assumptions | PR #30 synthetic preflight only | Full integrated execution and independent expected numerical result, approved assumption and source evidence, UI/export parity, Engineer 1 sign-off |

## Minimum integrated G2 fixture to execute

1. Establish **approved** baseline inputs and an expected-output ledger independently of the application's calculations. Include physical keys `physical:1` and `physical:2`, both displayed as `T-104`, and independently verified 10k + 5k = 15k only when the agreed numerical policy and fixture support those values. Do not manufacture costs.
2. Freeze the source workbook bytes and digest; capture source cell references, normalized units, operating schedule, source/assumption status, user approvals, equipment identity and all stage outputs.
3. Execute explicit Engineering → Equipment → CAPEX → Revenue → OPEX → Financial stages in the approved fixture. Record input/output hashes, stage status, totals, and each critical quantity's evidence reference. No implicit calculation on read.
4. Change one approved engineering quantity. Before rerun, assert affected stages are visibly stale, unaffected stages stay current, stored historical results remain unchanged and approved unrelated assumptions remain locked. OPEX can become stale when its optional CAPEX or Revenue basis changes.
5. Explicitly rerun affected stages in dependency order. Independently compare equipment counts and costs, CAPEX, Revenue, OPEX, annual ledger and NPV to precomputed expected values. Check no duplicate asset, missing-as-zero, hidden assumption or stale result is presented as current.
6. Reopen the original named version and a fork. Confirm original workbook bytes, baseline outputs, approvals and lineage remain unchanged. Exercise a failed migration with rollback/recovery and a historical project requiring conversion.
7. Repeat source/mutation tests against three structurally different workbooks and a manual process. Confirm conflicting units, missing properties and inconsistent operating schedules remain explicit and do not silently become zero.
8. Verify browser screens and JSON/CSV/XLSX exports reflect the same identities, numbers, source provenance, stale/partial labels and approval status. Save commands, CI logs, fixtures, output diffs and reviewer approval.

## Test execution commands

```bash
python -m pytest backend/tests/test_p2_m21_stream_contract.py -q
python -m pytest backend/tests/test_p2_m23_provenance_contract.py -q
python -m pytest backend/tests/test_p2_m24_dependency_mutations.py -q
python -m pytest backend/tests/test_p2_g2_preflight.py -q
python -m pytest backend/tests/test_p2_m25_version_isolation.py -q
python -m pytest backend -q --tb=short
```

**Important:** The five files live on distinct draft PR branches. They cannot be executed together on the unmodified development baseline until authorized integration or a temporary, isolated test-only combination. CI has verified them separately, not as one combined integrated suite.

## Blockers requiring Engineer 1

- Review/accept PR #21 and authorize merge order for PRs #3, #6, #9, #21, #26–#28, #30–#31.
- Approve the authoritative G2 numerical fixture and its expected values, workbook availability and reviewer.
- Explicitly authorize B09 production integration before adding live immutable receipt writes, changing freshness authority or touching cloud persistence.
- Confirm the migration policy and conversion evidence for historical saved projects.

## Non-goals until authorization

No production receipt activation, freshness authority changes, silent recalculation, altered numerical formulas, E1 branch edits, PR #21 changes, merges or deployment. CI-green test-only PRs are **not** P2 milestone acceptance.
