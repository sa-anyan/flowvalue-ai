.PHONY: install api web check install-biosteam validate-biosteam validate-engineering
PYTHON ?= python3.12
install:
	cd backend && $(PYTHON) -m uv sync --frozen --extra dev
	cd frontend && npm ci
api:
	cd backend && .venv/bin/python -m uvicorn app.main:app --reload --port 8000
web:
	cd frontend && npm run dev
check:
	cd backend && .venv/bin/python -m ruff check . && .venv/bin/python -m pytest
	cd frontend && npm test && npm run lint && npm run typecheck && npm run build

install-biosteam:
	$(PYTHON) -m uv venv --python 3.12 backend/.venv-biosteam
	$(PYTHON) -m uv pip sync --python backend/.venv-biosteam/bin/python backend/requirements-biosteam.txt
validate-engineering:
	cd backend && .venv/bin/python -m app.validation.references
validate-biosteam:
	cd backend && .venv-biosteam/bin/python -m app.integrations.biosteam_runner --output examples/water-heating-biosteam.json
