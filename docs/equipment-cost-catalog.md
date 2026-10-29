# Equipment cost name catalog

This build catalogs **51 chart groups** in Donald E. Garrett, *Chemical Engineering Economics* (1989), Appendix 1, printed pages 256–306 / supplied PDF pages 6–56. The supplied file contains other appendices too; plant-cost charts outside Appendix 1 are deliberately excluded.

## Storage and provenance

- `backend/app/data/equipment_catalog.json`: reviewable seed, one record per chart group, normalized spelling, manually curated synonyms and family classification.
- `backend/app/data/equipment_catalog.sqlite3`: shipped read-only SQLite database; equipment, aliases and source/version tables. No extra cloud database or paid service is required.
- `python tools/build_equipment_catalog.py` rebuilds the database from the seed. Both are packaged with the API. Tests reconcile seed and database and require all 51 chart pages exactly once.
- Each item retains the original source filename and SHA-256 via the source record, PDF page, printed page, stable ID and `not_digitized` method status. Synonyms are FlowValue interpretation, not a quotation from the source.
- Buildings, insulation, pipework, ducts and internals are marked capital items, not misrepresented as major process equipment.

**Only names are cataloged.** No textbook graph images, curve coordinates, equations, installation factors or prices are copied into the application. Existing independent costing methods are unchanged. A name match does not establish correlation applicability, equipment design, materials, sizing or cost validity. Future cost methods need their own reviewed provenance, applicability and source/licensing basis.

## Matching

`GET /api/equipment/catalog` returns the versioned names catalog. `POST /api/equipment/match` accepts the existing bounded `BalanceReport` and returns one result per scoped equipment entity, retaining source evidence and candidate page references. The frontend proxy exposes both routes. CAPEX → Equipment displays matching even when no financial project exists and preserves existing equipment/baseline/analyst sections.

The matcher normalizes plural forms, case and punctuation; resolves curated aliases; prefers specific phrases over contained generic names; resolves shared stream references; and isolates wording adjacent to the actual equipment tag. It never assumes P means pump, creates equipment or updates an approved baseline. Family-level evidence and conflicting alternatives require review. Unknown types remain unmatched. No LLM calls, research or numerical confidence scores are used.

Known limits: heuristic English terminology and conventional tag-adjacent prose; arbitrary abbreviations, spelling errors, long narratives, multilingual descriptions and unusual sentence structures can remain unmatched or need review. The initial synonym list is extensible, not universal semantic understanding. The parser still determines which equipment exists; matching cannot recover equipment absent from the parser register. Cost chart subtypes and service conditions still require engineering review even for a displayed name Match. Parsed numerical balances remain separate from equipment-name recognition.

## Reference check

Mass Balance Team 8.xlsm: four tank name matches (T-001, B-001, T-002, T-003); R-001 bioreactor → review Reactors; S-001 biomass settler → review Thickeners and clarifiers; P-001 pH adjustment → no match. Unrelated upstream unit names must not contaminate destination matches.

## Workspace reliability

The existing draft-write effect could erase a stored balance before asynchronous restoration during development StrictMode. Persistence now waits until restoration completes. Browser acceptance must include actual upload → CAPEX match table → refresh, in addition to API tests. No source workbook or baseline is edited.

## Verification on 29 October 2026

246 backend tests and 38 frontend tests passed. Targeted ESLint, frontend TypeScript checks and the optimized production build passed. Actual browser upload of the retained Team 8 workbook, navigation to CAPEX Equipment, matching table and full refresh passed after the restoration fix. Source-cell evidence and the 51-entry catalog are inspectable in native expandable details. Local API/proxy responses were checked; no paid AI calls or deployment were performed.

## Second supplied PDF: full Garrett textbook

`Chemical Engineering Economics for me.pdf` is the same author/title/1989 edition, with 431 PDF pages. All 51 Appendix 1 chart pages have identical whitespace-normalized extracted text to the first supplied PDF (page offset +261). This is duplicate source coverage, not independent equipment estimates or a different author. Both file SHA-256 identities and page references are retained in `sources` and the 102 `equipment_sources` associations; the 51 canonical chart names are unchanged. Each API item now includes `source_refs` and the catalog returns the complete `sources` list. The legacy `source` field remains available.

Historical index bases are stored per source: CE Index 320, early 1987, first file PDF p. 5 / printed p. 255; full book PDF p. 25 / printed p. 13 (also stated in its Appendix introduction). These agree. The model's independently sourced default reference index 397 and configurable target index are not overwritten or blended with Garrett's 320. Only the source-stated basis is cataloged; index history graph points and cost curves are not digitized. Different author/method variants must remain separate source-qualified records if added later; no automatic averaging or conflict resolution is implemented. UI candidate rows label each reference as Garrett appendix extract or full textbook, and Sources & historical index bases shows both records.

## LLM engineering interpretation layer

CAPEX Equipment now offers an explicit selected-unit interpretation action using the existing backend OpenAI connection and configured model. It sends only the selected unit's bounded source observations, its referenced stream properties, up to 2,000 characters of the Entry description and the names/source metadata catalog. No raw workbook/PDF, other units' registers, financial project, credentials or browser tokens are sent to the model. Stream descriptions can mention neighbouring tags; these remain untrusted context rather than an instruction to reassign identities.

`POST /api/equipment/interpret` uses strict Pydantic structured output, no tools/search, no automatic retry, a 60-second timeout and at most 2,600 output tokens. Existing deployment authentication and AI_ENABLED/key gates apply. Selected units are scoped by entity key, not ambiguous display tags. The request is bounded to 3 MiB before JSON decoding; provider input is bounded to 80 observations and 65,000 encoded characters. Generation incurs provider usage charges only on explicit action. The UI discloses data use and model before generation. There is no new provider, model training, autonomous research or per-user billing quota in this build.

