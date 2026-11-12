# P6 M6.4 — Active interface audit and implementation boundary

**Status:** read-only architecture evidence; no implementation or acceptance claim. **Inspected ref:** `engineer-2/development` on 12 November 2026. **Owner:** Engineer 2.

## Confirmed live paths

| Area | Current implementation | M6.4 implication |
|---|---|---|
| Upload | `backend/api/app.py` `POST /api/assessments` accepts `.xlsx/.xls/.xlsm`, 20 MiB bound, creates assessment and source SHA-256; stage execution is explicit for non-revenue workflow | Upload is **not** a general simulator adapter or mapping acceptance endpoint |
| Extraction | `backend/blocks/engineering_data/runner.py` returns parsed report and source-cell inventory; optional AI source review via `backend/orchestration/workbook_review.py` | Source-backed review exists, but AI review is not equivalent to authorised mapping acceptance |
| Register editing | `PATCH /api/assessments/{key}/equipment-register` delegates to `backend/blocks/engineering_data/edits.py` | Explicit manual edits retain workbook observations, record inferred user evidence, version the prior state and refresh downstream stages; this is equipment-register editing, **not** a complete source-to-canonical mapping UI |
| Approval | `POST /api/assessments/{key}/engineering-approval` delegates to `backend/blocks/stage_workflow.py` | Approval requires current revision and fresh engineering_data, stores digest of engineering_data output and time; no separate mapping diff/individual mapping decision evidenced in this endpoint |
| Specialist review | `POST /api/assessments/{key}/review-decisions` accepts agree/challenge/defer for an existing specialist finding and records no engineering design/cost change | Do not treat this review record as source-mapping acceptance |
| Freshness | `backend/blocks/execution.py` fingerprints source hash, filename, process description and upstream receipts; `refresh` marks changed downstream stage views stale | Reuse P2 freshness rather than building parallel invalidation |
| Plan edits | `backend/orchestration/service.py` requires revision and rationale, marks results stale and records user override | Plan editing is distinct from mapping source engineering observations |

## Critical distinction

The existing engineering approval signs a digest of the **whole engineering_data stage output**. The M6.4 requirement to show **per-source observation → proposed canonical mapping → reviewed decision**, including conflicts and unmapped fields, is **not demonstrated by these API paths**. Do not infer the absence of all UI features from this backend audit; frontend component inventory and end-to-end browser verification remain open.

## Proposed smallest safe implementation sequence

1. **Read-only preview first.** Derive a serialisable mapping diff from the existing parsed `BalanceReport`, source cells and canonical report; do not mutate state, approve, run stages, or create equipment.
2. **Test contract.** Verify original vs normalized value/unit, source evidence IDs, unsupported/unmapped records, duplicate tags across scopes, missing/zero, conflicts and textual connection mentions.
3. **Approval binding.** Once approved by P2 owner, bind reviewed mapping decisions to source SHA-256, adapter version, canonical project revision, and engineering_data digest; enforce revision conflict handling. Do not retrofit this silently into current engineering approval.
4. **UI.** Preview before acceptance; render unresolved cases distinctly; never imply AI suggestions or source-supported measurements are verified plant facts.
5. **Acceptance.** Independent workbook/export fixtures and browser tests, then reviewer signoffs. No G6 pass before these.

## Gaps and constraints

- No verified general `/import-preview` or `/accept-mapping` endpoint from the inspected routes.
- No confirmed simulator-version-specific acceptance in the generic workbook upload.
- No demonstrated per-observation mapping acceptance receipt.
- Frontend preview/approval components and P2 migration/version contracts require further review.
- G2 formal acceptance remains open; integration audit PR #36 is not an approved merge base.
- The existing financial XLSX stale-label issue remains a separate integration finding; no P6 work should mask it.

## Evidence paths

- `backend/api/app.py`: assessment upload (~285–335), review decisions (~261–282), equipment edit (~72–79), engineering approval (~583–593).
- `backend/blocks/engineering_data/runner.py`: source extraction and review payload.
- `backend/blocks/engineering_data/edits.py`: `apply_edit` and `save_edit`.
- `backend/blocks/stage_workflow.py`: `approved` and `approve`.
- `backend/blocks/execution.py`: `_inputs`, `input_fingerprint`, `fresh`, `refresh`.
- `backend/orchestration/service.py`: `edit` stale/assumption logic.

**Next gate:** review frontend implementation and confirm approved G2 baseline before adding a production mapping endpoint.
