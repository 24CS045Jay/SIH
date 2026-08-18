from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import require_roles
from app.db.session import get_db
from app.models import AuditEvent, Role

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/events")
async def browse_audit_events(
    search: str | None = Query(default=None, max_length=120),
    event_type: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(require_roles(Role.AUDITOR, Role.SYSTEM_ADMINISTRATOR)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(AuditEvent).order_by(AuditEvent.timestamp.desc()).offset(offset).limit(limit)
    if event_type:
        query = query.where(AuditEvent.event_type == event_type)
    if search:
        query = query.where(AuditEvent.event_type.ilike(f"%{search}%"))
    rows = (await db.execute(query)).scalars().all()
    return {
        "read_only": True,
        "items": [{
            "id": str(item.id), "actor_id": str(item.actor_id) if item.actor_id else None,
            "event_type": item.event_type, "object_type": item.object_type, "object_id": str(item.object_id),
            "timestamp": item.timestamp.isoformat(), "hash": item.hash, "detail": item.detail,
        } for item in rows],
        "limit": limit, "offset": offset,
    }


@router.get("/governance")
async def governance_settings(current_user: dict = Depends(require_roles(Role.AUDITOR, Role.SYSTEM_ADMINISTRATOR, Role.DOCUMENT_ADMINISTRATOR))) -> dict:
    settings = get_settings()
    return {
        "demo_purge_after_judging": settings.demo_purge_after_judging,
        "destructive_action_enabled": False,
        "message": "Governance placeholder only; no purge is executed by this endpoint.",
    }
