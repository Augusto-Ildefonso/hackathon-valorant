.PHONY: setup dev dev-api dev-web dev-mock test fixtures

PY := backend/.venv/bin/python

setup:
	python3 -m venv backend/.venv
	backend/.venv/bin/pip install -r backend/requirements.txt
	cd frontend && npm install

dev-api:
	cd backend && .venv/bin/python -m uvicorn app.main:app --reload --port 8000

dev-web:
	cd frontend && npm run dev

dev:
	$(MAKE) -j2 dev-api dev-web

dev-mock:
	cd frontend && VITE_USE_MOCKS=1 npm run dev

test:
	cd backend && .venv/bin/python -m pytest -q
	cd frontend && npm run typecheck

fixtures:
	$(PY) contract/make_fixtures.py
