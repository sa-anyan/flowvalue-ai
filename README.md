# FlowValue AI

Current controlled rebuild: modular chemical-engineering techno-economic assessment,
with a Python backend and Next.js frontend. The original application remains in the
recovery checkpoint below. Historical acceptance documents describe their respective
versions; they are not certification of this rebuild.

## Current workspace

Canonical local directory: `/Users/user/Documents/ChatGPT/Chemical Engineering Automation`.
The current build includes equipment costing/unit conversion, CAPEX, OPEX, six-category
Revenue, financial modelling, workbook ingestion, saved local assessments and the
Commercial Strategy Analyst. Research and commercial assumptions remain reviewable;
Python performs the calculations. Independent industrial validation is outstanding.

- Backend: `backend/api/app.py` and the canonical calculation packages.
- Frontend: `frontend/src`; Entry, Revenue and the connected assessment pages.
- Commercial agent: `backend/revenue/llm/COMMERCIAL_STRATEGY_ANALYST.md`.
- Product requirements: `docs/analyst-workflow-specification.md` and `docs/product-build-roadmap.md`.

## Local development

Use Python3.12 and Node24. Install backend requirements from
`backend/requirements-orchestration.txt` in a virtual environment and run from the
repository root:

```sh
python -m uvicorn backend.api.app:app --host 127.0.0.1 --port 8000 --env-file backend/.env
```

In `frontend`, run `npm ci` and `npm run dev`. Open `http://localhost:3000/entry`.
Server-only AI configuration is described in `backend/orchestration/.env.example`;
never commit keys. The local SQLite assessment store and uploaded workbooks are in
ignored `outputs/`; they are not published to GitHub.

## Deployment status

This rebuild's API currently enforces localhost access and its SQLite persistence is
local. Cloud release requires explicit access protection, a configured backend URL,
server-only secrets and durable storage decisions. The earlier production deployment
must not be treated as proof that this new runtime is cloud-ready. Provider settings
and release checks must be verified for the actual deployment commit.

## Recovery checkpoint

- Repository: https://github.com/sa-anyan/flowvalue-ai
- Checkpoint commit: `a6c0a471ba1669ed10abbceeae80fa3a9006f612`
- Checkpoint branch: `codex/checkpoint-before-costing-rebuild-2026-10-29`
- Annotated tag: `checkpoint-before-costing-rebuild-2026-10-29`
- New working branch: `codex/controlled-rebuild`

The complete earlier application remains in the checkpoint. Recover individual files/features only when required, reviewing dependencies, licences and tests before bringing them into this rebuild. Do not merge the entire checkpoint by default.

```sh
# Inspect a previous file without restoring it:
git show checkpoint-before-costing-rebuild-2026-10-29:path/to/file

# Restore a specifically agreed file into the rebuild:
git restore --source checkpoint-before-costing-rebuild-2026-10-29 -- path/to/file
```

