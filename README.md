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

`make check` runs backend lint/tests and frontend lint/type checking/production build.
GitHub Actions runs the same checks on pushes and pull requests.

## Repository layout

- `frontend/`: Next.js App Router, TypeScript, Tailwind CSS, ESLint.
- `backend/`: FastAPI, Pandas, NumPy, SciPy, openpyxl, safe XML parsing.
- `.github/workflows/ci.yml`: frontend and backend validation.

Local environment files, virtual environments, dependencies, and build outputs are ignored by Git. Never put secrets in `NEXT_PUBLIC_*` variables: these are exposed to browsers.

Phases 1–3 are implemented: JSON/CSV stream ingestion, equipment sizing/costing, and DCF/Monte Carlo analysis. LLM integration, exports, the financial dashboard, authentication, storage, and cloud deployment are not implemented yet. DWSIM and domain-specific TEA integrations will be validated and added separately. No cloud services or paid APIs are required to run this foundation.

## Stream ingestion (Phase 1)

`POST /api/streams/parse/json` accepts `{"streams": [...]}`. Each stream requires `stream_id`, `mass_flow_kg_h`, `temperature_c`, `pressure_bar_abs`, and `phase`. Optional `source_unit` and `destination_unit` preserve flowsheet connectivity when provided; connectivity is not inferred. Phases: liquid, vapor, gas, solid, mixed.

`POST /api/streams/parse/csv` accepts a multipart `file` with the same column names. UTF-8 and UTF-8 BOM are supported. Uploads are limited to 5 MiB and 10,000 streams. Invalid rows, duplicate IDs, missing/unknown columns, nonfinite numbers, and nonphysical values are rejected with HTTP 422 (oversized files: 413).

Units are explicit: kg/h, Celsius, absolute bar. Convert simulator output to these units before upload. XML/DWSIM ingestion is a later phase.

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

## API keys

No key is needed for Phase 1. Optional `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` placeholders are in `backend/.env.example` for the future copilot. Add real keys only to ignored local backend environment files, never frontend public variables or Git.

## Docker

```sh
docker build -t flowvalue-api backend
docker run --rm -p 8000:8000 --env-file backend/.env flowvalue-api
```

## Dependency updates

Frontend dependencies are pinned by `frontend/package-lock.json`. Backend dependencies are pinned by `backend/uv.lock`; run `python3 -m uv lock --upgrade` followed by `python3 -m uv sync --frozen --extra dev` inside `backend` to update. `requirements-dev.lock` is a pip-compatible export; regenerate with `python3 -m uv export --frozen --extra dev --no-hashes --output-file requirements-dev.lock`.

Framework setup references: [Next.js installation](https://nextjs.org/docs/app/getting-started/installation), [FastAPI](https://fastapi.tiangolo.com/tutorial/first-steps/).
