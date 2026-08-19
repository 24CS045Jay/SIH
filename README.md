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

## Quick Start (Recommended Single-Command Bootstrap)

To start everything locally in one step (Docker services, database wait loop, migrations, demo user seeding, demo document corpus seeding, Uvicorn API server, and Celery worker):

```bash
make dev-up
```

*Or run directly without Make:*
```bash
python backend/scripts/dev_up.py
# or on Linux/macOS: ./backend/scripts/dev_up.sh
```

In a second terminal, start the frontend:
```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

---

## Manual Step-by-Step Setup (Fallback)

If you prefer to run each piece individually:

### 1. Start PostgreSQL and Redis

```bash
docker compose up -d postgres redis
```

The default development connection is `postgresql+asyncpg://kmrl:kmrl@localhost:5432/kmrl_portal`. No real credentials are stored in this repository.

### 2. Configure and start the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload --port 8000
```

Once the API server is up, seed the full demo document corpus (in another terminal or after starting the server):
```bash
python scripts/seed_demo_corpus.py
```

The health endpoint is `GET http://localhost:8000/api/v1/health`. FastAPI documentation is available at `http://localhost:8000/api/v1/docs`.

### 3. Start the Celery worker

In another terminal, with the backend virtual environment active and Redis running:

```bash
cd backend
source .venv/bin/activate
celery -A app.jobs.celery_app.celery_app worker --loglevel=INFO
```

The placeholder task can be dispatched from a Python shell with `from app.jobs.ping import ping_job; ping_job.delay()`. It returns a JSON result containing `pong` and an ISO timestamp.

### 4. Start the frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open `http://localhost:5173`. The root route is the protected-workspace shell; `/login` is the public authentication route.


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

## Phase 3 authentication and RBAC

Phase 3 adds demo-friendly JWT authentication under `/api/v1/auth`. The login screen loads seeded users from `/api/v1/auth/demo-users`; use the clearly labeled **DEMO LOGIN** picker with the password `demo-password`. The token embeds the user ID, name, email, role, department ID, and department name. The frontend stores the token only for the local demo session and provides a logout menu.

Protected RBAC examples are available under `/api/v1/rbac`: administrator user management, department queue, executive summary, reviewer workspace, audit log, and authenticated identity. Unauthorized roles receive HTTP 403. Each seeded role lands on a different workspace view and the top navigation displays the current name, role, and department.

Set `JWT_SECRET` in `.env` to a long random value for any deployment beyond the local synthetic demo. The default value in the example configuration is intentionally a placeholder.

## Phase 4 document repository and OCR pipeline

Phase 4 adds protected upload and repository endpoints under `/api/v1/documents`. The upload endpoint accepts PDF, image, and text files, validates extension, MIME type, and the 25 MB size limit, rejects duplicate SHA-256 hashes, persists the original under the local demo object-storage directory, creates the document/version/file records, and returns HTTP 202 after enqueueing OCR.

Run the worker alongside the API with:

```bash
celery -A app.jobs.celery_app.celery_app worker --loglevel=INFO --pool=solo
```

The worker transitions versions through `queued`, `processing`, and `review_ready` (or `failed`) and stores page-level OCR text and confidence in `pages`. PDFs use `pdftotext -layout` where available; text files are read directly; images use Tesseract where available. Low-confidence pages are preserved and explicitly flagged rather than hidden.

The frontend’s **Documents** workspace provides drag-and-drop/file-picker upload, client-side validation feedback, searchable and status-filterable repository rows, status badges, source opening, page navigation, original-file viewing, OCR text, confidence percentages, and the amber “Low OCR confidence — needs review” warning. Every source view carries the required synthetic-data watermark.

## Phase 5 AI intelligence pipeline

After OCR completes, the worker runs the strict intelligence pipeline. Its Pydantic contracts are defined in `backend/app/schemas/intelligence.py` with `extra="forbid"`, fixed document-type and reason-code enums, bounded confidence values, page/character source spans, and explicit deadline states: `found`, `no_deadline_found`, or `ambiguous`. Malformed structured output is rejected rather than silently persisted.

The production integration can call the built-in OpenAI-compatible proxy with `INTELLIGENCE_LLM_ENABLED=true` and the `gpt-5-mini` model. The request uses strict JSON Schema output and treats OCR text as untrusted data. For the synthetic hackathon demo, the default is deterministic, schema-validated extraction so the portal remains runnable without external credentials; it covers circular classification, dates, departments, assets, locations, identifiers, monetary references, obligations, deadlines, summaries, priorities, reason codes, and routing recommendations.

