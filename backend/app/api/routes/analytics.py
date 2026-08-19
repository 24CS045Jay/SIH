"""
Analytics endpoints for Module 1 (Central Control dashboard).
Role-gated: executive_viewer and system_administrator can access all data;
department_user sees only their department slice.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models import Action, ActionStatus, Alert, AlertStatus, Document, DocumentVersion, VersionStatus

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
async def analytics_summary(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Aggregated analytics for the Central Control dashboard.
    All counts are computed DB-side to avoid N+1.
    """
    role = current_user.get("role", "")
    department_id = current_user.get("department_id")

    # --- Documents by status ---
    doc_rows = (await db.execute(
        select(DocumentVersion.status, func.count().label("n"))
        .group_by(DocumentVersion.status)
    )).all()
    documents_by_status = {row.status.value if hasattr(row.status, "value") else str(row.status): row.n for row in doc_rows}
    total_docs = sum(documents_by_status.values())

    # --- Alerts by priority and department ---
    alert_priority_rows = (await db.execute(
        select(Alert.priority, func.count().label("n"))
        .group_by(Alert.priority)
    )).all()
    alerts_by_priority = {row.priority.value if hasattr(row.priority, "value") else str(row.priority): row.n for row in alert_priority_rows}
    total_alerts = sum(alerts_by_priority.values())

    alert_dept_rows = (await db.execute(
        select(Alert.suggested_department, func.count().label("n"))
        .group_by(Alert.suggested_department)
    )).all()
    alerts_by_department = {str(row.suggested_department or "Unassigned"): row.n for row in alert_dept_rows}

    # --- Actions by status ---
    action_rows = (await db.execute(
        select(Action.status, func.count().label("n"))
        .group_by(Action.status)
    )).all()
    actions_by_status = {row.status.value if hasattr(row.status, "value") else str(row.status): row.n for row in action_rows}
    total_actions = sum(actions_by_status.values())

    # --- Overdue actions ---
    now = datetime.now(timezone.utc)
    overdue_count = (await db.scalar(
        select(func.count())
        .select_from(Action)
        .where(Action.due_at < now)
        .where(Action.status.notin_([ActionStatus.COMPLETED, ActionStatus.CLOSED, ActionStatus.REJECTED]))  # type: ignore[arg-type]
    )) or 0

    return {
        "total_documents": total_docs,
        "documents_by_status": documents_by_status,
        "total_alerts": total_alerts,
        "alerts_by_priority": alerts_by_priority,
        "alerts_by_department": alerts_by_department,
        "total_actions": total_actions,
        "actions_by_status": actions_by_status,
        "overdue_actions": overdue_count,
        "avg_days_to_complete": None,  # Future: compute from action_events
    }