Outputs distinguish verbatim workbook observations from general engineering hypotheses. Candidate methods must use real catalog IDs. Source evidence IDs and exact quote substrings are validated server-side, duplicates/unknown methods and ungrounded observations rejected, and incomplete/refused output rejected. Common explicit monetary/percentage/factor estimates in narrative are rejected; this is a bounded syntactic safeguard, not proof of semantic correctness. Hypotheses can still be wrong and require engineering review. Catalog names cannot establish textbook design/cost applicability.

Proposals expose equipment identity, alternative catalog bases, service differences/modifications to investigate, missing sizing/service inputs, clarification questions and qualitative uncertainty drivers. Bioreactor→agitated vessel/reactor is a provisional method hypothesis, never a claim that a shell includes aeration, hygiene, agitation, cooling or instrumentation. No new unit, connection, property, scaling factor, cost range or approved baseline is created.

Every accepted draft records workbook digest, selected unit key, input digest, catalog version, prompt version, model, generation time, source observations and both source references. The UI fingerprints the entire current report/description/unit to invalidate stale local results, discards responses arriving after input changes, retains the latest draft and acknowledgement in sessionStorage, and allows JSON download. Storage failures are explicit; malformed saved drafts are rejected. Review acknowledgement is a self-entered local note, not authenticated peer approval or engineering certification. It does not approve a baseline. Latest-draft tab persistence is not cloud project revision storage or a multi-draft history.

Cost application is deliberately blocked: catalog curves remain undigitized and the service/design basis, validated sizing/cost method, modification costs and calibrated uncertainty model are not established. This layer prepares a review record for later deterministic method hand-off; it does not implement scaling or Monte Carlo costing. Existing independent financial/sizing engines and approved baselines remain unchanged.

API implementation follows the official structured-output guide: https://developers.openai.com/api/docs/guides/structured-outputs . Structured schema adherence is not a guarantee of engineering truth.

### Interpretation verification — 29 October 2026

256 backend and 40 frontend tests passed, plus targeted Ruff/ESLint/TypeScript checks and the production build. Mocked provider tests cover traceable observations, real catalog IDs, input fingerprints, scoped data, incomplete results, invalid quantitative allowances, deployment authentication, AI-disabled state and oversized bodies. Two bounded live synthetic requests used the configured gpt-5.4-mini connection; no actual user workbook was sent to the provider for these smoke tests. The browser fixture was uploaded on Entry, interpreted on CAPEX Equipment, acknowledged explicitly as an automated synthetic test, downloaded, and restored after full refresh. The downloaded record and test fixture are retained under outputs/local-parser-check. Generated drafts are unvalidated engineering hypotheses, not proof of method applicability. No deployment was performed.

## Process-context matching upgrade

Prompt `equipment-process-context-v2` reasons from process function, scoped composition/properties and source-labelled relationships rather than only equipment wording. The bounded same-sheet/same-case overview includes up to 20 unit descriptors and 40 stream descriptors, with an explicit truncation flag. Selected-unit stream observations are limited to 16 streams / 160 total observations; up to 120 existing selected-stream relationships retain their original role, basis, status and evidence IDs. A descriptive mention or neighbouring overview entry is never promoted into a physical connection. Unknown directions and possible semantic links must remain hypotheses. At least one cited observation must belong to the selected unit before a catalog proposal is accepted. Input digests include this context, so changes to downstream descriptions invalidate interpretation.

CAPEX Equipment displays a visible Why this match column. Deterministic name/candidate matches retain their source wording and reason. Explicit LLM interpretation updates the selected unit's row with provisional catalog names, source references and the model's rationale, labelled AI proposal requiring review. Type unresolved replaces the misleading implication that unmatched equipment is absent from the book. No paid generation is triggered by upload or page load.

The tab cache retains up to 20 current-input unit drafts, keyed by a process-context-version/report/description digest plus scoped equipment key. Selecting another unit does not remove the earlier explanation. Old narrower-context drafts are not silently reused. These are local review records, not approved project baselines or cloud history. Older single-draft documentation above describes the previous build and is superseded by this section.

The v2 provider schema selects short evidence references (e1, e2, …) instead of retyping workbook quotes. FlowValue resolves each selected reference to the original evidence ID, exact original cell text and cell location in the returned draft. This avoids quote transcription/paraphrase failures without accepting invented values. Selected-unit grounding permits distinct parser evidence records from the same workbook/sheet/cell, while a different neighbouring cell alone cannot establish the selected equipment identity. Model-origin prose remains an unverified hypothesis.

### Process-context acceptance — 29 October 2026

259 backend tests and 41 frontend tests passed, plus Ruff, targeted ESLint, TypeScript and production build checks. In the actual local browser, Team 8 upload → P-001 selection → live interpretation produced Agitated tanks as the leading provisional analogue, with Tanks and Agitators as alternatives and service-specific rationale. The table displayed these candidates and why, kept them visible after selecting T-001 and after full reload, and downloaded the traceable record. No cost or baseline was applied. The first two live attempts were rejected by evidence grounding; the final attempt passed after replacing model quote transcription with short evidence-reference selection and server-attached original observations. There were no automatic provider retries. The accepted record and screenshot are retained in outputs/local-parser-check/p001-process-context-interpretation.json and p001-match-and-reason.png. Tests verify both same-cell evidence aliases and rejection of a different neighbouring cell as sole selected-unit evidence. No deployment was performed.
