# Review before calculation — 8 November 2026

GitHub main d7a2ff6 already includes Seyram's published Revenue changes from 6 November. Fetch found no newer main commits. RevenueDashboard, revenue forms and Revenue engine were retained.

## Workflow

1. Entry uploads the workbook and saves process/revenue descriptions. Its engineering API now defaults to preparation only: canonical extraction/review, equipment matching and conversion-assumption proposals. No equipment, CAPEX, OPEX or finance calculation runs at this point.
2. Equipment presents a spreadsheet-style review register with linked stream evidence, selected model, model input quantities/units, design size, quantity and conversion assumptions. Users can add, rename or remove equipment with explicit user provenance. Research requires opt-in and a selected focus; findings remain drafts. Save inputs, then explicitly Run Equipment using deterministic Python. Existing per-equipment save previews remain available after the first equipment calculation.
3. CAPEX and OPEX expose grouped assumption editors and methodology factor ranges, bases and sources. AI preparation saves drafts without numerical execution; Save and Run are separate. Draft factors requiring unavailable future totals remain reviewable.
4. Revenue retains Seyram's workflow, commercial approval and user-authoritative Revenue Box. OPEX preparation and the new OPEX structured editor preserve Revenue fields.
5. Shared navigation keeps the selected assessment across stages. Existing stage prerequisites and stale-result tracking remain authoritative; opening a page does not execute dependencies.

## Checks

- Frontend production build and TypeScript passed. Browser testing caught a save-state issue caused by server JSON key ordering; value-based comparison now prevents unchanged saved drafts remaining falsely dirty.
- 35 backend tests passed: review/preparation boundaries, explicit equipment run, user register event replay/provenance, duplicate/stale revision rejection, factor catalogues, missing OPEX bases, and existing Revenue forms/price edits.
- 15 existing engineering workflow, stage isolation and stage connection tests passed in the first combined run. Its one new API test initially used an incorrect function name; corrected and included in the successful 35-test run.
- Ten frontend tests passed: Revenue series, assessment navigation and order-independent saved JSON comparisons.
- Another 22 specialist/research workflow regression tests passed.
- Browser verification uses a separate synthetic workbook, not Charlie prices or production inputs. Paid AI and external research were not invoked. Source models and assumptions are not certified by these workflow tests.

## Limits

- AI preparation and external research remain provider-dependent; this change tests their stage boundaries with deterministic test providers, not new paid model runs.
- New array items require explicit numerical inputs; no fabricated cost defaults are supplied. Complex multi-parameter models retain the existing detailed equipment controls.
- Model matches do not guarantee sufficient design data or validated engineering suitability. Missing units/bases remain visible.
- Register edits retain source observations and version history; a complete re-extraction whose generated equipment identities change may still require review of the user overlay.
- Production deployment is outside this change. The founder subsequently requested publishing the complete local build to main; existing pricing improvements are included and duplicate sync files remain excluded.
