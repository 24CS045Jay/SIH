from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter
from redis.asyncio import Redis
from sqlalchemy import text
from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.schemas.health import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    settings = get_settings()
    database = "ok"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        database = "unavailable"
    return HealthResponse(
        status="ok" if database == "ok" else "degraded",
        service=settings.app_name,
        environment=settings.environment,
        database=database,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/health/detailed")
async def detailed_health() -> dict[str, object]:
    settings = get_settings()
    checks: dict[str, str] = {"database": "ok", "redis": "ok", "storage": "ok"}
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        checks["database"] = "unavailable"
    redis_client: Redis | None = None
    try:
        redis_client = Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
        await redis_client.ping()
    except Exception:
        checks["redis"] = "unavailable"
    finally:
        if redis_client is not None:
            await redis_client.aclose()
    try:
        storage = Path(settings.storage_path)
        storage.mkdir(parents=True, exist_ok=True)
        probe = storage / ".health-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except Exception:
        checks["storage"] = "unavailable"
    status = "ok" if all(value == "ok" for value in checks.values()) else "degraded"
    return {"status": status, "service": settings.app_name, "environment": settings.environment, "checks": checks, "timestamp": datetime.now(timezone.utc).isoformat()}
