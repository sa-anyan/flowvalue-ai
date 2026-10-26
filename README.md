# FlowValue AI

The AI-driven techno-economic assessment copilot for Chemical & CleanTech Engineering.

## Development environment

Requires Node.js 24 (`.nvmrc`), npm, Python 3.12, and Make.

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

This is the development foundation. Simulation ingestion, equipment costing, financial models, LLM integration, exports, authentication, storage, and deployment are not implemented yet. DWSIM and domain-specific TEA integrations will be validated and added separately. No cloud services or paid APIs are required to run this foundation.

## Dependency updates

Frontend dependencies are pinned by `frontend/package-lock.json`. Backend development dependencies are pinned by `backend/requirements-dev.lock` for Python 3.12. To update backend dependencies, install `-e ".[dev]" --upgrade` in the virtual environment, then regenerate the lock with `pip freeze --exclude flowvalue-api`.
