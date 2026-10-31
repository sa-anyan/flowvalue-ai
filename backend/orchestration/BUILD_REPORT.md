# Orchestration implementation and verification — 30 October 2026

## Delivered locally

- Safely recovered existing Excel parser; subprocess upload isolation and source-cell context.
- Bounded structured OpenAI engineering proposals, model/prompt tracking, persistent cache,
  explicit opt-in, source-reference validation, conservative source-backed numeric recovery.
- Canonical equipment → purchased subset CAPEX → Revenue → annual OPEX → financial ledger.
- Incomplete stage continuation; unpriced exclusions remain null, not zero; historical price basis gates.
- Value-level assumption register, section-level user locks, deterministic downstream reruns.
- Private SQLite source/input/result storage, named immutable versions, independent reopening and comparisons.
- Local Entry, Equipment, CAPEX, OPEX, Revenue and Financial Model pages; model/size controls,
  scalar and structured assumption editors, progress, evidence, results and version controls.

No existing costing, CAPEX, OPEX, revenue or financial calculation modules were changed.
New orchestration calls their canonical APIs. The original cloud app was not overwritten.

## Checks

- Backend: **226 tests pass**, including existing calculation tests and 12 orchestration checks.
- Full real-workbook chain: five worksheets, seven equipment tags and fourteen usable mass-flow
  records. Complete financial schedules use **explicit synthetic economics/design inputs**;
  six equipment items remain excluded in that integration case.
- Edits change dependent CAPEX/OPEX/financial outputs, baseline survives save/reopen, and
  deterministic Run Again makes no LLM request.
- Unknown models, fabricated stream references, replaced flows, malformed files, stale edits,
  provider outage, false AI self-verification, source-recovery conflicts and local request guards checked.
- Browser: uploaded the actual .xlsm, displayed seven tags, saved a named baseline, opened an
  independent copy, compared versions, edited a synthetic buffer-tank configuration, saved a
  locked override and reran Python. Numeric-text conversion bug found and fixed; the displayed
  provisional purchased cost then matched the canonical engine. This is not a plant cost validation.
- Next.js production build and TypeScript checks pass. Python lint passes for new orchestration/API/tests.
- No paid AI requests, external market research, cloud deployment or buyer contact during these checks.

Private artifacts: `outputs/orchestration-review/all-tests.txt`, `frontend-build.txt`,
`actual-workbook-synthetic-economics.json` and the local workspace screenshot.

## Remaining reliability / release limits

Live OpenAI proposal quality and account connectivity were **not tested**. Configure a server-side
key/model and explicitly request proposals to exercise that path. API availability is not
engineering validation. The AI can leave complex plans incomplete; required physical specifications
and product review must be supplied by the user. Automatic recovery is limited to explicitly labelled,
aligned existing stream blocks, not arbitrary sheet reconstruction or new connections.

External research is not implemented; supplied project/textbook evidence is used, unknown market
facts remain unknown. Assumption explanations may be inherited at section level; industrial review
must check individual choices. Digitised graphs retain existing unverified flags and discrepancies.
Economic outputs cover the disclosed priced subset, not an undisclosed complete plant.

The local UI is a development integration surface, not a restoration of every historical dashboard,
chart, export, account or cloud capability. Some complex inputs currently use canonical structured
editors. Single-process local queue, SQLite storage and no account authentication mean this is not
a production multi-user deployment. Retain the corresponding source version with saved studies.
