"""
Admin endpoints for Module 6 — Administration & Governance.
All routes require system_administrator role except where noted.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import require_roles
from app.db.session import get_db
from app.models import Department, Role, User, UserStatus

router = APIRouter(prefix="/admin", tags=["administration"])

_admin_only = require_roles(Role.SYSTEM_ADMINISTRATOR)


@router.get("/departments")
async def list_departments(
    current_user: dict = Depends(require_roles(Role.SYSTEM_ADMINISTRATOR, Role.AUDITOR)),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = (await db.execute(select(Department).order_by(Department.name))).scalars().all()
    return [{"id": str(d.id), "name": d.name, "parent_id": str(d.parent_id) if d.parent_id else None} for d in rows]


@router.post("/departments", status_code=status.HTTP_201_CREATED)
async def create_department(
    name: str = Body(..., embed=True),
    parent_id: UUID | None = Body(None, embed=True),
    current_user: dict = Depends(_admin_only),
    db: AsyncSession = Depends(get_db),
) -> dict:
    existing = await db.scalar(select(Department).where(Department.name == name))
    if existing:
        raise HTTPException(status_code=409, detail="A department with this name already exists")
    dept = Department(name=name, parent_id=parent_id)
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return {"id": str(dept.id), "name": dept.name, "parent_id": str(dept.parent_id) if dept.parent_id else None}


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: UUID,
    role: str = Body(..., embed=True),
    current_user: dict = Depends(_admin_only),
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Validate role value
    valid_roles = {r.value for r in Role}
    if role not in valid_roles:
        raise HTTPException(status_code=422, detail=f"Invalid role. Must be one of: {sorted(valid_roles)}")

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Safety: prevent demoting the only system administrator
    if user.role == Role.SYSTEM_ADMINISTRATOR and role != Role.SYSTEM_ADMINISTRATOR.value:
        count = await db.scalar(
            select(User).where(User.role == Role.SYSTEM_ADMINISTRATOR).where(User.status == UserStatus.ACTIVE)
        )
        if count is not None and count <= 1:
            raise HTTPException(status_code=409, detail="Cannot demote the only system administrator")

    user.role = Role(role)
    await db.commit()
    return {"id": str(user.id), "name": user.name, "role": user.role.value, "message": "Role updated"}


@router.get("/config")
async def get_config(current_user: dict = Depends(_admin_only)) -> dict:
    """Returns non-secret configuration values for display in the admin panel."""
    settings = get_settings()
    return {
        "environment": settings.environment,
        "app_name": settings.app_name,
        "intelligence_llm_enabled": str(settings.intelligence_llm_enabled),
        "intelligence_model": settings.intelligence_model,
        "max_upload_size_mb": str(settings.max_upload_size_mb),
        "low_ocr_confidence_threshold": str(settings.low_ocr_confidence_threshold),
        "access_token_expire_minutes": str(settings.access_token_expire_minutes),
        "api_v1_prefix": settings.api_v1_prefix,
    }
