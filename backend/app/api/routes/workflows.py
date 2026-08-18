from __future__ import annotations
import json
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.security import get_current_user, require_roles
from app.db.session import get_db
from app.models import Action, ActionEventType, ActionPriority, ActionStatus, Alert, AlertStatus, Assignment, DocumentVersion, Feedback, FeedbackReason, Role, User
from app.schemas.workflows import ActionCreateRequest, ActionEventResponse, ActionResponse, ActionTransitionRequest, ActionUpdateRequest, AlertResponse, AlertTransitionRequest, QuickShareRequest
from app.services.workflows import ACTION_FLOW, ensure_action_transition, ensure_alert_transition, event, mark_overdue

router = APIRouter(tags=["workflows"])


def user_uuid(user: dict) -> UUID: return UUID(user["sub"])


def alert_response(alert: Alert, assigned_user_id: UUID | None = None) -> AlertResponse:
    return AlertResponse(id=alert.id, title=alert.title, priority=alert.priority, reason_codes=alert.reason_codes, suggested_department=alert.suggested_department, suggested_action=alert.suggested_action, deadline=alert.deadline, source_excerpt=alert.source_excerpt, source_version_id=alert.source_version_id, status=alert.status, routing_state=alert.routing_state.value, assigned_user_id=assigned_user_id, document_title=getattr(getattr(alert, "source_version", None), "document", None).title if getattr(alert, "source_version", None) and getattr(alert.source_version, "document", None) else None)


def action_response(action: Action) -> ActionResponse:
    return ActionResponse(id=action.id, source_version_id=action.source_version_id, title=action.title, owner_id=action.owner_id, due_at=action.due_at, priority=action.priority, status=action.status, comments=action.comments, completion_evidence=action.completion_evidence, acknowledged_at=action.acknowledged_at, completed_at=action.completed_at, verified_by=action.verified_by, verified_at=action.verified_at, events=[ActionEventResponse(id=item.id, event_type=item.event_type.value, timestamp=item.timestamp, actor_id=item.actor_id, detail=item.detail) for item in sorted(action.events, key=lambda item: item.timestamp.replace(tzinfo=timezone.utc) if item.timestamp.tzinfo is None else item.timestamp)])


