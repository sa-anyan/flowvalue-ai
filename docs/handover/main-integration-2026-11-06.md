# Main integration — 6 November 2026

Integrated histories, without force-pushing or replacing remote main:

- Equipment/costing checkpoint: `b1ad0d3`, also retained on
  `codex/checkpoint-before-main-merge-2026-11-06`.
- Colleague's revenue main tip: `fcb91ba` (dashboard, comparisons and MECE editing),
  including the revenue-only workflow/forms and metric-tonne/component basis fixes.

## Conflict resolutions

The colleague's `backend/revenue/` implementation and revenue dashboard/forms
remain the remote versions. Existing source-aware equipment costing/matching is
unchanged from the equipment checkpoint. Shared API/service conflicts retain both
revenue-only actions and isolated engineering/equipment stage execution.

The active `/revenue` route now uses the colleague's assessment workspace and
RevenueDashboard/RevenueDrawer. On a full project its calculate buttons call the
canonical Revenue stage rather than the legacy run-engineering endpoint. Dedicated
revenue-only uploads retain the colleague's bounded revenue-only workflow.

The colleague's metric-tonne/component quantity fix is also applied to the active
`backend/blocks/revenue/input_builder.py` adapter, since that calculation moved
out of the former orchestration module during stage isolation. Source-year price
views preserve revenue-only saved results and the current isolated-stage policy.
Unapproved historical financial numbers remain hidden; historical equipment
numbers do not become calculation inputs. Both sets of CSS/components are retained.

## Validation

- Combined revenue authority/forms/routing/price edits/refresh/workflow/quantity,
  connected/isolated stages, additional-model and OpenPyTEA tests: **996 passed**.
- Production frontend build/TypeScript/routes: passed.
- Colleague's revenue-series frontend tests: **4 passed**.
- Additional revenue/operating-economics and equipment/edit regressions: **85 passed**.
- Total selected backend tests: **1,081 passed**.

No paid AI call, source-workbook mutation, baseline replacement or force-push was
needed. Work that has not yet been committed/pushed on another developer's machine
cannot be included automatically; that developer should merge/pull the new main
while retaining their local work. The merge preserves the published histories.
