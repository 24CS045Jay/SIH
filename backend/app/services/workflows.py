from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models import Action, ActionEvent, ActionEventType, ActionPriority, ActionStatus, Alert, AlertStatus, Assignment, Role, User

ALERT_FLOW = {
    AlertStatus.DRAFT: {AlertStatus.NEEDS_REVIEW},
    AlertStatus.NEEDS_REVIEW: {AlertStatus.APPROVED, AlertStatus.REJECTED},
    AlertStatus.APPROVED: {AlertStatus.ASSIGNED},
    AlertStatus.ASSIGNED: {AlertStatus.ACKNOWLEDGED},
    AlertStatus.ACKNOWLEDGED: {AlertStatus.IN_PROGRESS},
    AlertStatus.IN_PROGRESS: {AlertStatus.COMPLETED},
    AlertStatus.COMPLETED: {AlertStatus.VERIFIED_CLOSED},
    AlertStatus.VERIFIED_CLOSED: set(),
    AlertStatus.REJECTED: set(),
}
ACTION_FLOW = {
    ActionStatus.DRAFT: {ActionStatus.OPEN, ActionStatus.REJECTED},
    ActionStatus.OPEN: {ActionStatus.ACKNOWLEDGED, ActionStatus.IN_PROGRESS, ActionStatus.OVERDUE, ActionStatus.REJECTED},
    ActionStatus.ACKNOWLEDGED: {ActionStatus.IN_PROGRESS, ActionStatus.OVERDUE},
    ActionStatus.IN_PROGRESS: {ActionStatus.BLOCKED, ActionStatus.COMPLETED, ActionStatus.OVERDUE},
    ActionStatus.BLOCKED: {ActionStatus.IN_PROGRESS, ActionStatus.REJECTED},
    ActionStatus.OVERDUE: {ActionStatus.ACKNOWLEDGED, ActionStatus.IN_PROGRESS, ActionStatus.COMPLETED},
    ActionStatus.COMPLETED: {ActionStatus.CLOSED},
    ActionStatus.CLOSED: set(),
    ActionStatus.REJECTED: set(),
    ActionStatus.PROPOSED: {ActionStatus.OPEN, ActionStatus.REJECTED},
    ActionStatus.PENDING_APPROVAL: {ActionStatus.OPEN, ActionStatus.REJECTED},
    ActionStatus.ASSIGNED: {ActionStatus.ACKNOWLEDGED, ActionStatus.IN_PROGRESS},
    ActionStatus.CANCELLED: set(),
}


def reviewer_role(role: str) -> bool:
    return role in {Role.SYSTEM_ADMINISTRATOR.value, Role.DOCUMENT_ADMINISTRATOR.value, Role.REVIEWER.value}


def ensure_alert_transition(alert: Alert, target: AlertStatus, actor: dict) -> None:
    if target not in ALERT_FLOW.get(alert.status, set()):
        raise HTTPException(status_code=409, detail=f"Invalid alert transition: {alert.status.value} -> {target.value}")
    if target == AlertStatus.APPROVED and not reviewer_role(actor["role"]):
        raise HTTPException(status_code=403, detail="Only a Reviewer or administrator can approve an alert")
    if alert.priority == ActionPriority.CRITICAL and target == AlertStatus.APPROVED and alert.status != AlertStatus.NEEDS_REVIEW:
        raise HTTPException(status_code=409, detail="Critical alerts must pass needs_review before approval")


def ensure_action_transition(action: Action, target: ActionStatus, actor: dict) -> None:
    if target not in ACTION_FLOW.get(action.status, set()):
        raise HTTPException(status_code=409, detail=f"Invalid action transition: {action.status.value} -> {target.value}")
    if target == ActionStatus.CLOSED and not reviewer_role(actor["role"]):
        raise HTTPException(status_code=403, detail="Only a Reviewer or administrator can verify and close an action")
    if target in {ActionStatus.ACKNOWLEDGED, ActionStatus.IN_PROGRESS, ActionStatus.COMPLETED} and action.owner_id and str(action.owner_id) != actor["sub"] and not reviewer_role(actor["role"]):
        raise HTTPException(status_code=403, detail="Only the action owner or a reviewer can update this action")


def event(action: Action, actor_id: UUID, event_type: ActionEventType, detail: dict) -> ActionEvent:
    return ActionEvent(action=action, actor_id=actor_id, event_type=event_type, detail=detail)


async def mark_overdue(action: Action, session: AsyncSession, actor_id: UUID) -> None:
    if action.due_at and action.due_at < datetime.now(timezone.utc) and action.status in {ActionStatus.OPEN, ActionStatus.ACKNOWLEDGED, ActionStatus.IN_PROGRESS}:
        previous = action.status.value
        action.status = ActionStatus.OVERDUE
        session.add(event(action, actor_id, ActionEventType.STATUS_CHANGED, {"from": previous, "to": ActionStatus.OVERDUE.value, "rule": "in-app overdue flag"}))
