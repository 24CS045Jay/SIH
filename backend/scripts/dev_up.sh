#!/usr/bin/env bash
set -e

# ==============================================================================
# KMRL Document Intelligence & Action Portal — One-Command Local Bootstrap
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT_DIR="$(cd "$BACKEND_DIR/.." && pwd)"

echo -e "\033[1;34m[KMRL Bootstrap]\033[0m Starting local services bootstrap..."

# 1. Start Docker containers (PostgreSQL & Redis)
echo -e "\033[1;34m[KMRL Bootstrap]\033[0m Starting PostgreSQL & Redis via Docker Compose..."
cd "$ROOT_DIR"
docker compose up -d postgres redis || echo "Docker Compose warning: continuing..."

# 2. Wait for PostgreSQL readiness loop (pg_isready or Python socket probe)
echo -e "\033[1;34m[KMRL Bootstrap]\033[0m Waiting for PostgreSQL to accept connections..."
cd "$BACKEND_DIR"

RETRIES=45
until python3 -c '
import socket, sys
try:
    with socket.create_connection(("127.0.0.1", 5432), timeout=1.0):
        sys.exit(0)
except Exception:
    sys.exit(1)
' 2>/dev/null || [ $RETRIES -eq 0 ]; do
    echo "Waiting for Postgres on 127.0.0.1:5432 ($RETRIES retries remaining)..."
    sleep 1
    RETRIES=$((RETRIES-1))
done

if [ $RETRIES -eq 0 ]; then
    echo -e "\033[1;31mError:\033[0m PostgreSQL did not become ready in time."
    exit 1
fi
echo -e "\033[1;32m✓\033[0m PostgreSQL is ready."

# 3. Run Alembic migrations
echo -e "\033[1;34m[KMRL Bootstrap]\033[0m Applying database migrations (alembic upgrade head)..."
alembic upgrade head
echo -e "\033[1;32m✓\033[0m Migrations applied."

# 4. Seed demo users and base documents
echo -e "\033[1;34m[KMRL Bootstrap]\033[0m Seeding demo users and initial documents..."
python3 scripts/seed.py
echo -e "\033[1;32m✓\033[0m Demo users seeded."

# 5. Start Uvicorn in background to seed demo corpus
echo -e "\033[1;34m[KMRL Bootstrap]\033[0m Starting Uvicorn API server & seeding demo corpus..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
UVICORN_PID=$!

trap "kill $UVICORN_PID 2>/dev/null || true; exit" SIGINT SIGTERM EXIT

# Wait for API to respond
API_RETRIES=30
until python3 -c '
import urllib.request, sys
try:
    with urllib.request.urlopen("http://127.0.0.1:8000/api/v1/health", timeout=1.0) as r:
        sys.exit(0 if r.status == 200 else 1)
except Exception:
    sys.exit(1)
' 2>/dev/null || [ $API_RETRIES -eq 0 ]; do
    sleep 0.5
    API_RETRIES=$((API_RETRIES-1))
done

echo -e "\033[1;34m[KMRL Bootstrap]\033[0m Seeding full demo corpus (python scripts/seed_demo_corpus.py)..."
python3 scripts/seed_demo_corpus.py || echo "Warning: Demo corpus seeding encountered an issue."

# 6. Start Celery worker alongside Uvicorn
echo -e "\033[1;34m[KMRL Bootstrap]\033[0m Starting Celery worker..."
celery -A app.jobs.celery_app.celery_app worker --loglevel=INFO &
CELERY_PID=$!

trap "kill $UVICORN_PID $CELERY_PID 2>/dev/null || true; exit" SIGINT SIGTERM EXIT

echo -e "\033[1;32m✓\033[0m KMRL backend and worker are running!"
echo -e "API: http://localhost:8000/api/v1"
echo -e "Press Ctrl+C to stop all backend services."

wait $UVICORN_PID $CELERY_PID
