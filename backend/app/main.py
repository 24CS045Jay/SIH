from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes.admin import router as admin_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.audit import router as audit_router
from app.api.routes.auth import router as auth_router
from app.api.routes.comparisons import router as comparisons_router
from app.api.routes.documents import router as documents_router
from app.api.routes.events import router as events_router
from app.api.routes.health import router as health_router
from app.api.routes.intelligence import router as intelligence_router
from app.api.routes.rbac import router as rbac_router
from app.api.routes.search import router as search_router
from app.api.routes.workflows import router as workflows_router
from app.core.config import get_settings
from app.core.logging import RequestIdMiddleware, configure_logging
from app.db.session import engine

# Configure structured logging
configure_logging()
logger = logging.getLogger("app.startup")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup self-check: ping Postgres database
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection established successfully on startup.")
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "\n" + "=" * 78 + "\n"
            "⚠️  STARTUP WARNING: POSTGRES DATABASE UNREACHABLE!\n"
            "FastAPI started, but failed to connect to PostgreSQL.\n"
            f"Configured Database URL: {settings.database_url}\n"
            f"Connection Error: {exc}\n"
            "Action required:\n"
            "  1. Start Postgres: `docker compose up -d postgres`\n"
            "  2. Apply migrations: `alembic upgrade head`\n"
            "  3. Seed demo users: `python scripts/seed.py`\n"
            + "=" * 78
        )
    yield
    await engine.dispose()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)


app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_v1 = FastAPI(openapi_url="/openapi.json", docs_url="/docs", redoc_url="/redoc")
api_v1.include_router(health_router)
api_v1.include_router(documents_router)
api_v1.include_router(intelligence_router)
api_v1.include_router(search_router)
api_v1.include_router(workflows_router)
api_v1.include_router(comparisons_router)
api_v1.include_router(auth_router)
api_v1.include_router(rbac_router)
api_v1.include_router(events_router)
api_v1.include_router(analytics_router)
api_v1.include_router(admin_router)
api_v1.include_router(audit_router)
app.mount(settings.api_v1_prefix, api_v1)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": f"{settings.api_v1_prefix}/docs"}
