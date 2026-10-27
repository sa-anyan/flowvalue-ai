.PHONY: install api web check
install:
	cd backend && python3 -m uv sync --frozen --extra dev
	cd frontend && npm ci
api:
	cd backend && .venv/bin/python -m uvicorn app.main:app --reload --port 8000
web:
	cd frontend && npm run dev
check:
	cd backend && .venv/bin/python -m ruff check . && .venv/bin/python -m pytest
	cd frontend && npm test && npm run lint && npm run typecheck && npm run build
