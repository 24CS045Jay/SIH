from __future__ import annotations

import hashlib
import json
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models import AuditEvent, Document
from app.schemas.rag import Citation, RAGRequest, RAGResponse
from app.services.access import can_access_document
from app.services.rag import REFUSAL, retrieve
from app.services.rag_embeddings import EmbeddingProviderError
from app.services.rag_generation import GenerationProviderError, generate_grounded_answer
from app.services.rag_guardrails import evidence_gate

router = APIRouter(prefix="/search", tags=["rag-search"])


@router.post("/ask", response_model=RAGResponse)
async def ask(question: RAGRequest, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> RAGResponse:
    started = time.perf_counter()
    scope = question.scope or "all"
    if question.document_id is not None:
        document = await db.scalar(select(Document).options(selectinload(Document.owner)).where(Document.id == question.document_id))
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        if not can_access_document(document, current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to search this document")
        scope = "document"
    try:
        results = await retrieve(db, question.question, current_user, document_id=question.document_id, scope=scope)
    except EmbeddingProviderError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    decision = evidence_gate(results, scope, str(question.document_id) if question.document_id else None)
    answer = REFUSAL
    raw_citations: list[dict] = []
    if decision.allowed:
        try:
            answer, raw_citations = await generate_grounded_answer(question.question, results)
        except GenerationProviderError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    permitted_ids = {str(item.chunk.id) for item in results}
    raw_citations = [citation for citation in raw_citations if citation["chunk_id"] in permitted_ids]
    citations = [Citation(**citation, source_url=f"/api/v1/documents/{citation['document_id']}/source") for citation in raw_citations]
    if answer != REFUSAL and not citations:
        answer = REFUSAL
        decision.reason = "citation_validation_failed"
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    diagnostics = {"candidate_count": len(results), "final_evidence_ids": [str(item.chunk.id) for item in results[:4]], "vector_scores": [round(item.vector_score, 4) for item in results[:4]], "lexical_scores": [round(item.keyword_score, 4) for item in results[:4]], "reranker_scores": [round(item.rerank_score, 4) for item in results[:4]], "refusal_reason": None if answer != REFUSAL else decision.reason, "latency_ms": duration_ms}
    audit_payload = {"question": question.question, "scope": scope, "document_id": str(question.document_id) if question.document_id else None, "answer": answer, "refusal": answer == REFUSAL, "citations": [citation.model_dump(mode="json") for citation in citations], "diagnostics": diagnostics}
    audit_hash = hashlib.sha256(json.dumps(audit_payload, sort_keys=True).encode()).hexdigest()
    db.add(AuditEvent(actor_id=UUID(current_user["sub"]), event_type="rag_query_answer", object_type="rag_query", object_id=UUID(current_user["sub"]), hash=audit_hash, detail=audit_payload))
    await db.commit()
    return RAGResponse(answer=answer, refusal=answer == REFUSAL, citations=citations, scope=scope, refusal_reason=diagnostics["refusal_reason"], diagnostics=diagnostics)
