from __future__ import annotations

import hashlib
import json
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models import AuditEvent
from app.schemas.rag import Citation, RAGRequest, RAGResponse
from app.services.rag import REFUSAL, allowed, answer_from_evidence, retrieve

router = APIRouter(prefix="/search", tags=["rag-search"])


@router.post("/ask", response_model=RAGResponse)
async def ask(question: RAGRequest, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> RAGResponse:
    results = await retrieve(db, question.question, current_user)
    answer, raw_citations = answer_from_evidence(question.question, results)
    permitted_chunk_ids = {str(item.chunk.id) for item in results if allowed(item.chunk.access_scope, current_user)}
    raw_citations = [citation for citation in raw_citations if citation["chunk_id"] in permitted_chunk_ids]
    citations = [Citation(**citation, source_url=f"/api/v1/documents/{citation['document_id']}/source") for citation in raw_citations]
    if answer != REFUSAL and not citations:
        answer = REFUSAL
    audit_payload = {"question": question.question, "answer": answer, "refusal": answer == REFUSAL, "citations": [citation.model_dump(mode="json") for citation in citations]}
    audit_hash = hashlib.sha256(json.dumps(audit_payload, sort_keys=True).encode()).hexdigest()
    db.add(AuditEvent(actor_id=UUID(current_user["sub"]), event_type="rag_query_answer", object_type="rag_query", object_id=UUID(current_user["sub"]), hash=audit_hash, detail=audit_payload))
    await db.commit()
    return RAGResponse(answer=answer, refusal=answer == REFUSAL, citations=citations)
