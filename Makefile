# ==============================================================================
# KMRL Document Intelligence & Action Portal Makefile
# ==============================================================================

.PHONY: help dev-up dev-frontend services-up migrate seed seed-corpus dev-backend dev-worker test clean

help:
	@echo "KMRL Document Intelligence Portal"
	@echo ""
	@echo "Available commands:"
	@echo "  make dev-up        - Single-command backend bootstrap (Docker, Postgres wait, migrations, seeds, Uvicorn, Celery)"
	@echo "  make dev-frontend  - Start Vite development frontend (http://localhost:5173)"
	@echo "  make services-up   - Start PostgreSQL and Redis containers via Docker Compose"
	@echo "  make migrate       - Run Alembic database migrations"
	@echo "  make seed          - Seed synthetic departments and demo RBAC users"
	@echo "  make seed-corpus   - Seed full demo document corpus (requires backend running)"
	@echo "  make dev-backend   - Run FastAPI dev server with auto-reload"
	@echo "  make dev-worker    - Run Celery background task worker"
	@echo "  make test          - Run frontend build & backend verifications"

dev-up:
	@python backend/scripts/dev_up.py

services-up:
	docker compose up -d postgres redis

migrate:
	cd backend && alembic upgrade head

seed:
	cd backend && python scripts/seed.py

seed-corpus:
	cd backend && python scripts/seed_demo_corpus.py

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-worker:
	cd backend && celery -A app.jobs.celery_app.celery_app worker --loglevel=INFO

dev-frontend:
	cd frontend && npm run dev

test:
	cd frontend && npm run build
	cd backend && python scripts/verify_auth.py
