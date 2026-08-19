# KMRL Portal Container Deployment

This deployment path runs the complete institute-round demo stack with Docker Compose: PostgreSQL, Redis, the FastAPI API, the Celery OCR/intelligence worker, and the React/Nginx frontend. It is designed for a clean Linux machine with Docker Engine and the Compose plugin installed. No production secrets are included in this repository.

## Bring the stack up from zero

From the repository root, copy the templates and replace the demo placeholders locally:

```bash
cp .env.example .env
cp backend/.env.example backend/.env
```

Set a long random `JWT_SECRET` in `backend/.env`. Keep `OPENAI_API_KEY` empty for the deterministic demo path, or set it only in the untracked local environment file if the LLM-backed intelligence path is intentionally enabled. The local storage volume is the default object-storage substitute for the hackathon. `OBJECT_STORAGE_ENDPOINT`, `OBJECT_STORAGE_BUCKET`, `OBJECT_STORAGE_ACCESS_KEY`, and `OBJECT_STORAGE_SECRET_KEY` are present as explicit governance placeholders for a later object-storage deployment.

Build and start the services:

```bash
docker compose up -d --build
```

The backend container runs `alembic upgrade head` before starting FastAPI. The frontend is available at `http://localhost:8080`, the API is proxied at `http://localhost:8080/api/v1`, and the direct API port is `http://localhost:8000`. Redis and PostgreSQL are internal compose services. The worker shares the backend image and consumes the OCR queue.

Seed the reference users and the seven synthetic documents through the normal API pipeline. The seed command must run from the backend container so it can reach the compose service name and shared storage volume:

```bash
docker compose exec backend python scripts/seed.py
docker compose exec backend python scripts/generate_demo_corpus.py
docker compose exec backend python scripts/seed_demo_corpus.py
```

The corpus seed prints a readiness report. It should show seven review-ready documents, one low-confidence page per document, RAG citations, and exactly three Maintenance Manual V2-to-V3 changes. For a quick rehearsal reset, use:

```bash
docker compose exec backend python scripts/reset_demo_environment.py --yes
```

The reset wrapper is also available as `docker compose exec backend scripts/reset_demo.sh`.

## Health and uptime checks

Run the basic stack check before presenting:

```bash
curl -fsS http://localhost:8080/health
curl -fsS http://localhost:8080/api/v1/health

docker compose ps
docker compose logs --tail=80 backend worker frontend
```

All compose services should be running; the `backend` and `frontend` health checks should report healthy. The API responses include the service name, environment, and timestamp where applicable. A failed worker does not make the HTTP health endpoint fail, so inspect the worker log before an upload demo.

## Judge-accessible deployment options

For a judge-accessible URL, run this same stack on a single Linux VM with Docker installed and expose only port 80/443 through the VM firewall or a reverse proxy. Point the judge URL at the frontend container; Nginx serves the React application and proxies `/api/` to FastAPI. For a presentation with no external hosting budget or credentials, run the compose stack on the presenter’s laptop and share the URL from the same local network. The application is intentionally kept as a single-origin stack so the browser does not need a separate API URL.

## Final smoke test

With the stack running and the corpus seeded, run the Phase 13 automated checks inside the backend container:

```bash
docker compose exec backend python -m unittest discover -s tests -p 'test_*.py'
docker compose exec backend env KMRL_API_BASE=http://frontend/api/v1 python scripts/test_core_loop_e2e.py
docker compose exec backend env KMRL_API_BASE=http://frontend/api/v1 python scripts/evaluate_known_answers.py
```

The integration smoke test must finish with a closed action and audit event types including `view`, `edit`, `share`, and `status_change`. The known-answer evaluation must report seven questions, source citations for supported questions, and the exact refusal `Information not available in the approved documents` for the unsupported question.

## Troubleshooting

If migrations fail, inspect `docker compose logs backend` and verify that the database health check is healthy before restarting the backend. If uploads remain queued, inspect `docker compose logs worker`; the worker must use the same `kmrl_storage` volume and Redis URLs as the API. If the frontend loads but API calls fail, confirm that the Nginx proxy is using `/api/` and that the backend is healthy. Do not put real keys in the repository or in a committed Compose file.

## Vercel frontend and Render backend

The repository also includes `frontend/vercel.json` and `render.yaml` for a split deployment. In Vercel, set the project root directory to `frontend/`, use the Vite framework preset, and configure `VITE_API_BASE_URL` to the public Render API URL ending in `/api/v1`. The Vercel rewrite keeps client-side navigation working on refresh.

In Render, create the services described by `render.yaml`: the Dockerized FastAPI web service, the Dockerized Celery worker, the managed PostgreSQL database, and the Redis service. Set `CORS_ORIGINS` on the API to the exact Vercel origin. Render uses `/api/v1/health` as the web-service health check and generated values for `JWT_SECRET`; no secrets belong in Git.

Before a judge-facing rehearsal, run both the basic and detailed checks:

```bash
curl -fsS https://<render-api>/api/v1/health
curl -fsS https://<render-api>/api/v1/health/detailed
curl -fsS https://<render-api>/api/v1/auth/demo-users
```

The detailed response reports only `database`, `redis`, and `storage` states. It never includes connection strings, credentials, JWT secrets, or document text.
