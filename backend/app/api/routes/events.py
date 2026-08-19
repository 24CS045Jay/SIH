"""
Server-Sent Events (SSE) stream for real-time alert notifications.
No WebSocket dependency — uses SSE which works through standard HTTP.

The frontend connects via EventSource and receives new Critical/High alerts
as they arrive. This does NOT auto-approve anything — it only surfaces items
for human review.

Token auth: since EventSource cannot set Authorization headers, the JWT is
passed as a `?token=...` query parameter and validated here.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import get_current_user
from app.db.session import AsyncSessionLocal
from app.models import Alert, AlertStatus, DocumentVersion

import jwt

router = APIRouter(prefix="/events", tags=["real-time"])


def _validate_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if not payload.get("sub") or not payload.get("role"):
            return None
        return payload
    except jwt.PyJWTError:
        return None


async def _alert_stream(user: dict):
    """
    Generator that polls for new DRAFT alerts every 15 seconds and yields them as SSE events.
    Only Critical and High priority alerts are emitted to avoid notification fatigue.
    """
    seen: set[str] = set()
    while True:
        try:
            async with AsyncSessionLocal() as db:
                rows = (
                    await db.execute(
                        select(Alert, DocumentVersion)
                        .join(DocumentVersion, Alert.source_version_id == DocumentVersion.id)
                        .where(Alert.status == AlertStatus.DRAFT)
                        .where(Alert.priority.in_(["critical", "high"]))
                        .order_by(Alert.id.desc())
                        .limit(20)
                    )
                ).all()

            for alert, version in rows:
                alert_id = str(alert.id)
                if alert_id in seen:
                    continue
                seen.add(alert_id)
                payload = {
                    "id": alert_id,
                    "title": alert.title,
                    "priority": alert.priority.value,
                    "reason_codes": alert.reason_codes or [],
                    "suggested_department": alert.suggested_department,
                    "suggested_action": alert.suggested_action,
                    "deadline": alert.deadline.isoformat() if alert.deadline else None,
                    "source_excerpt": alert.source_excerpt,
                    "source_version_id": str(alert.source_version_id),
                    "status": alert.status.value,
                    "routing_state": alert.routing_state.value,
                    "assigned_user_id": None,
                    "document_title": None,
                }
                yield f"id: {alert_id}\ndata: {json.dumps(payload)}\n\n"
        except Exception:  # noqa: BLE001
            # Log but don't crash the stream
            pass
        await asyncio.sleep(15)


@router.get("/alerts")
async def alert_events(token: str = Query(..., description="JWT bearer token")) -> StreamingResponse:
    """
    SSE stream of new Critical/High draft alerts.
    Authenticate with ?token=<jwt>
    """
    user = _validate_token(token)
    if user is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return StreamingResponse(
        _alert_stream(user),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
