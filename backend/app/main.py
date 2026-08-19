from fastapi import FastAPI, Request
from uuid import UUID, uuid4
import hashlib
import json
import logging
import traceback
import jwt
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("kmrl_portal")

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
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url=f"{settings.api_v1_prefix}/docs",
    redoc_url=f"{settings.api_v1_prefix}/redoc",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
)

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


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    trace_id = getattr(request.state, "trace_id", "unknown")
    logger.error(
        "Unhandled exception on %s %s [trace_id=%s]:\n%s",
        request.method, request.url.path, trace_id, traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"An unexpected server error occurred ({exc.__class__.__name__}). "
                      f"Reference trace ID: {trace_id}. Check backend logs for the full traceback.",
            "trace_id": trace_id,
        },
    )

api_v1_prefix = settings.api_v1_prefix
app.include_router(health_router, prefix=api_v1_prefix)
app.include_router(documents_router, prefix=api_v1_prefix)
app.include_router(intelligence_router, prefix=api_v1_prefix)
app.include_router(search_router, prefix=api_v1_prefix)
app.include_router(workflows_router, prefix=api_v1_prefix)
app.include_router(comparisons_router, prefix=api_v1_prefix)
app.include_router(auth_router, prefix=api_v1_prefix)
app.include_router(rbac_router, prefix=api_v1_prefix)
app.include_router(dashboard_router, prefix=api_v1_prefix)
app.include_router(audit_router, prefix=api_v1_prefix)


@app.on_event("startup")
async def verify_critical_routes() -> None:
    """Fail loudly at boot if a critical route is missing instead of 404ing later at login."""
    resolved_paths = {getattr(route, "path", "") for route in app.routes}
    required = [
        f"{api_v1_prefix}/auth/demo-users",
        f"{api_v1_prefix}/auth/login",
        f"{api_v1_prefix}/health",
    ]
    missing = [path for path in required if path not in resolved_paths]
    if missing:
        print("!" * 70)
        print("STARTUP ERROR: the following required API routes did not register:")
        for path in missing:
            print(f"  - {path}")
        print("The server will start, but these endpoints will 404. Check router imports/prefixes in app/main.py.")
        print("!" * 70)
    else:
        print(f"[startup] All critical routes verified OK under prefix '{api_v1_prefix}'.")


@app.get("/health", include_in_schema=False)
async def root_health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "environment": settings.environment}

@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": f"{settings.api_v1_prefix}/docs"}
