# FlowValue AI

The AI-driven techno-economic assessment copilot for Chemical & CleanTech Engineering.

## Development environment

Requires Node.js 24 (`.nvmrc`), npm, Python 3.12, uv, and Make. Install uv with `python3 -m pip install --user uv` (commands use `python3 -m uv`, so no PATH changes are needed).

```sh
make install
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

Run in two terminals:

```sh
make api
```

```sh
make web
```

Frontend: http://localhost:3000 · API docs: http://localhost:8000/docs · Health: http://localhost:8000/health

`make check` runs backend lint/tests and frontend workspace tests, lint/type checking/production build.
GitHub Actions runs the same checks on pushes and pull requests.

## Repository layout

- `frontend/`: Next.js App Router, TypeScript, Tailwind CSS, ESLint.
- `backend/`: FastAPI, Pandas, NumPy, SciPy, openpyxl, safe XML parsing.
- `.github/workflows/ci.yml`: frontend and backend validation.

Local environment files, virtual environments, dependencies, and build outputs are ignored by Git. Never put secrets in `NEXT_PUBLIC_*` variables: these are exposed to browsers.

The local workspace implements stream/native DWSIM ingestion, equipment costing, DCF/Monte Carlo, dynamic reports, a research copilot, process diagrams, sensitivities and incentive scenarios. Supabase authentication and project-version storage are configured; hosting targets are Vercel and Render (see rollout notes below). BioSTEAM integration imports trusted result snapshots. Core local calculations run without paid APIs.

## Stream ingestion (Phase 1)

`POST /api/streams/parse/json` accepts `{"streams": [...]}`. Each stream requires `stream_id`, `mass_flow_kg_h`, `temperature_c`, `pressure_bar_abs`, and `phase`. Optional `source_unit` and `destination_unit` preserve flowsheet connectivity when provided; connectivity is not inferred. Phases: liquid, vapor, gas, solid, mixed.

`POST /api/streams/parse/csv` accepts a multipart `file` with the same column names. UTF-8 and UTF-8 BOM are supported. Uploads are limited to 5 MiB and 10,000 streams. Invalid rows, duplicate IDs, missing/unknown columns, nonfinite numbers, and nonphysical values are rejected with HTTP 422 (oversized files: 413).

CSV/JSON stream units are explicit: kg/h, Celsius, absolute bar. The native DWSIM parser converts saved SI values automatically.

```sh
curl -F 'file=@backend/examples/streams.csv' http://localhost:8000/api/streams/parse/csv
```

The backend includes `parsers`, `engine`, `financial`, `reports`, and `agent` packages for the phased implementation. Frontend routes remain in `frontend/src/app` as initialized.

## Equipment costing and financial analysis (Phases 2–3)

- `POST /api/costing/bom`: typed heat exchanger, vessel/reactor, pump and compressor specifications; returns sizing, factor provenance, per-unit purchased/bare-module costs and quantity-weighted totals.
- `POST /api/financial/dcf`: annual cash flows, NPV, IRR/DCFROR, both paybacks and pre-tax LCOP. Supply `total_capex_usd` directly.
- `POST /api/financial/monte-carlo`: `financial` inputs plus optional `simulation` settings. Defaults to 1,000 runs and ±20% feedstock/utility price variation.
- `POST /api/assessment`: `costing` specifications plus `financial` assumptions **without CAPEX**. CAPEX is derived from total bare module cost; optional `simulation` runs uncertainty analysis.

```sh
curl -H 'Content-Type: application/json' \
  --data-binary @backend/examples/assessment.json \
  http://localhost:8000/api/assessment
