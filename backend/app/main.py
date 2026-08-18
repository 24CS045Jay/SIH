from fastapi import FastAPI, Request
from uuid import UUID, uuid4
import hashlib
import json
import jwt
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
from app.api.routes.audit import router as audit_router
from app.core.security import get_current_user
from app.db.session import AsyncSessionLocal
from app.models import AuditEvent
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")

@app.middleware("http")
async def trace_and_audit(request: Request, call_next):
    trace_id = str(uuid4())
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["X-Trace-ID"] = trace_id
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer ") and request.url.path.startswith(settings.api_v1_prefix):
        try:
            claims = jwt.decode(authorization.split(" ", 1)[1], settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            actor_id = UUID(claims["sub"])
            path = request.url.path
            method = request.method.upper()
            if method == "GET" and path.endswith("/source"):
                event_type = "download"
            elif method == "GET":
                event_type = "view"
            elif "quick-share" in path:
                event_type = "share"
            elif "transition" in path:
                event_type = "status_change"
            elif method in {"POST", "PATCH", "PUT", "DELETE"}:
                event_type = "edit"
            else:
                event_type = "api_request"
            detail = {"method": method, "path": path, "status_code": response.status_code, "trace_id": trace_id}
            digest = hashlib.sha256(json.dumps(detail, sort_keys=True).encode()).hexdigest()
            async with AsyncSessionLocal() as session:
                session.add(AuditEvent(actor_id=actor_id, event_type=event_type, object_type="api_request", object_id=actor_id, hash=digest, detail=detail))
                await session.commit()
        except Exception:
            pass
    return response

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
api_v1.include_router(audit_router)
app.mount(settings.api_v1_prefix, api_v1)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": f"{settings.api_v1_prefix}/docs"}
