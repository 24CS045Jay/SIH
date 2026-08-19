# Architecture Decision Record (ADR): Backend & Database Architecture

## 1. Single Database Standard: PostgreSQL with pgvector
* **Status**: Accepted & Implemented
* **Context**: Earlier drafts used SQLite for local prototyping, resulting in configuration drift, lack of native vector operations, and concurrency limitations.
* **Decision**: Standardize exclusively on PostgreSQL with `pgvector` across all environments (local via Docker `pgvector/pgvector:pg16`, staging/production via Render managed PostgreSQL).
* **Rationale**: Eliminates dialect-specific query branching, enables DB-side vector similarity search for RAG embeddings, and supports native UUID and JSONB operations.

## 2. Structured JSON Logging & Request ID Tracing
* **Status**: Accepted & Implemented
* **Context**: Production debugging and audit compliance require machine-readable log output and end-to-end request tracing.
* **Decision**: Adopt `python-json-logger` with a custom `RequestIdMiddleware` that tags every inbound request with a UUID `X-Request-ID` header.
* **Rationale**: Simplifies log aggregation in modern observability stacks (Datadog, CloudWatch, Render logs) and guarantees document text content remains redacted from log streams.

## 3. Server-Sent Events (SSE) for Real-Time Workflow Alerts
* **Status**: Accepted & Implemented
* **Context**: Critical and high-priority alerts need immediate notification in the browser without polling loops or full bidirectional WebSocket overhead.
* **Decision**: Implement `/api/v1/events/alerts` using HTTP Server-Sent Events (SSE) with query-token validation.
* **Rationale**: Standard HTTP compatibility through proxies and firewalls; auto-reconnect built into browser `EventSource`; unidirectional broadcast is strictly sufficient for alert notifications.

## 4. Connection Pooling & Resource Bounds
* **Status**: Accepted & Implemented
* **Context**: Free-tier cloud deployments (e.g. Render) impose strict connection and memory limits.
* **Decision**: Configure SQLAlchemy `create_async_engine` with `pool_size=5`, `max_overflow=10`, and `pool_pre_ping=True`.
* **Rationale**: Prevents connection exhaustion while maintaining responsiveness under burst traffic.

## 5. Rate Limiting Strategy
* **Status**: Accepted & Implemented
* **Context**: Public-facing demo auth and upload endpoints must be protected against brute-force and resource denial.
* **Decision**: In-process token-bucket rate limiter for `/auth/login` (10 req/min/IP) and `/documents/upload` (20 req/min/IP).
* **Rationale**: Zero external runtime dependencies required for local or single-instance deployment, with straightforward upgrade path to Redis token bucket for horizontal scaling.