```

The example is synthetic and demonstrates the API; it is not a validated process or investment case. Full units, cost sources, limits, factor assumptions, exclusions and financial conventions are in [the calculation basis](docs/calculation_basis.md). Default CEPCI 800/397 is a planning assumption. Unsupported equipment sizes are rejected by default; explicit extrapolation is flagged. Input schemas are available in `/docs`.

## Live dashboard (Phase 5)

Open http://localhost:3000/dashboard (`/` redirects there). It starts with a clearly labelled synthetic demonstration. Change materials, quantities or expanded per-unit sizing inputs; adjust the economic sliders and annual assumptions to recalculate the displayed scenario. Validation errors remain visible, stale results are marked and exports stay disabled until the displayed result matches the current inputs. Dark/light mode and narrow-screen layouts are supported.

CSV/JSON uploads call the validated stream parser and display stream data. They do not automatically infer equipment duties, thermodynamics, connectivity or equipment sizing. Configure equipment inputs separately. A CSV example is in `backend/examples/streams.csv`.

Frontend API calls use the same-origin `/api` proxy. Set **server-only** `API_INTERNAL_URL` in `frontend/.env.local` when the backend is not at `http://127.0.0.1:8000`. Docker Compose supplies `http://backend:8000`; no browser-visible backend address is required. Restart Next.js after changing environment variables. `NEXT_PUBLIC_API_URL` from the original scaffold is no longer used.

## Exports (Phase 4)

- `POST /api/export/excel` and `POST /api/export/pdf` accept the same body as `/api/assessment` and stream the current scenario's file.
- `GET /api/export/excel` and `GET /api/export/pdf` export the labelled synthetic demonstration, without shared server state.
- `GET /api/demo` supplies the demonstration inputs. Optional `is_demo` controls the demonstration label in exports; the dashboard exposes this choice explicitly.

The workbook contains Summary, Inputs, Equipment BOM, Cash Flow and Notes sheets. All numeric cash-flow cells are native Excel formulas. CAPEX links to a quantity-weighted BOM, equipment costs use editable size/factor correlations, and financial results use active NPV/IRR/payback/LCOP formulas. Edit blue inputs; same-sheet calculations are dark and cross-sheet links green. A 100-year formula schedule supports changing operating life from 1 to 100 years without extending ranges. Mechanical sizing/material labels/pressure factors are export snapshots; editable sizes and factors drive equipment cost formulas. Risk simulations are recomputed in the app, not inside Excel.

Excel/LibreOffice recalculates the workbook on opening. Lightweight file previews that do not evaluate formulas may initially show blanks. No macros, password protection or external workbook links are used. The two-page PDF contains the scenario's metrics, grouped BOM, cash-flow curve, actual Monte Carlo histogram, percentiles and estimate-basis notes.

```sh
curl -H 'Content-Type: application/json' --data-binary @backend/examples/assessment.json \
  -o assessment.xlsx http://localhost:8000/api/export/excel
curl -H 'Content-Type: application/json' --data-binary @backend/examples/assessment.json \
  -o assessment.pdf http://localhost:8000/api/export/pdf
```

## Universal cost advisor and market research

The dashboard's **AI Market & Risk Advisor** profiles the active cost structure automatically. It annualizes CAPEX using the capital recovery factor, ranks the top three cost leaves, and reports raw materials/utilities as subsets of variable OPEX. Cost contributions therefore reconcile to LCOP without double counting. Deterministic rules suggest 20-50% screening stresses and compute NPV impacts with the financial engine. These are scenarios, not forecasts or calibrated probability ranges.

Clicking a recommendation compounds its change from the current scenario and updates the corresponding slider. Actions beyond the +/-50% range are disabled. Named-material/utility recommendations explicitly stress the entire cost category; commodity-specific consumption models are not implied. CAPEX stress has a separate 0.5-1.5 multiplier, preserved in Excel's editable Inputs C20 and BOM formulas and labelled in the PDF. Selling-price, fixed-OPEX and other variable-OPEX stresses are available under additional sensitivities. Cash flows support cumulative and waterfall views.

Set project name, process description, classification and region in the advisor panel. The optional detailed-cost editor names base annual raw-material and electricity/steam/water components; these must fit within the base category totals and are not additional expenses. Auto-classification uses provisional keyword rules for electrochemical, thermal, biological, separation, circular and specialty processes; users can override it. There is a general fallback, and rules are extensible in `app/agent/universal_advisor.py`. Stream observations are summarized without inferring thermodynamics, consumption or equipment sizing.

