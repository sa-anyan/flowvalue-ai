# Local end-to-end engineering orchestration

This integration connects the controlled-rebuild engines without modifying their
calculation modules. It restores the original FlowValue Excel parser selectively
from checkpoint a6c0a471ba1669ed10abbceeae80fa3a9006f612. See
`../ingestion/RECOVERY.json` for source hashes.

## Run

From the repository root, use a Python 3.11+ environment:

```sh
python -m pip install -r backend/requirements-orchestration.txt
python -m uvicorn backend.api.app:app --host 127.0.0.1 --port 8000
```

In another terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open http://localhost:3000/entry. The Next server proxies only the assessment,
version, catalogue and health endpoints. `FLOWVALUE_BACKEND_URL` is server-only,
with default http://127.0.0.1:8000. This is a **local development workspace**, not
the old cloud application. Its accounts, Supabase, exports, charts and production
routes have not been restored. Do not expose the unauthenticated API publicly.

To enable explicitly requested AI proposals, set server environment variables
`AI_ENABLED=true`, `OPENAI_MODEL=<structured-output-capable model available to your account>`
and `OPENAI_API_KEY`. Secrets are not stored in assessment files, sent to the
browser or passed into the spreadsheet subprocess. No model or key is assumed.
Use one API process: its bounded worker queue is process-local. A restarted process
can leave a running assessment marked busy; reopen a previously saved version.

## Workflow and calculation ownership

1. Upload .xlsx/.xls/.xlsm and a process description. Workbook decoding uses a
   separate subprocess (30-second timeout, 20-second CPU limit, Linux address-space
   cap, bounded sheets/cells and upload bytes). VBA, formulas and external links
   are never executed. Cached formula results are not recalculated.
2. Optional AI proposes configurations/engineering and economic assumptions using
   available canonical model contracts, factors, parsed evidence and bounded raw
   source cells. One request, no autonomous retries, max 12,000 output tokens,
   no tools, 60-second network timeout. Context above 240,000 characters is rejected.
   Truncated source-cell coverage is disclosed. Cache keys include the exact
   context, model and prompt version. Explicit refresh can make a new paid request;
   ordinary Run Again never calls AI.
3. Python validates exact model IDs, units, ranges and calculation bases through
   the existing engines. AI can recover a missing numeric property only within an
   existing aligned stream table, with an explicit source header/unit. Python reads
   the original value itself. Conflicts remain pending review, existing values are
   never replaced, and no new stream/equipment connection is created by AI.
4. Canonical equipment totals retain their incomplete status. CAPEX consumes only
   the separate priced subset with a purchased-cost component. Every unpriced item
   remains an explicit exclusion with null cost. All downstream results are scoped
   to that subset, not represented as whole-plant totals. Module/installed-only
   values are never reclassified as purchased costs.
5. Revenue precedes final OPEX calculation because royalties and other costs use
   annual sales. Physical revenue quantities are rebound to source-backed stream
   keys. OPEX capital and revenue bases refresh every rerun. Financial handoff uses
   canonical results, prevents duplicate depreciation/financing, and rejects price
   year mismatches rather than relabelling historical prices as current.
6. Product quality, saleable fraction, boundary and review require user decisions.
   AI cannot self-approve them. Independent stages continue if another is unresolved.
   Complete financial schedules require complete, compatible assumptions.
7. Edit fields/configuration controls or canonical structured input. Save with a
   reason to lock that section against future AI replacement. Run Again updates all
   dependent Python calculations. Section locks deliberately favour preserving user
   choices over silently filling gaps. Source workbook values remain unchanged.
8. Named versions save parsed inputs, original file, proposals, overrides and outputs
   in private local SQLite. Opening a version creates an independent model. Comparison
   includes complete engine results and changed sections; originals are untouched.

The value-level assumption register inherits stage rationale/uncertainty and stores
nested assumptions' own units, rationale and sources when present. Inherited generic
rationales are not equivalent to equipment-specific validated engineering evidence.

## Verification and limits

Run `python -m unittest discover -s backend/tests -v`. Private workbook tests skip
when its local file is unavailable. Portable negative/security tests still run.
Real case: **Mass Balance Team 8.xlsm**, five sheets, seven equipment tags, fourteen
material records with usable mass-flow values; other records remain unresolved.
No claim of universal workbook compatibility is made. Numeric recovery is deliberately
restricted; complex ambiguous tables, missing components and topology still need review.

The full financial-chain test uses this real workbook but **synthetic user-defined
sizing, quality, saleability, prices, staffing and financial policy**, in historical
1987 USD. It tests data handoffs and reproducibility, not this plant's business case.
Artifacts are saved privately under `outputs/orchestration-review/`; the workbook
is not copied into public source. Test reports identify synthetic assumptions.

Live OpenAI generation is implemented but was not invoked in development validation:
no paid requests or live researched prices were used. Tests exercise deterministic
provider responses, caching, outages and locked overrides; they do not establish the
accuracy or completeness of a live model's engineering judgement. Research is limited
to supplied references: no external research or supplier/buyer contact is implemented
or automatically authorized. Broad source recovery and model compatibility still need
representative industrial review. The AI output cap can leave parts of a large plan
unresolved. Manual user inputs can complete these using canonical contracts.

Local database storage is single-user and not cloud account storage. No authentication,
access-role design, public deployment or accreditation claim is included. Store saved
versions alongside the exact code version when retaining reproducible studies.
