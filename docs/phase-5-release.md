# Phase 5 — policy scenarios, index rights and release evidence

## Delivered scope

- Versioned, deterministic `POST /api/policy/screen`: custom evidence checklist and preliminary US 45V screen, reviewed 2026-10-27. No LLM calls or automatic benefit rates.
- Saved policy evidence includes reviewer/date, sources, construction/service dates, kg-H2 basis, lifecycle emissions and explicit reviews of verification, ownership/use, conflicting credits, electricity rules, wage/apprenticeship and monetization.
- Named screens reject enabled credits with missing, failed, future-dated or stale evidence. Rule and evidence review freshness is 90 days. For 45V the selected annual window must fit years 1–10 from placed-in-service. The financial model still uses whole operating years; it does not prorate calendar-year claims.
- Editing policy fields resets inclusion and confirmation in the UI. Server validation applies to assessments, Monte Carlo, saves and exports; legacy custom scenarios remain supported and explicitly unscreened.
- Full structured evidence is carried into workbook Notes. The two-page PDF points to workbook evidence. Reports remain scenarios, not tax certifications.
- CEPCI licensing holder stays disconnected with no new subscription expense. A downloadable observation template and append-only operator import include publication, source, reviewer, license reference, distribution rights and rights expiry. Verified observations require rights metadata. Internal-only or expired redistributed data is excluded from the shared catalog API. The application makes no assertion that an entered license reference is genuine.
- Catalog selection captures the source basis in the project/workbook/PDF. Manual index edits clear the old source label. No licensed index data or provider credentials were added.
- `POST /api/release/check` runs current-project DCF, seven frozen references and binary report generation without paid AI or writes. It marks outstanding source, policy and account acceptance work explicitly. UI results are marked stale when the scenario changes.

## Source basis and limits

Reviewed primary sources:

- https://uscode.house.gov/us/usc/119-124/t26/s45V/
- https://www.irs.gov/credits-deductions/clean-hydrogen-production-credit
- https://www.irs.gov/forms-pubs/about-form-7210

The screen checks the construction cutoff **before 2028-01-01**, production after 2022, no greater than 4 kg CO2e/kg H2 and a ten-year window. It does not compute GREET, certify qualifying electricity, calculate inflation-adjusted rates, evaluate detailed wage exceptions, make elections, determine legal ownership or certify tax eligibility. Those are user/adviser-reviewed evidence items. Other jurisdictions use the custom checklist until dedicated rules are implemented.

Manual credits remain useful for hypothetical sensitivities; their labels never imply statutory qualification. Purchased subscription access alone is not redistribution permission. Rights over project snapshots, reports, repository storage and customer downloads must be reviewed separately before adding licensed observations. No live feed is activated by filling in the template.

## Low-cost release acceptance

1. `make check`: backend tests, frontend tests, lint, TypeScript and production build. Phase-5 tests cover screen boundary failures, API auth, export formulas/evidence, index rights filtering and readiness binaries.
2. In the hosted app sign in, load/import a synthetic project, run readiness checks and inspect the policy screen. Confirm an incomplete 45V screen cannot enable benefits.
3. Save as a **new** acceptance project; reload and reopen the saved revision. Confirm evidence and index basis remain. Never overwrite a real customer project for smoke tests.
4. Change a financial assumption and confirm KPIs change; download Excel/PDF and inspect formula cells and source/evidence notes. Excel recalculation occurs in Excel/LibreOffice.
5. Check AI configuration only by default. Generation is separately verified when explicitly needed; readiness does not claim to verify provider quota or generated results.
6. Check backend `/health`, protected endpoint 401 without credentials and frontend availability. Existing Supabase row-ownership tests and browser acceptance are complementary; an API health check does not prove tenant isolation.
7. Record deployment commit and CI outcome. Roll back code through the hosting dashboard if acceptance fails; no schema migration or new infrastructure is required for this phase.

## After the MVP build

Independent representative-project/vendor benchmarking, detailed tax specialist review, acquisition of licensed data and additional sector-specific simulator models remain follow-up validation and expansion work. Passing release checks does not certify a complete commercial plant design.