- `POST /api/assessment/universal-suggestions`: accepts an assessment request, a result state containing `bom` plus `financial.inputs`, or generic explicit economics. Generic fields include `total_capex_usd`, annual fixed/variable/feedstock/utility OPEX, plant capacity, discount rate and operating years. `equipment_bom` may contain arbitrary equipment names with `cost_usd` and `quantity`; this profiles quoted equipment without creating a new mechanical cost correlation. Alternatively `opex_breakdown` accepts `fixed`, `variable`, `raw_materials` and `utilities`; named entries use `name` and `annual_cost` in USD/year. Missing assumptions are disclosed; incomplete stream-only projects cannot produce an economic profile.
- `POST /api/copilot/research-sensitivities`: accepts `{project, question?, market_context?}` and streams SSE events: `profile`, `recommendations`, `status`, `delta`, `citation`, `complete` or `error`. Market context entries contain `title`, `summary`, `url` and optional `published_at`; supplied context is unverified until independently researched.

**Run Market Risk Scan** uses the backend's `OPENAI_API_KEY` and optional `OPENAI_MODEL` (default `gpt-5.4-mini`). It uses the [OpenAI Responses API with live web search](https://developers.openai.com/api/docs/guides/tools-web-search) and [streamed output](https://developers.openai.com/api/docs/guides/streaming-responses). Search is restricted to a configurable primary-source host list, including energy agencies, governments and statistical bodies. `RESEARCH_DOMAINS` can override that list as a JSON array. Sources are linked inline and results show retrieval time. Raw uploads, full stream tables and unknown project fields are not sent to the model; the model receives a computed profile, equipment summary, project context and the research question. Only an explicit scan sends a paid API request. Ordinary profiling remains local and works without a key.

The copilot returns commentary; executable slider actions remain calculated server-side and require a human click. Partial/failed scans are marked unavailable, and briefings are marked stale when the scenario changes. No numeric probability of CAPEX overrun is produced because the current Monte Carlo model samples operating costs, not CAPEX. Policy research does not establish eligibility. Production-credit scenarios are enabled only through explicit user-confirmed assumptions (see below).

The uploader accepts stream CSV/JSON and complete assessment JSON with `costing`, `financial`, optional `advisor_context`, and optional normalized `streams`. The separate generic profiling endpoint does not imply arbitrary equipment can be mechanically costed by the dashboard. Try `backend/examples/biological-assessment.json` for a clearly labelled, synthetic biological cost-profile example. No performance or profitability validation is implied by that example.

## API keys

No key is needed for deterministic calculations or cost profiling. `OPENAI_API_KEY` enables live market research; `ANTHROPIC_API_KEY` is reserved and is not currently used. Add real keys only to ignored local backend environment files, never frontend public variables or Git.

## Docker

To run both services (stop local servers first if ports 3000/8000 are occupied):

```sh
docker compose up --build
```

Open http://localhost:3000/dashboard. Both host ports bind only to loopback. The frontend waits for backend health and proxies requests over the Compose network.

Backend-only image:

```sh
docker build -t flowvalue-api backend
docker run --rm -p 8000:8000 --env-file backend/.env flowvalue-api
```

## Dependency updates

Frontend dependencies are pinned by `frontend/package-lock.json`. Backend dependencies are pinned by `backend/uv.lock`; run `python3 -m uv lock --upgrade` followed by `python3 -m uv sync --frozen --extra dev` inside `backend` to update. `requirements-dev.lock` is a pip-compatible export; regenerate with `python3 -m uv export --frozen --extra dev --no-hashes --output-file requirements-dev.lock`.

