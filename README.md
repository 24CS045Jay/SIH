# KMRL Document Intelligence & Action Portal

This repository contains the Phase 1 monorepo scaffold for the CHA-225 KMRL Document Intelligence & Action Portal. It intentionally contains **synthetic/demo-safe UI copy only**. The portal is designed around a traceable workflow in which document intelligence produces reviewable information, not silent automation.

## Repository layout

| Folder | Responsibility |
| --- | --- |
| `frontend/` | React + TypeScript + Vite portal shell, route guard, three-column workspace, and government-enterprise design tokens. |
| `backend/` | FastAPI application, typed schemas, modular service boundaries, PostgreSQL/Alembic configuration, and Celery/Redis worker skeleton. |
| `docs/` | Architecture diagrams and implementation notes. |

## Local prerequisites

Install Node.js 20+ with npm, Python 3.11+, PostgreSQL 14+, and Redis 6+. Docker users can start the data services with the included Compose file.

## Start PostgreSQL and Redis

```bash
docker compose up -d postgres redis
```

The default development connection is `postgresql+asyncpg://kmrl:kmrl@localhost:5432/kmrl_portal`. No real credentials are stored in this repository.

## Start the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

The health endpoint is `GET http://localhost:8000/api/v1/health`. FastAPI documentation is available at `http://localhost:8000/api/v1/docs`.

## Start the worker

In another terminal, with the backend virtual environment active and Redis running:

```bash
cd backend
source .venv/bin/activate
celery -A app.jobs.celery_app.celery_app worker --loglevel=INFO
```

The placeholder task can be dispatched from a Python shell with `from app.jobs.ping import ping_job; ping_job.delay()`. It returns a JSON result containing `pong` and an ISO timestamp.

## Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The root route is the protected-workspace shell for this phase; `/login` is the public placeholder route. Authentication and production RBAC are deliberately reserved for a later phase, while the route boundary is already represented in the entrypoint.

## Architecture

The architecture is documented in [`docs/architecture.mmd`](docs/architecture.mmd). Render it with Mermaid-compatible tooling. The diagram follows the CHA-225 flow from Users/Reviewers through the Web Portal and API Gateway into Identity/RBAC, Ingestion, Alert/Action Workflow, and RAG Retrieval, with storage, OCR/extraction, intelligence, vector search, analytics, notifications, and audit log dependencies.

## Acceptance checks

From the repository root, run:

```bash
cd frontend && npm run build
curl http://localhost:8000/api/v1/health
```

A healthy backend returns JSON with `status: "ok"`, service name, environment, and a UTC timestamp. The frontend renders an empty left navigation, center stream, and right evidence panel as the Phase 1 base layout.

> **Safety boundary:** Any future AI-derived field must include `source_version_id`, citation, confidence, and review state. Critical, safety, and compliance actions require explicit human approval before publication. Uploaded text is untrusted document data, never an instruction to the application.

## Phase 2 database schema

Phase 2 adds the complete PostgreSQL relational model specified by CHA-225. The authoritative SQLAlchemy entities are in `backend/app/models/entities.py`, with enum definitions and naming conventions in `backend/app/models/base.py`. The schema contains `users`, `departments`, `documents`, `document_versions`, `files`, `pages`, `chunks`, `extracted_facts`, `actions`, `action_events`, `alerts`, `assignments`, `comparisons`, `changes`, `audit_events`, and `feedback`.

Run the migration against a fresh PostgreSQL database with:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

Seed only synthetic departments and RBAC users with:

```bash
python scripts/seed.py
```

The seed script creates seven departments and seven demo users covering all six RBAC roles. It intentionally creates no documents or document-derived records. Demo credentials use a deterministic placeholder hash for local development only and must not be used in a production deployment.

`document_versions` and `audit_events` are protected by a SQLAlchemy `before_flush` guard in `backend/app/models/__init__.py`. Attempts to update or delete either entity through the application session raise an error. New uploads must create a new immutable version row; audit events must be appended rather than edited or removed.

The schema ER diagram is available as Mermaid source in [`docs/schema-er.mmd`](docs/schema-er.mmd) and as a rendered image in [`docs/schema-er.png`](docs/schema-er.png).
