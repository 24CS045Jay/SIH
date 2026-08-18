from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user
from app.db.session import get_db
from app.models import (
    Action,
    ActionEvent,
    Department,
    ActionPriority,
    ActionStatus,
    Alert,
    Document,
    DocumentVersion,
    ExtractedFact,
    Feedback,
    Page,
    User,
    VersionStatus,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


EXECUTIVE_ROLES = {
    "system_administrator",
    "document_administrator",
    "executive_viewer",
}
TERMINAL_ACTIONS = {ActionStatus.COMPLETED, ActionStatus.CLOSED, ActionStatus.REJECTED, ActionStatus.CANCELLED}


def _id(value: UUID | None) -> str | None:
    return str(value) if value else None


def _enum(value):
    return value.value if hasattr(value, "value") else value


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value).isoformat()


def _role_scope(user: dict) -> tuple[bool, str | None]:
    role = user.get("role", "")
    department = user.get("department")
    return role in EXECUTIVE_ROLES, department


def _trust(version: DocumentVersion, fact: ExtractedFact | None = None, excerpt: str | None = None) -> dict:
    span = (fact.source_span if fact else {}) or {}
    return {
        "source_document": version.document.title if version.document else "Source document",
        "document_id": _id(version.document_id),
        "version_id": _id(version.id),
        "page": span.get("page_no") or 1,
        "extracted_span": span.get("quote") or excerpt or (fact.value if fact else "Source evidence available in the approved document."),
        "reviewer": None,
        "model_version": "KMRL intelligence pipeline v1",
    }


async def _version_bundle(db: AsyncSession, version_ids: list[UUID]) -> dict[UUID, DocumentVersion]:
    if not version_ids:
        return {}
    result = await db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.id.in_(version_ids))
        .options(selectinload(DocumentVersion.document))
    )
    return {version.id: version for version in result.scalars().all()}


