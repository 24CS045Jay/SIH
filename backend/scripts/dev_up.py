#!/usr/bin/env python3
"""
Single-command local bootstrap for KMRL Document Intelligence Portal.

Executes in order:
1. Start PostgreSQL and Redis via docker compose.
2. Wait for PostgreSQL to accept connections (readiness loop).
3. Apply database migrations (alembic upgrade head).
4. Seed base departments and demo RBAC users (python scripts/seed.py).
5. Start Uvicorn and seed full demo document corpus (python scripts/seed_demo_corpus.py).
6. Start Celery worker and Uvicorn dev server concurrently.
"""

from __future__ import annotations

import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]


def log(msg: str) -> None:
    print(f"\n\033[1;34m[KMRL Bootstrap]\033[0m {msg}", flush=True)


def log_success(msg: str) -> None:
    print(f"\033[1;32m✓\033[0m {msg}", flush=True)


def log_warn(msg: str) -> None:
    print(f"\033[1;33m!\033[0m {msg}", flush=True)


def run_cmd(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    cwd_path = cwd or BACKEND_DIR
    return subprocess.run(cmd, cwd=str(cwd_path), check=check)


def wait_for_postgres(host: str = "127.0.0.1", port: int = 5432, timeout_seconds: int = 45) -> bool:
    log(f"Waiting for PostgreSQL to accept connections at {host}:{port}...")
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        try:
            with socket.create_connection((host, port), timeout=1.5):
                log_success("PostgreSQL is ready and accepting connections.")
                return True
        except (OSError, ConnectionRefusedError):
            time.sleep(0.8)
    raise TimeoutError(f"PostgreSQL did not become ready within {timeout_seconds} seconds.")


def wait_for_api(url: str = "http://127.0.0.1:8000/api/v1/health", timeout_seconds: int = 30) -> bool:
    log(f"Waiting for backend API to be ready at {url}...")
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        try:
            with urlopen(url, timeout=1.5) as resp:
                if resp.status == 200:
                    log_success("Backend API is responsive.")
                    return True
        except Exception:
            time.sleep(0.5)
    raise TimeoutError(f"Backend API did not become ready within {timeout_seconds} seconds.")


def main() -> None:
    log("Starting KMRL local services bootstrap...")

    # 1. Start Docker containers
    log("Step 1/5: Starting PostgreSQL and Redis via Docker Compose...")
    try:
        run_cmd(["docker", "compose", "up", "-d", "postgres", "redis"], cwd=ROOT_DIR)
        log_success("Docker containers launched.")
    except Exception as exc:
        log_warn(f"Docker Compose command failed ({exc}). Assuming services are already running locally.")

    # 2. Wait for Postgres readiness
    log("Step 2/5: Verifying database readiness...")
    wait_for_postgres()

    # 3. Run Alembic migrations
    log("Step 3/5: Applying database migrations (`alembic upgrade head`)...")
    run_cmd([sys.executable, "-m", "alembic", "upgrade", "head"])
    log_success("Database schema is up to date.")

    # 4. Seed demo users and initial documents
    log("Step 4/5: Seeding synthetic departments and demo RBAC users (`python scripts/seed.py`)...")
    run_cmd([sys.executable, "scripts/seed.py"])
    log_success("Demo users seeded.")

    # 5. Start Uvicorn in background temporarily to seed demo corpus if needed
    log("Step 5/5: Starting Uvicorn API server & seeding demo corpus...")
    uvicorn_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=str(BACKEND_DIR),
    )

    try:
        wait_for_api()
        log("Seeding full demo document corpus (`python scripts/seed_demo_corpus.py`)...")
        run_cmd([sys.executable, "scripts/seed_demo_corpus.py"])
        log_success("Demo document corpus seeded successfully.")
    except Exception as exc:
        log_warn(f"Demo corpus seeding warning: {exc}")

    # Start Celery worker alongside Uvicorn
    celery_pool = ["--pool=solo"] if os.name == "nt" else []
    log("Starting Celery worker...")
    celery_process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "celery",
            "-A",
            "app.jobs.celery_app.celery_app",
            "worker",
            "--loglevel=INFO",
            *celery_pool,
        ],
        cwd=str(BACKEND_DIR),
    )

    log_success("All KMRL backend services are running!")
    print("\n" + "=" * 60)
    print("  KMRL Backend API: http://localhost:8000/api/v1")
    print("  API Docs:         http://localhost:8000/api/v1/docs")
    print("  Health Probe:     http://localhost:8000/api/v1/health")
    print("=" * 60 + "\n")
    print("Press Ctrl+C to stop backend services.\n")

    try:
        uvicorn_process.wait()
    except KeyboardInterrupt:
        log("Shutting down KMRL services...")
        uvicorn_process.terminate()
        celery_process.terminate()
        try:
            uvicorn_process.wait(timeout=5)
            celery_process.wait(timeout=5)
        except Exception:
            uvicorn_process.kill()
            celery_process.kill()
        log_success("KMRL backend stopped cleanly.")


if __name__ == "__main__":
    main()
