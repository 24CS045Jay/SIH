from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.documents import router as documents_router
from app.api.routes.intelligence import router as intelligence_router
from app.api.routes.search import router as search_router
from app.api.routes.workflows import router as workflows_router
from app.api.routes.comparisons import router as comparisons_router
from app.api.routes.rbac import router as rbac_router
from app.api.routes.dashboard import router as dashboard_router
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")

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
api_v1.include_router(dashboard_router)
app.mount(settings.api_v1_prefix, api_v1)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": f"{settings.api_v1_prefix}/docs"}
