from datetime import datetime, timezone
from fastapi import APIRouter
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
