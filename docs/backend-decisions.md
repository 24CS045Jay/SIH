# Backend decisions

- **PostgreSQL-only runtime:** development, CI, demo, and deployment use the same `postgresql+asyncpg` connection pattern. This avoids SQLite drift and keeps the SQLAlchemy/Alembic behavior consistent with the production schema.
- **Redis-backed jobs:** OCR and post-processing remain asynchronous through Celery and Redis so upload requests stay responsive and failures are visible in persisted processing diagnostics.
- **Source-grounded RAG:** chunks remain the authorization boundary. Retrieval filters by access scope before reranking and final citation validation rejects unsupported answers.
- **Provider fallback:** optional OpenAI providers can improve embeddings and intelligence extraction, but credential absence or invalid optional credentials must not fail OCR. Deterministic local embeddings and extractive generation are the safe demo defaults.
- **Operational diagnostics:** `/api/v1/health` checks backend/database reachability; `/api/v1/health/detailed` additionally checks Redis and storage writability. Diagnostics never return secrets or full OCR/document text.
- **Auditability:** document versions are immutable, audit events are append-only, and workflow state changes remain server-authorized.
- **Deployment boundary:** Vercel serves the static React frontend; Render runs the Dockerized FastAPI API and Celery worker with managed Postgres and Redis.
