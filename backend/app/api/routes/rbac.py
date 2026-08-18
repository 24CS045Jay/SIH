from fastapi import APIRouter, Depends

from app.core.security import get_current_user, require_roles
from app.models import Role

router = APIRouter(prefix="/rbac", tags=["authorization"])


@router.get("/admin/users")
async def admin_users(current_user: dict = Depends(require_roles(Role.SYSTEM_ADMINISTRATOR, Role.DOCUMENT_ADMINISTRATOR))) -> dict:
    return {"view": "user-management", "message": "Authorized administrator view", "user": current_user["name"]}


@router.get("/department/queue")
async def department_queue(current_user: dict = Depends(require_roles(Role.DEPARTMENT_USER, Role.REVIEWER, Role.DOCUMENT_ADMINISTRATOR, Role.SYSTEM_ADMINISTRATOR))) -> dict:
    return {"view": "department-queue", "department": current_user.get("department"), "user": current_user["name"]}


@router.get("/executive/summary")
async def executive_summary(current_user: dict = Depends(require_roles(Role.EXECUTIVE_VIEWER, Role.SYSTEM_ADMINISTRATOR))) -> dict:
    return {"view": "executive-summary", "user": current_user["name"]}


@router.get("/audit/log")
async def audit_log(current_user: dict = Depends(require_roles(Role.AUDITOR, Role.SYSTEM_ADMINISTRATOR))) -> dict:
    return {"view": "audit-log", "message": "Append-only audit view", "user": current_user["name"]}


@router.get("/review/workspace")
async def reviewer_workspace(current_user: dict = Depends(require_roles(Role.REVIEWER, Role.SYSTEM_ADMINISTRATOR, Role.DOCUMENT_ADMINISTRATOR))) -> dict:
    return {"view": "review-workspace", "user": current_user["name"]}


@router.get("/identity")
async def identity(current_user: dict = Depends(get_current_user)) -> dict:
    return {"view": "identity", "claims": current_user}
