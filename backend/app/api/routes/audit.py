"""
Audit log viewer endpoints for Module 6.
Accessible to: system_administrator and auditor roles.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_roles
from app.db.session import get_db
from app.models import AuditEvent, Role

router = APIRouter(prefix="/audit", tags=["audit"])

_audit_roles = require_roles(Role.SYSTEM_ADMINISTRATOR, Role.AUDITOR)


@router.get("/events")
async def list_audit_events(
    event_type: str | None = Query(None),
    actor_id: UUID | None = Query(None),
    object_type: str | None = Query(None),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    current_user: dict = Depends(_audit_roles),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    query = select(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(limit)

    if event_type:
        query = query.where(AuditEvent.event_type == event_type)
    if actor_id:
        query = query.where(AuditEvent.actor_id == actor_id)
    if object_type:
        query = query.where(AuditEvent.object_type == object_type)
    if from_date:
        query = query.where(AuditEvent.timestamp >= from_date)
    if to_date:
        query = query.where(AuditEvent.timestamp <= to_date)

    rows = (await db.execute(query)).scalars().all()
    return [
        {
            "id": str(e.id),
            "actor_id": str(e.actor_id) if e.actor_id else None,
            "event_type": e.event_type,
            "object_type": e.object_type,
            "object_id": str(e.object_id),
            "timestamp": e.timestamp.isoformat(),
            "hash": e.hash,
            "detail": e.detail,
        }
        for e in rows
    ]
