from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Action, ActionPriority, ActionStatus, Alert, ExtractedFact, ReviewerState
from app.schemas.intelligence import IntelligenceResult


def add_fact(session: AsyncSession, version_id: UUID, field: str, value: str, source_span: dict | None, confidence: float) -> ExtractedFact:
    fact = ExtractedFact(version_id=version_id, field=field, value=value, source_span=source_span or {}, confidence=confidence, reviewer_state=ReviewerState.PENDING)
    session.add(fact)
    return fact


async def persist_intelligence(session: AsyncSession, version_id: UUID | str, result: IntelligenceResult) -> None:
    vid = UUID(str(version_id)) if isinstance(version_id, str) else version_id
    await session.execute(delete(ExtractedFact).where(ExtractedFact.version_id == vid))
    await session.execute(delete(Action).where(Action.source_version_id == vid))
    add_fact(session, vid, "classification", result.classification.document_type.value, result.classification.evidence.model_dump(mode="json"), result.classification.confidence)
    summary_span = result.summary.key_facts[0].source_span.model_dump(mode="json") if result.summary.key_facts else result.classification.evidence.model_dump(mode="json")
    add_fact(session, vid, "summary", result.summary.executive_summary, summary_span, result.summary.confidence)
    for fact in result.summary.key_facts:
        add_fact(session, vid, "key_fact", fact.text, fact.source_span.model_dump(mode="json"), fact.confidence)
    for entity in result.entities:
        add_fact(session, vid, f"entity:{entity.entity_type}", entity.value, entity.source_span.model_dump(mode="json"), entity.confidence)
    if result.deadline.status == "found":
        value = result.deadline.explicit_date or ""
    elif result.deadline.status == "ambiguous":
        value = f"Ambiguous relative deadline: {result.deadline.relative_text or 'not specified'}"
    else:
        value = "No deadline found"
    add_fact(session, vid, "deadline", value, result.deadline.evidence.model_dump(mode="json") if result.deadline.evidence else None, result.deadline.confidence)
    add_fact(session, vid, "priority", result.priority.priority, {"reason_codes": result.priority.reason_codes, "evidence": [item.model_dump(mode="json") for item in result.priority.evidence]}, result.priority.confidence)
    add_fact(session, vid, "routing", result.routing.department, {"why": result.routing.why, "evidence": result.routing.evidence.model_dump(mode="json")}, result.routing.confidence)
    for action_prediction in result.actions:
        add_fact(session, vid, "action", action_prediction.title, action_prediction.evidence.model_dump(mode="json"), action_prediction.confidence)
        session.add(Action(source_version_id=vid, title=action_prediction.title, priority=ActionPriority(result.priority.priority), status=ActionStatus.PROPOSED, due_at=None))
    if result.priority.priority in {"critical", "high"}:
        session.add(Alert(source_version_id=vid, priority=ActionPriority(result.priority.priority), reason_codes=result.priority.reason_codes))
    await session.flush()


async def get_facts(session: AsyncSession, version_id: UUID) -> Sequence[ExtractedFact]:
    return (await session.execute(select(ExtractedFact).where(ExtractedFact.version_id == version_id).order_by(ExtractedFact.field, ExtractedFact.id))).scalars().all()