@router.get("/alerts", response_model=list[AlertResponse])
async def list_alerts(priority: ActionPriority | None = None, department: str | None = None, status: AlertStatus | None = None, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = select(Alert).order_by(Alert.priority.desc(), Alert.deadline.asc().nullslast())
    if priority: query = query.where(Alert.priority == priority)
    if department: query = query.where(Alert.suggested_department == department)
    if status: query = query.where(Alert.status == status)
    query = query.options(selectinload(Alert.assignments), selectinload(Alert.source_version).selectinload(DocumentVersion.document))
    alerts = (await db.execute(query)).scalars().unique().all()
    return [alert_response(alert, alert.assignments[0].assignee_id if alert.assignments else None) for alert in alerts]


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: UUID, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    alert = (await db.execute(select(Alert).options(selectinload(Alert.assignments), selectinload(Alert.source_version).selectinload(DocumentVersion.document)).where(Alert.id == alert_id))).scalar_one_or_none()
    if alert is None: raise HTTPException(status_code=404, detail="Alert not found")
    return alert_response(alert, alert.assignments[0].assignee_id if alert.assignments else None)


@router.post("/alerts/{alert_id}/transition", response_model=AlertResponse)
async def transition_alert(alert_id: UUID, payload: AlertTransitionRequest, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    alert = (await db.execute(select(Alert).options(selectinload(Alert.assignments), selectinload(Alert.source_version).selectinload(DocumentVersion.document)).where(Alert.id == alert_id))).scalar_one_or_none()
    if alert is None: raise HTTPException(status_code=404, detail="Alert not found")
    ensure_alert_transition(alert, payload.target, current_user)
    before = {"title": alert.title, "suggested_department": alert.suggested_department, "suggested_action": alert.suggested_action, "deadline": alert.deadline.isoformat() if alert.deadline else None, "status": alert.status.value}
    if payload.title is not None: alert.title = payload.title
    if payload.suggested_department is not None: alert.suggested_department = payload.suggested_department
    if payload.suggested_action is not None: alert.suggested_action = payload.suggested_action
    if payload.deadline is not None: alert.deadline = payload.deadline
    alert.status = payload.target
    if payload.target == AlertStatus.APPROVED: alert.reviewer_id = user_uuid(current_user)
    await db.flush()
    after = {"title": alert.title, "suggested_department": alert.suggested_department, "suggested_action": alert.suggested_action, "deadline": alert.deadline.isoformat() if alert.deadline else None, "status": alert.status.value}
    if before != after and reviewer_role(current_user["role"]): db.add(Feedback(prediction_id=alert.id, reviewer_id=user_uuid(current_user), correction=json.dumps({"before": before, "after": after}), reason=FeedbackReason.INCORRECT_ACTION))
    await db.commit()
    return alert_response(alert, alert.assignments[0].assignee_id if alert.assignments else None)


def reviewer_role(role: str) -> bool: return role in {Role.SYSTEM_ADMINISTRATOR.value, Role.DOCUMENT_ADMINISTRATOR.value, Role.REVIEWER.value}


@router.post("/alerts/{alert_id}/quick-share", response_model=AlertResponse)
async def quick_share(alert_id: UUID, payload: QuickShareRequest, current_user: dict = Depends(require_roles(Role.SYSTEM_ADMINISTRATOR, Role.DOCUMENT_ADMINISTRATOR, Role.REVIEWER)), db: AsyncSession = Depends(get_db)):
    alert = (await db.execute(select(Alert).options(selectinload(Alert.assignments), selectinload(Alert.source_version).selectinload(DocumentVersion.document)).where(Alert.id == alert_id))).scalar_one_or_none()
    if alert is None: raise HTTPException(status_code=404, detail="Alert not found")
    if alert.status not in {AlertStatus.APPROVED, AlertStatus.ASSIGNED}: raise HTTPException(status_code=409, detail="Only approved alerts can be shared")
    assignee = await db.get(User, payload.assignee_id)
    if assignee is None: raise HTTPException(status_code=404, detail="Assignee not found")
    alert.source_excerpt = payload.excerpt
    alert.suggested_action = payload.action
    alert.deadline = payload.deadline
    alert.status = AlertStatus.ASSIGNED
    db.add(Assignment(alert_id=alert.id, assignee_id=payload.assignee_id, assigned_by=user_uuid(current_user)))
    await db.commit()
    return alert_response(alert, payload.assignee_id)


@router.post("/alerts/{alert_id}/create-action", response_model=ActionResponse)
async def create_action_from_alert(alert_id: UUID, payload: ActionCreateRequest | None = None, current_user: dict = Depends(require_roles(Role.SYSTEM_ADMINISTRATOR, Role.DOCUMENT_ADMINISTRATOR, Role.REVIEWER)), db: AsyncSession = Depends(get_db)):
    alert = (await db.execute(select(Alert).options(selectinload(Alert.assignments), selectinload(Alert.source_version).selectinload(DocumentVersion.document)).where(Alert.id == alert_id))).scalar_one_or_none()
    if alert is None: raise HTTPException(status_code=404, detail="Alert not found")
    if alert.status not in {AlertStatus.APPROVED, AlertStatus.ASSIGNED}: raise HTTPException(status_code=409, detail="Alert must be approved before creating an action")
    owner_id = payload.owner_id if payload else (alert.assignments[0].assignee_id if alert.assignments else None)
    action = Action(source_version_id=alert.source_version_id, title=(payload.title if payload else alert.suggested_action or alert.title), owner_id=owner_id, due_at=(payload.due_at if payload else alert.deadline), priority=(payload.priority if payload else alert.priority), status=ActionStatus.OPEN, comments=(payload.comments if payload else "Created from approved alert"))
    db.add(action)
    await db.flush()
    db.add(event(action, user_uuid(current_user), ActionEventType.CREATED, {"source_alert_id": str(alert.id), "status": ActionStatus.OPEN.value}))
    alert.status = AlertStatus.ASSIGNED
    if owner_id: db.add(Assignment(alert_id=alert.id, action_id=action.id, assignee_id=owner_id, assigned_by=user_uuid(current_user)))
    await db.commit()
    action = (await db.execute(select(Action).options(selectinload(Action.events)).where(Action.id == action.id))).scalar_one()
    return action_response(action)


@router.get("/actions", response_model=list[ActionResponse])
async def list_actions(owner_id: UUID | None = None, status: ActionStatus | None = None, priority: ActionPriority | None = None, overdue: bool = False, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = select(Action).order_by(Action.due_at.asc().nullslast())
    if owner_id: query = query.where(Action.owner_id == owner_id)
    if status: query = query.where(Action.status == status)
    if priority: query = query.where(Action.priority == priority)
    if overdue: query = query.where(Action.due_at < datetime.now(timezone.utc), Action.status.not_in([ActionStatus.COMPLETED, ActionStatus.CLOSED, ActionStatus.REJECTED]))
    query = query.options(selectinload(Action.events))
    actions = (await db.execute(query)).scalars().unique().all()
    for action in actions: await mark_overdue(action, db, user_uuid(current_user))
    await db.commit()
    return [action_response(action) for action in actions]


@router.post("/actions", response_model=ActionResponse)
async def create_action(payload: ActionCreateRequest, current_user: dict = Depends(require_roles(Role.SYSTEM_ADMINISTRATOR, Role.DOCUMENT_ADMINISTRATOR, Role.REVIEWER)), db: AsyncSession = Depends(get_db)):
    action = Action(source_version_id=payload.source_version_id, title=payload.title, owner_id=payload.owner_id, due_at=payload.due_at, priority=payload.priority, status=ActionStatus.DRAFT, comments=payload.comments)
    db.add(action); await db.flush(); db.add(event(action, user_uuid(current_user), ActionEventType.CREATED, {"status": ActionStatus.DRAFT.value})); await db.commit(); action = (await db.execute(select(Action).options(selectinload(Action.events)).where(Action.id == action.id))).scalar_one(); return action_response(action)


@router.delete("/actions/{action_id}", response_model=ActionResponse)
async def delete_action(action_id: UUID, current_user: dict = Depends(require_roles(Role.SYSTEM_ADMINISTRATOR, Role.DOCUMENT_ADMINISTRATOR, Role.REVIEWER)), db: AsyncSession = Depends(get_db)):
    action = (await db.execute(select(Action).options(selectinload(Action.events)).where(Action.id == action_id))).scalar_one_or_none()
    if action is None: raise HTTPException(status_code=404, detail="Action not found")
    if action.status == ActionStatus.CLOSED: raise HTTPException(status_code=409, detail="Closed actions cannot be deleted")
    previous = action.status.value
    action.status = ActionStatus.REJECTED
    db.add(event(action, user_uuid(current_user), ActionEventType.CANCELLED, {"from": previous, "to": ActionStatus.REJECTED.value, "soft_delete": True}))
    await db.commit()
    action = (await db.execute(select(Action).options(selectinload(Action.events)).where(Action.id == action.id))).scalar_one()
    return action_response(action)


@router.get("/actions/{action_id}", response_model=ActionResponse)
async def get_action(action_id: UUID, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    action = (await db.execute(select(Action).options(selectinload(Action.events)).where(Action.id == action_id))).scalar_one_or_none()
    if action is None: raise HTTPException(status_code=404, detail="Action not found")
    return action_response(action)


@router.patch("/actions/{action_id}", response_model=ActionResponse)
async def update_action(action_id: UUID, payload: ActionUpdateRequest, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    action = (await db.execute(select(Action).options(selectinload(Action.events)).where(Action.id == action_id))).scalar_one_or_none()
    if action is None: raise HTTPException(status_code=404, detail="Action not found")
    if action.owner_id and str(action.owner_id) != current_user["sub"] and not reviewer_role(current_user["role"]): raise HTTPException(status_code=403, detail="Only the action owner or reviewer can edit this action")
    if payload.owner_id is not None: action.owner_id = payload.owner_id
    if payload.due_at is not None: action.due_at = payload.due_at
    if payload.comments is not None: action.comments = payload.comments
    if payload.completion_evidence is not None: action.completion_evidence = payload.completion_evidence
    db.add(event(action, user_uuid(current_user), ActionEventType.COMMENTED, {"comments": payload.comments, "completion_evidence": payload.completion_evidence}))
    await db.commit(); return action_response(action)


@router.post("/actions/{action_id}/transition", response_model=ActionResponse)
async def transition_action(action_id: UUID, payload: ActionTransitionRequest, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    action = (await db.execute(select(Action).options(selectinload(Action.events)).where(Action.id == action_id))).scalar_one_or_none()
    if action is None: raise HTTPException(status_code=404, detail="Action not found")
    ensure_action_transition(action, payload.target, current_user)
    previous = action.status
    action.status = payload.target
    if payload.completion_evidence is not None: action.completion_evidence = payload.completion_evidence
    now = datetime.now(timezone.utc)
    if payload.target == ActionStatus.ACKNOWLEDGED: action.acknowledged_at = now
    if payload.target == ActionStatus.COMPLETED: action.completed_at = now
    if payload.target == ActionStatus.CLOSED: action.verified_by = user_uuid(current_user); action.verified_at = now
    event_type = ActionEventType.COMPLETED if payload.target == ActionStatus.COMPLETED else ActionEventType.STATUS_CHANGED
    db.add(event(action, user_uuid(current_user), event_type, {"from": previous.value, "to": payload.target.value, "detail": payload.detail, "completion_evidence": payload.completion_evidence}))
    await db.commit(); return action_response(action)
