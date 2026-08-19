from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import time

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine
from app.schemas.health import HealthResponse

router = APIRouter(tags=["system"])


def _check_alembic_heads(sync_conn) -> bool:
    try:
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory

        alembic_dir = Path(__file__).resolve().parents[3] / "alembic"
        script = ScriptDirectory(str(alembic_dir))
        head_revs = set(script.get_heads())

        context = MigrationContext.configure(sync_conn)
        current_revs = set(context.get_current_heads())

        return bool(head_revs and head_revs == current_revs)
    except Exception:
        return False


async def check_system_diagnostics() -> tuple[bool, bool, bool]:
    """
    Returns (database_reachable, migrations_current, demo_users_seeded).
    """
    database_reachable = False
    migrations_current = False
    demo_users_seeded = False

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            database_reachable = True

            migrations_current = await conn.run_sync(_check_alembic_heads)

            try:
                result = await conn.execute(text("SELECT count(*) FROM users"))
                count = result.scalar() or 0
                demo_users_seeded = count > 0
            except Exception:
                demo_users_seeded = False
    except Exception:
        database_reachable = False
        migrations_current = False
        demo_users_seeded = False

    return database_reachable, migrations_current, demo_users_seeded


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    settings = get_settings()
    db_ok, mig_ok, users_ok = await check_system_diagnostics()
    overall = "ok" if (db_ok and mig_ok and users_ok) else "degraded"
    return HealthResponse(
        status=overall,
        service=settings.app_name,
        environment=settings.environment,
        timestamp=datetime.now(timezone.utc),
        database_reachable=db_ok,
        migrations_current=mig_ok,
        demo_users_seeded=users_ok,
    )


@router.get("/health/detailed")
async def health_detailed() -> dict:
    """
    Detailed health probe checking DB, storage, and config.
    Used by load balancers and monitoring tools.
    """
    settings = get_settings()
    checks: dict[str, object] = {}
    overall = "ok"
    t0 = time.monotonic()

    db_ok, mig_ok, users_ok = await check_system_diagnostics()

    # Database check
    if db_ok:
        checks["database"] = {
            "status": "ok",
            "latency_ms": round((time.monotonic() - t0) * 1000, 1),
            "migrations_current": mig_ok,
            "demo_users_seeded": users_ok,
        }
        if not mig_ok or not users_ok:
            overall = "degraded"
    else:
        checks["database"] = {"status": "error", "detail": "Cannot reach database"}
        overall = "degraded"

    # Storage path check
    import os
    storage_path = settings.storage_path
    storage_ok = os.path.isdir(storage_path)
    checks["storage"] = {"status": "ok" if storage_ok else "missing", "path": storage_path}
    if not storage_ok:
        overall = "degraded"

    # Redis check (optional — if not configured, skip)
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url, socket_timeout=1)
        await r.ping()
        await r.aclose()
        checks["redis"] = {"status": "ok"}
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = {"status": "unavailable", "detail": str(exc)}
        # Redis unavailable = degraded for Celery tasks, not critical for API itself

    return {
        "status": overall,
        "service": settings.app_name,
        "environment": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database_reachable": db_ok,
        "migrations_current": mig_ok,
        "demo_users_seeded": users_ok,
        "checks": checks,
        "config": {
            "intelligence_llm_enabled": settings.intelligence_llm_enabled,
            "intelligence_model": settings.intelligence_model,
            "max_upload_size_mb": settings.max_upload_size_mb,
        },
    }