Framework setup references: [Next.js installation](https://nextjs.org/docs/app/getting-started/installation), [FastAPI](https://fastapi.tiangolo.com/tutorial/first-steps/).

## Native engineering and reporting workspace

- Upload `.dwxml` alongside CSV and JSON. Dashboard uploads are capped at 4 MiB to fit Vercel’s request limit; direct backend XML uploads retain a 5 MiB parser limit. The parser uses `defusedxml`, a 5 MiB limit, native object tags/connectors and saved SI results (K→°C, Pa→bar absolute, kg/s→kg/h). It never runs scripts, calls DWSIM automation, or re-converges the simulation. Supported complete saved sizing maps to the BOM; unsupported or incomplete operations remain visible in import review. Their exclusion is carried into dashboard warnings, Excel notes and PDF. Operating pressure is only a provisional design-pressure basis; review design margins and material assumptions.
- `/process-flow` displays connected material streams in an editable React Flow diagram and an orbitable Three.js 3D block view. Click nodes to edit supported sizing, recalculate and return to the dashboard. This is a schematic, not a mechanical layout. Tab-local draft state links these pages; cloud revisions are saved explicitly.
- OpenPyTEA **3.2.1** is installed and called through `POST /api/integrations/openpytea/equipment`. The integration catalog lists correlation families and units. External installed-cost estimates become editable, source-labelled quoted equipment; they are not asserted to have the same scope as a Turton bare-module estimate. Source: [OpenPyTEA](https://github.com/pbtamarona/OpenPyTEA), MIT.
- BioSTEAM integration accepts a **validated result snapshot**, not executable Python. From a trusted, already simulated BioSTEAM environment, call `app.integrations.libraries.snapshot_biosteam(tea, product, reference_cepci=..., provenance=...)`, serialize its return value as JSON, then upload it. The API recomputes economics on FlowValue's disclosed DCF basis. It does not rebuild an arbitrary biochemical process from stream totals or claim independently validated thermodynamics. See [BioSTEAM TEA documentation](https://biosteam.readthedocs.io/en/latest/API/TEA.html) and `backend/examples/biosteam-snapshot.json` (synthetic example).
- `POST /api/assessment/tornado` runs ±20% one-at-a-time sensitivities. The dashboard ranks NPV impacts without interpreting them as probabilities.
- `POST /api/copilot/executive-memo` drafts an investment memo from computed results and assumptions, using the server-side OpenAI key. Download the editable Markdown draft and review it before distributing it; it is separate from the deterministic two-page financial PDF.

### Incentive scenarios and cost-index provenance

`financial.incentive` supports a per-product-unit credit, eligible production fraction, first operating year, duration, cash-payment or nonrefundable tax-offset treatment. Enabling it requires an explicit eligibility confirmation and written basis. Cash-payment credits are modeled outside taxable income; tax offsets are capped by annual tax liability without carryforward. These assumptions flow through DCF, Monte Carlo, charts and active Excel formulas. LCOP remains before tax and credits. A label such as “45V” is not an eligibility engine: the operator must verify current legislation, dates, emissions intensity, wage conditions, product units and monetization using the [IRS source](https://www.irs.gov/credits-deductions/clean-hydrogen-production-credit).

`GET /api/indices/cepci` returns a versioned source catalog; it is **not a live feed**. The default 800 remains an unverified planning assumption. New licensed observations are validated and appended with:

```sh
cd backend
.venv/bin/python scripts/import_cepci.py /path/to/reviewed-observation.json
```

The JSON requires `period`, `value`, `source_url`, `source_title`, `retrieved_on`, `reviewed_by`, `status` (`verified` or `assumption`), and optional `note`. Commit reviewed changes to preserve the audit trail. Obtain update rights from the [CEPCI publisher](https://www.chemengonline.com/pci-home/); no subscription data is scraped or redistributed automatically.

### Accounts, saved versions and hosting

Supabase project `flowvalue-ai` (`ywrqkclxwcjungkrtlpq`, London) is separate from unrelated account projects. Schema is in `supabase/migrations/20261026105814_flowvalue_projects.sql`. Owner-based RLS protects immutable project-version rows, and the save RPC checks the expected revision atomically. No service-role key is used by this app. Email/password sign-in and registration live under **Accounts & saved projects**; email confirmation follows Supabase's settings. Explicitly save a new revision to retain scenario, stream and native-import history. Loading an older version then saving requires resolving a revision conflict or saving as a new project.

Set backend `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY`. Local engineering mode defaults to `REQUIRE_AUTH=false`; **public deployment must use `REQUIRE_AUTH=true`**. The backend validates bearer tokens against Supabase Auth before protected API calls. The same-origin frontend proxy forwards tokens. Public `/api/config` exposes only the publishable client configuration; OpenAI credentials remain on the backend.

Deployment status (26 October 2026): the authenticated Render backend is live at [flowvalue-api.onrender.com](https://flowvalue-api.onrender.com/health), service `srv-dbfnag6i0phs73ba5pgg`, Frankfurt, free plan. Anonymous `/api/demo` is rejected with HTTP 401. Cloud AI was activated with the owner's explicit approval on 27 October 2026; provider/model access, hosted research with linked sources, and hosted memo generation/download were verified. The Next.js frontend is live at [flowvalue-ai.vercel.app](https://flowvalue-ai.vercel.app/dashboard), rooted at `frontend` and proxied to Render. Its public configuration points at the correct Supabase project and requires sign-in; anonymous API calls return 401. Production email redirects were configured on 27 October 2026: Site URL `https://flowvalue-ai.vercel.app/dashboard`, with that exact URL and `http://localhost:3000/dashboard` allowed. Project identity/revision metadata persists through refresh and process-flow navigation in the same tab. Production acceptance passed on 27 October 2026: real user sign-in, creation of a labelled demo project, refresh with revision identity retained, restoration from cloud history over an unsaved edit, and saving/reloading revision 2. Database transaction tests separately verified stale-write rejection and cross-user read/write isolation.

Deployment targets selected for this project:

1. **Render:** `render.yaml` defines a free Docker service rooted at `backend`, `/health`, and required authentication. Configure the two Supabase values, the server-only OpenAI key if authorized, and optional primary-source research hosts. No local `.env` files are committed.
2. **Vercel:** import the GitHub repository with root directory `frontend`, Next.js preset, and `API_INTERNAL_URL=https://<actual-render-service>.onrender.com`. `frontend/vercel.json` allows a 300-second research proxy duration where the plan supports it.
3. Confirm the frontend origin in Supabase Auth Site URL/redirect configuration before sending confirmation or password-recovery links to users. Provider account terms and any paid plans require the account owner's approval. Free Render instances can sleep, so first requests may be slow.
4. Verify `/health`, anonymous API rejection, authenticated project save/load and tenant isolation after deployment. Source checks passing do not by themselves prove a live deployment.

Phase 2 core workflow checks and supported import/export behavior are recorded in [the acceptance checklist](docs/phase-2-acceptance.md). The uploader includes downloadable sample CSV and explicitly labelled demo project JSON. Scope warnings are recomputed from the active native mapping and carried into saved projects, Excel and the two-page PDF.

AI configuration and data handling are described in [Phase 3 AI setup](docs/phase-3-ai.md). The dashboard reports AI availability, offers a model-access check, labels sourced research versus computed-only memos, and blocks stale memo downloads. Cloud generation is enabled using a server-only key explicitly authorized by the owner on 27 October 2026.

Phase 4 adds [engineering reference checks and the isolated BioSTEAM runner](docs/phase-4-engineering.md). Use `make validate-engineering` for the seven frozen arithmetic cases, or `make install-biosteam` / `make validate-biosteam` for the optional trusted simulator template. Native imports have reviewed unit-level completion forms. No paid AI calls are required for these workflows.

Phase 5 adds [policy evidence, CEPCI rights and release checks](docs/phase-5-release.md). The Engineering section provides custom/45V preliminary screening, an unconnected licensed-index holder with operator template, and an on-demand readiness check. No paid AI request, new subscription or database migration is required. Tax eligibility and independent plant validation still require project-specific review.

The expanded analyst product follows the [A–I build and independent-review roadmap](docs/product-build-roadmap.md) and [founder requirements](docs/analyst-workflow-specification.md). Phase A adds a design/evidence/cost register and explicit reviewed OPEX replacement in the dashboard. CAPEX ledger entries are planning-only until total-capital integration. The [supplied workbook](docs/reference-workbook-benchmark.md) is presentation inspiration only; none of its formulas or results are implementation/validation sources. No IChemE recognition is claimed.
