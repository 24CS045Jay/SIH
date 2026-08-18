from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_user, require_roles
from app.db.session import get_db
from app.models import Action, ActionEventType, ActionStatus, Alert, Comparison, Document, DocumentVersion, Role, Change
from app.schemas.comparison import ChangeResponse, ComparisonResponse
from app.services.workflows import event
from app.services.access import can_access_document

router = APIRouter(prefix="/comparisons", tags=["comparisons"])


def change_response(change: Change, action_id: UUID | None = None) -> ChangeResponse:
    return ChangeResponse(id=change.id, change_type=change.change_type, old_span=change.old_span, new_span=change.new_span, impact=change.impact, interpretation=change.interpretation, affected_department=change.affected_department, priority=change.priority, required_action=change.required_action, action_id=action_id)


@router.get("", response_model=list[ComparisonResponse])
async def list_comparisons(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Comparison).options(selectinload(Comparison.changes), selectinload(Comparison.old_version).selectinload(DocumentVersion.document).selectinload(Document.owner), selectinload(Comparison.new_version).selectinload(DocumentVersion.document).selectinload(Document.owner)).order_by(Comparison.id.desc()))).scalars().unique().all()
    return [ComparisonResponse(id=item.id, old_version_id=item.old_version_id, new_version_id=item.new_version_id, status=item.status, changes=[change_response(change) for change in item.changes]) for item in rows if item.old_version and item.new_version and can_access_document(item.old_version.document, current_user) and can_access_document(item.new_version.document, current_user)]


@router.get("/{comparison_id}", response_model=ComparisonResponse)
async def get_comparison(comparison_id: UUID, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = (await db.execute(select(Comparison).options(selectinload(Comparison.changes), selectinload(Comparison.old_version).selectinload(DocumentVersion.document).selectinload(Document.owner), selectinload(Comparison.new_version).selectinload(DocumentVersion.document).selectinload(Document.owner)).where(Comparison.id == comparison_id))).scalar_one_or_none()
    if item is None: raise HTTPException(status_code=404, detail="Comparison not found")
    if not item.old_version or not item.new_version or not can_access_document(item.old_version.document, current_user) or not can_access_document(item.new_version.document, current_user): raise HTTPException(status_code=403, detail="Comparison is outside your access scope")
    return ComparisonResponse(id=item.id, old_version_id=item.old_version_id, new_version_id=item.new_version_id, status=item.status, old_title=item.old_version.document.title if item.old_version and item.old_version.document else None, new_title=item.new_version.document.title if item.new_version and item.new_version.document else None, old_document_id=item.old_version.document.id if item.old_version and item.old_version.document else None, new_document_id=item.new_version.document.id if item.new_version and item.new_version.document else None, changes=[change_response(change) for change in item.changes])


@router.post("/{comparison_id}/changes/{change_id}/action", response_model=dict)
async def convert_change_to_action(comparison_id: UUID, change_id: UUID, current_user: dict = Depends(require_roles(Role.SYSTEM_ADMINISTRATOR, Role.DOCUMENT_ADMINISTRATOR, Role.REVIEWER)), db: AsyncSession = Depends(get_db)):
    comparison = (await db.execute(select(Comparison).options(selectinload(Comparison.new_version).selectinload(DocumentVersion.document).selectinload(Document.owner), selectinload(Comparison.old_version).selectinload(DocumentVersion.document).selectinload(Document.owner)).where(Comparison.id == comparison_id))).scalar_one_or_none()
    change = await db.get(Change, change_id)
    if comparison is None or change is None or change.comparison_id != comparison.id: raise HTTPException(status_code=404, detail="Comparison change not found")
    if not comparison.new_version or not comparison.old_version or not can_access_document(comparison.new_version.document, current_user) or not can_access_document(comparison.old_version.document, current_user): raise HTTPException(status_code=403, detail="Comparison is outside your access scope")
    existing = await db.scalar(select(Action).where(Action.comments.ilike(f"%comparison_change_id:{change.id}%")))
    if existing: return {"action_id": str(existing.id), "status": existing.status.value, "message": "Action candidate already exists"}
    new_span = change.new_span or change.old_span or {}
    action = Action(source_version_id=comparison.new_version_id, title=change.required_action or change.interpretation, owner_id=None, due_at=None, priority=change.priority, status=ActionStatus.DRAFT, comments=f"Comparison change candidate; comparison_id:{comparison.id}; comparison_change_id:{change.id}; source_span:{new_span.get('quote','')}")
    db.add(action); await db.flush(); db.add(event(action, UUID(current_user["sub"]), ActionEventType.CREATED, {"source": "comparison_change", "comparison_id": str(comparison.id), "change_id": str(change.id), "requires_human_review": True})); await db.commit()
    return {"action_id": str(action.id), "status": action.status.value, "message": "Draft action candidate created for human review"}
