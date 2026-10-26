.PHONY: install api web check
install:
	python3 -m venv backend/.venv
	cd backend && .venv/bin/python -m pip install -r requirements-dev.lock
	cd frontend && npm ci
api:
	cd backend && .venv/bin/python -m uvicorn app.main:app --reload --port 8000
web:
	cd frontend && npm run dev
check:
	cd backend && .venv/bin/python -m ruff check . && .venv/bin/python -m pytest
	cd frontend && npm run lint && npm run typecheck && npm run build