@router.get("/summary")
async def dashboard_summary(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    is_broad, department = _role_scope(current_user)
    user_id = UUID(current_user["sub"])

    alert_query = select(Alert).options(selectinload(Alert.source_version).selectinload(DocumentVersion.document))
    if not is_broad:
        alert_query = alert_query.where(Alert.suggested_department == department)
    alerts = (await db.execute(alert_query.order_by(Alert.priority.desc(), Alert.deadline.asc().nullslast()).limit(30))).scalars().unique().all()

    action_query = select(Action).options(selectinload(Action.events), selectinload(Action.owner))
    action_query = action_query.where(Action.owner_id == user_id)
    my_actions = (await db.execute(action_query.order_by(Action.due_at.asc().nullslast()).limit(40))).scalars().unique().all()

    latest_query = (
        select(DocumentVersion)
        .join(Document, Document.id == DocumentVersion.document_id)
        .options(selectinload(DocumentVersion.document).selectinload(Document.owner), selectinload(DocumentVersion.extracted_facts))
        .where(DocumentVersion.status.in_([VersionStatus.READY, VersionStatus.REVIEW_READY]))
        .order_by(DocumentVersion.uploaded_at.desc())
        .limit(12)
    )
    if not is_broad:
        latest_query = latest_query.join(User, User.id == Document.owner_id).where(User.department_id == UUID(current_user["department_id"]) if current_user.get("department_id") else False)
    latest = (await db.execute(latest_query)).scalars().unique().all()

    priority_counts = Counter(_enum(item.priority) for item in alerts)
    reason_counts: Counter[str] = Counter()
    for alert in alerts:
        reason_counts.update(alert.reason_codes or [])

    now = datetime.now(timezone.utc)
    def action_group(action: Action) -> str:
        if action.status == ActionStatus.BLOCKED:
            return "blocked"
        if action.status in TERMINAL_ACTIONS:
            return "recently_completed" if action.status in {ActionStatus.COMPLETED, ActionStatus.CLOSED} else "closed_out"
        if action.due_at and (action.due_at.replace(tzinfo=timezone.utc) if action.due_at.tzinfo is None else action.due_at) < now:
            return "overdue"
        if action.due_at and (action.due_at.replace(tzinfo=timezone.utc) if action.due_at.tzinfo is None else action.due_at) <= now.replace(hour=23, minute=59, second=59, microsecond=999999):
            return "due_soon"
        return "open"

    action_payload = []
    action_groups: Counter[str] = Counter()
    action_version_ids = [item.source_version_id for item in my_actions]
    action_versions = await _version_bundle(db, action_version_ids)
    for action in my_actions:
        group = action_group(action)
        action_groups[group] += 1
        action_payload.append({
            "id": _id(action.id), "title": action.title, "priority": _enum(action.priority), "status": _enum(action.status),
            "due_at": _iso(action.due_at), "owner_id": _id(action.owner_id), "group": group,
            "source": _trust(action_versions[action.source_version_id]) if action.source_version_id in action_versions else None,
        })

    alert_payload = []
    alert_version_ids = [item.source_version_id for item in alerts]
    alert_versions = await _version_bundle(db, alert_version_ids)
    for alert in alerts:
        version = alert_versions.get(alert.source_version_id)
        alert_payload.append({
            "id": _id(alert.id), "title": alert.title, "priority": _enum(alert.priority), "reason_codes": alert.reason_codes or [],
            "suggested_department": alert.suggested_department, "suggested_action": alert.suggested_action,
            "deadline": _iso(alert.deadline), "status": _enum(alert.status), "routing_state": _enum(alert.routing_state),
            "document_title": version.document.title if version and version.document else None,
            "source": _trust(version, excerpt=alert.source_excerpt) if version else None,
        })

    intelligence = []
    for version in latest:
        classification = next((fact for fact in version.extracted_facts if fact.field == "classification"), None)
        priority = next((fact for fact in version.extracted_facts if fact.field == "priority"), None)
        summary = next((fact for fact in version.extracted_facts if fact.field == "summary"), None)
        intelligence.append({
            "version_id": _id(version.id), "document_id": _id(version.document_id), "title": version.document.title,
            "version_label": version.version_label, "uploaded_at": _iso(version.uploaded_at), "status": _enum(version.status),
            "classification": classification.value if classification else version.document.classification.value,
            "confidence": classification.confidence if classification else None,
            "priority": priority.value if priority else None, "summary": summary.value if summary else None,
            "owner": version.document.owner.name if version.document.owner else None,
            "source": _trust(version, classification or summary),
        })

    department_counts: defaultdict[str, dict[str, int]] = defaultdict(lambda: {"alerts": 0, "actions": 0, "total": 0})
    for alert in alerts:
        key = alert.suggested_department or "Unrouted"
        department_counts[key]["alerts"] += 1
    department_action_query = select(Action, User, DocumentVersion, Document).join(User, User.id == Action.owner_id, isouter=True).options(selectinload(User.department)).join(DocumentVersion, DocumentVersion.id == Action.source_version_id).join(Document, Document.id == DocumentVersion.document_id)
    if not is_broad:
        department_action_query = department_action_query.where(User.department_id == UUID(current_user["department_id"]) if current_user.get("department_id") else False)
    for action, owner, _, _ in (await db.execute(department_action_query)).all():
        key = owner.department.name if owner and owner.department else "Unrouted"
        department_counts[key]["actions"] += 1
    for value in department_counts.values():
        value["total"] = value["alerts"] + value["actions"]

    return {
        "viewer": {"id": current_user["sub"], "name": current_user["name"], "role": current_user["role"], "department": department},
        "priority_strip": {"counts": {key: priority_counts.get(key, 0) for key in ["critical", "high", "medium", "low"]}, "reason_codes": dict(reason_counts)},
        "urgent_alerts": alert_payload[:8],
        "my_actions": {"counts": dict(action_groups), "items": action_payload},
        "new_intelligence": intelligence,
        "department_queue": [{"department": key, **value} for key, value in sorted(department_counts.items(), key=lambda pair: pair[1]["total"], reverse=True)],
        "trust": alert_payload[0]["source"] if alert_payload else (intelligence[0]["source"] if intelligence else None),
    }


@router.get("/analytics")
async def dashboard_analytics(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    if current_user.get("role") not in EXECUTIVE_ROLES:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Analytics are restricted to Executive Viewer and administrator roles")

    volume_rows = (await db.execute(select(func.date(DocumentVersion.uploaded_at).label("day"), func.count(DocumentVersion.id)).group_by(func.date(DocumentVersion.uploaded_at)).order_by(func.date(DocumentVersion.uploaded_at)))).all()
    total_facts = await db.scalar(select(func.count(ExtractedFact.id))) or 0
    total_feedback = await db.scalar(select(func.count(Feedback.id))) or 0
    corrections_by_reason = (await db.execute(select(Feedback.reason, func.count(Feedback.id)).group_by(Feedback.reason).order_by(func.count(Feedback.id).desc()))).all()

    latest_events = (await db.execute(select(Action, ActionEvent).join(ActionEvent, ActionEvent.action_id == Action.id).order_by(ActionEvent.timestamp.desc()))).all()
    latest_by_action: dict[UUID, tuple[Action, ActionEvent]] = {}
    for action, event in latest_events:
        latest_by_action.setdefault(action.id, (action, event))
    age_buckets: defaultdict[str, list[float]] = defaultdict(list)
    for action, event in latest_by_action.values():
        age_buckets[_enum(action.status)].append(max((datetime.now(timezone.utc) - (event.timestamp.replace(tzinfo=timezone.utc) if event.timestamp.tzinfo is None else event.timestamp)).total_seconds() / 86400, 0))
    action_ageing = [{"status": status, "count": len(values), "average_days": round(sum(values) / len(values), 1)} for status, values in sorted(age_buckets.items())]

    department_rows = (await db.execute(select(Alert.suggested_department, func.count(Alert.id)).group_by(Alert.suggested_department).order_by(func.count(Alert.id).desc()))).all()
    action_department_rows = (await db.execute(select(User.department_id, func.count(Action.id)).join(Action, Action.owner_id == User.id).group_by(User.department_id))).all()
    department_names = {row[0]: row[1] for row in (await db.execute(select(Department.id, Department.name))).all()}
    department_queue: defaultdict[str, dict[str, int]] = defaultdict(lambda: {"alerts": 0, "actions": 0, "total": 0})
    for name, count in department_rows:
        department_queue[name or "Unrouted"]["alerts"] = count
    for department_id, count in action_department_rows:
        name = department_names.get(department_id)
        department_queue[name or "Unrouted"]["actions"] = count
    for item in department_queue.values():
        item["total"] = item["alerts"] + item["actions"]

    return {
        "processing_volume": [{"date": str(day), "count": count} for day, count in volume_rows],
        "correction_rate": {"feedback_count": total_feedback, "prediction_count": total_facts, "rate": round((total_feedback / total_facts * 100) if total_facts else 0, 1), "by_reason": [{"reason": _enum(reason), "count": count} for reason, count in corrections_by_reason]},
        "action_ageing": action_ageing,
        "department_queue": [{"department": key, **value} for key, value in sorted(department_queue.items(), key=lambda pair: pair[1]["total"], reverse=True)],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
