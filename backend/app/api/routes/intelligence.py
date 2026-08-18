from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user, require_roles
from app.db.session import get_db
from app.models import Document, DocumentVersion, Feedback, ReviewerState, Role, User
from app.schemas.intelligence import CorrectionRequest, IntelligenceCardResponse, IntelligenceFieldResponse, Span
from app.services.intelligence_persistence import get_facts
from app.services.access import can_access_document

router = APIRouter(prefix="/documents", tags=["intelligence"])


def as_span(value: dict) -> Span | None:
    if not value: return None
    candidate = value.get("evidence", value)
    if isinstance(candidate, list): candidate = candidate[0] if candidate else None
    if not isinstance(candidate, dict) or "page_no" not in candidate: return None
    return Span.model_validate(candidate)


def field(fact, source: str | None = None) -> IntelligenceFieldResponse:
    return IntelligenceFieldResponse(prediction_id=fact.id, field=fact.field, value=fact.value, confidence=fact.confidence, source_span=as_span(fact.source_span), review_state=fact.reviewer_state.value, source=source or ("human-entered" if fact.reviewer_state.value == "corrected" else "AI-suggested"))


@router.get("/{document_id}/intelligence", response_model=IntelligenceCardResponse)
async def intelligence_card(document_id: UUID, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> IntelligenceCardResponse:
    row = (await db.execute(select(Document, DocumentVersion).options(selectinload(Document.owner)).join(DocumentVersion, DocumentVersion.document_id == Document.id).where(Document.id == document_id).order_by(DocumentVersion.uploaded_at.desc()).limit(1))).first()
    if row is None: raise HTTPException(status_code=404, detail="Document not found")
    document, version = row
    if not can_access_document(document, current_user): raise HTTPException(status_code=403, detail="Document is outside your access scope")
    facts = list(await get_facts(db, version.id))
    if not facts: raise HTTPException(status_code=409, detail="Intelligence processing is not ready")
    grouped = {"classification": [], "summary": [], "key_fact": [], "entity": [], "action": [], "deadline": [], "priority": [], "routing": []}
    for fact in facts:
        key = fact.field.split(":", 1)[0]
        if key in grouped: grouped[key].append(fact)
    missing = [key for key in ("classification", "summary", "deadline", "priority", "routing") if not grouped[key]]
    if missing: raise HTTPException(status_code=409, detail=f"Intelligence fields are not ready: {', '.join(missing)}")
    return IntelligenceCardResponse(version_id=version.id, document_id=document.id, title=document.title, classification=field(grouped["classification"][0]), summary=field(grouped["summary"][0]), key_facts=[field(item) for item in grouped["key_fact"]], entities=[field(item) for item in grouped["entity"]], actions=[field(item) for item in grouped["action"]], deadline=field(grouped["deadline"][0]), priority=field(grouped["priority"][0]), routing=field(grouped["routing"][0]))


@router.post("/{document_id}/intelligence/corrections", response_model=IntelligenceFieldResponse)
async def correct_intelligence(document_id: UUID, payload: CorrectionRequest, current_user: dict = Depends(require_roles(Role.SYSTEM_ADMINISTRATOR, Role.DOCUMENT_ADMINISTRATOR, Role.REVIEWER)), db: AsyncSession = Depends(get_db)) -> IntelligenceFieldResponse:
    row = (await db.execute(select(DocumentVersion).join(Document, Document.id == DocumentVersion.document_id).options(selectinload(Document.owner)).where(DocumentVersion.document_id == document_id).order_by(DocumentVersion.uploaded_at.desc()).limit(1))).scalar_one_or_none()
    if row is None: raise HTTPException(status_code=404, detail="Document not found")
    document = await db.scalar(select(Document).options(selectinload(Document.owner)).where(Document.id == document_id))
    if document is None or not can_access_document(document, current_user): raise HTTPException(status_code=403, detail="Document is outside your access scope")
    facts = list(await get_facts(db, row.id))
    fact = next((item for item in facts if str(item.id) == payload.field or item.field == payload.field), None)
    if fact is None: raise HTTPException(status_code=404, detail="Intelligence field not found")
    reviewer_id = UUID(current_user["sub"])
    fact.value = payload.correction
    fact.reviewer_state = ReviewerState.CORRECTED
    db.add(Feedback(prediction_id=fact.id, reviewer_id=reviewer_id, correction=payload.correction, reason=payload.reason))
    await db.commit()
    return field(fact, "human-entered")