The service persists fields into `extracted_facts` with confidence, reviewer state, and source spans, and creates proposed `actions` and elevated `alerts` when priority signals require them. The protected endpoint `/api/v1/documents/{document_id}/intelligence` returns the Intelligence Card. Reviewers, Document Administrators, and System Administrators can correct individual fields through `/intelligence/corrections`; each correction updates reviewer state to `corrected` and appends a row to `feedback`. The UI labels each value as **AI-suggested** or **human-entered**, shows confidence badges and reason codes, and provides a source link for each cited field.

## Phase 6 source-grounded RAG assistant

Phase 6 adds the protected `POST /api/v1/search/ask` endpoint and an **Ask portal** workspace. After OCR and intelligence processing, approved document pages are split into overlapping chunks. Each chunk is stored in the `chunks` table with a deterministic demo embedding reference and an `access_scope` containing role, department, and sensitivity constraints.

Retrieval combines lexical keyword scoring with deterministic vector similarity. Access filtering is applied before candidate chunks are returned to the answer stage: administrators, document administrators, reviewers, and auditors can inspect all approved demo evidence; department users are restricted to their department scope; and executive viewers are restricted to public/internal sensitivity. The answer stage requires meaningful lexical evidence in addition to vector ranking, and returns exactly `Information not available in the approved documents` when the evidence threshold is not met.

Every non-refusal answer includes at least one citation containing the document title, version, page number, chunk ID, quoted evidence, and an original-source URL. The frontend displays inline citation markers, a citations panel, Open original links, and the disclaimer **AI-generated answer — verify against source**. The UI includes the required brake-inspection demo question and a deliberately unanswerable cafeteria-menu question.

Each RAG question, answer/refusal state, citation set, and integrity hash is appended to `audit_events.detail` by the backend. The audit payload migration is `0003_rag_audit_detail`. The local verification script is `backend/scripts/verify_rag.py`.

## Phase 7 Alert Center and Action Center

Phase 7 adds protected workflow APIs under `/api/v1/alerts` and `/api/v1/actions`. AI-generated alerts now carry a title, priority, visible reason codes, suggested department, suggested action, deadline, source excerpt, reviewer metadata, and an enforced lifecycle: `draft → needs_review → approved → assigned → acknowledged → in_progress → completed → verified_closed` (or `rejected`). The backend rejects invalid skips; in particular, a Critical alert cannot move to `approved` unless it is already in `needs_review` and the actor is a Reviewer or administrator.

The Alert Center supports priority and status filters, reviewer approval/rejection, field edits that are captured in `feedback` with before/after values, Quick Share of only the minimum excerpt/summary/action/deadline, and conversion of approved alerts into actions. Quick Share is intentionally an in-app routing operation for the MVP; it does not send external notifications.

The Action Center supports create, list, read, update, and safe-delete operations. Safe delete is implemented as a `rejected` soft-delete so the append-only action timeline is preserved. Action statuses include `draft`, `open`, `acknowledged`, `in_progress`, `blocked`, `overdue`, `completed`, `closed`, and `rejected`. Owners can acknowledge, update, and complete their actions with evidence; reviewers can verify and close them. Every transition and comment writes an `action_events` row, and application-layer guards prevent action-event updates and deletes. Overdue actions are visually flagged in-app only; there is no autonomous disciplinary or external notification automation.

The reusable frontend timeline component shows each action event, actor event type, timestamp, and transition detail. The end-to-end workflow check is `backend/scripts/verify_workflows.py`, and the schema changes are in Alembic revision `0004_phase7_workflows`.

## Phase 8 document version comparison

Phase 8 adds the protected `/api/v1/comparisons` API and the **What’s Changed?** workspace. When a new file is uploaded with a versioned title such as `Maintenance Manual V2` or `Maintenance Manual V3`, the upload flow normalizes both titles to one document, preserves immutable version rows, and allocates the first unused version label. After OCR, the worker compares the new version with the previous version of the same document.

The comparator aligns non-empty page paragraphs and stores additions, deletions, and modifications in `changes`. Each change retains old and new source spans with page numbers and quoted text, plus a plain-language interpretation, affected department, priority, impact, and required action. The comparison UI renders aligned old/new text panes, expandable change cards, source links, impact metadata, and a **Convert to reviewable action** button. Conversion creates a Draft Action Center candidate with comparison and source-span references; it is never auto-approved.

The schema migration is `0005_phase8_comparison_fields`. The synthetic fixtures are generated by `backend/scripts/create_synthetic_manual_versions.py`, and the end-to-end verification is `backend/scripts/verify_comparison.py`. The verification asserts exactly three V2-to-V3 changes: brake inspection frequency, revised checklist, and deadline change.
