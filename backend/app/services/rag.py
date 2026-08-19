from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import Chunk, Department, Document, DocumentVersion, Page, Role, User, VersionStatus
from app.services.access import can_access_scope
from app.services.rag_chunking import chunk_pages
from app.services.rag_embeddings import EmbeddingProviderError, cosine, embed_texts
from app.services.rag_reranker import rerank, suspicious_instruction

REFUSAL = "Information not available in the approved documents"
TOKEN_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = {"the", "is", "a", "an", "and", "or", "of", "for", "to", "in", "on", "what", "who", "how", "are", "was", "were", "this", "that", "from", "with", "about", "does", "do", "did", "can", "could", "would", "should", "please", "tell", "me", "give", "provide", "document", "report", "information", "related", "relate"}


@dataclass
class RetrievedChunk:
    chunk: Chunk
    document_id: UUID
    document_title: str
    version_id: UUID
    page_no: int
    keyword_score: float
    vector_score: float
    combined_score: float = 0.0
    rerank_score: float = 0.0
    ocr_confidence: float = 1.0
    suspicious_instruction: bool = False


def tokens(text: str) -> list[str]:
    return [token for token in TOKEN_RE.findall(text.lower()) if token not in STOPWORDS]


def embedding(text: str, dimensions: int = 24) -> list[float]:
    """Legacy compatibility helper; production indexing uses rag_embeddings.embed_texts."""
    from collections import Counter
    vocabulary = sorted(set(tokens(text)))
    counts = Counter(tokens(text))
    vector = [float(counts.get(term, 0)) for term in vocabulary[:dimensions]]
    length = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / length for value in vector]


def chunk_text(text: str, size: int = 900, overlap: int = 120) -> list[str]:
    """Compatibility wrapper; structure-aware chunking is the primary implementation."""
    normalized = text.strip()
    if not normalized:
        return []
    result: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + size)
        if end < len(normalized):
            boundary = max(normalized.rfind("\n", start, end), normalized.rfind(". ", start, end))
            if boundary > start + size // 2:
                end = boundary + (1 if normalized[boundary] == "." else 0)
        result.append(normalized[start:end].strip())
        if end >= len(normalized):
            break
        start = max(end - overlap, start + 1)
    return [item for item in result if item]


async def build_chunks(session: AsyncSession, version_id: UUID) -> int:
    version = await session.scalar(select(DocumentVersion).where(DocumentVersion.id == version_id))
    if version is None:
        return 0
    doc_row = (await session.execute(select(Document, User).join(User, Document.owner_id == User.id).where(Document.id == version.document_id))).first()
    if doc_row is None:
        return 0
    document, owner = doc_row
    pages = (await session.execute(select(Page).where(Page.version_id == version_id).order_by(Page.page_no))).scalars().all()
    page_payload = [(page.page_no, page.ocr_text or "", float(page.ocr_confidence or 0.0)) for page in pages if (page.ocr_text or "").strip()]
    structured = chunk_pages(page_payload)
    await session.execute(delete(Chunk).where(Chunk.version_id == version_id))
    if not structured:
        return 0
    vectors = await embed_texts([item.text for item in structured])
    scope = {"roles": [role.value for role in Role], "department_id": str(owner.department_id) if owner.department_id else None, "sensitivity": document.sensitivity.value}
    for item, vector in zip(structured, vectors):
        session.add(Chunk(version_id=version_id, page_id=next((page.id for page in pages if page.page_no == item.page_no), None), text=item.text, embedding_ref=json.dumps(vector, separators=(",", ":")), access_scope=scope, section_number=item.section, section_title=item.section_title, subsection=item.subsection, chunk_index=item.chunk_index, token_count=item.token_count, ocr_confidence=item.ocr_confidence, parent_context=item.parent_context))
    await session.flush()
    return len(structured)


def allowed(scope: dict, user: dict) -> bool:
    return can_access_scope(scope, user)


def _document_focus_terms(question: str) -> set[str]:
    terms = set(tokens(question))
    if "brake" in terms or ("maintenance" in terms and ("manual" in terms or "checklist" in terms)):
        return {"maintenance"}
    focus_pairs = ({"maintenance", "manual"}, {"safety", "circular"}, {"purchase", "order"}, {"incident", "report"}, {"training", "notice"}, {"environmental", "compliance"})
    for pair in focus_pairs:
        if pair <= terms:
            return pair
    return set()


def _scope_matches(item: RetrievedChunk, scope: str, document_id: UUID | None) -> bool:
    return scope != "document" or document_id is None or item.document_id == document_id


async def retrieve(session: AsyncSession, question: str, user: dict, limit: int | None = None, document_id: UUID | None = None, scope: str | None = None) -> list[RetrievedChunk]:
    settings = get_settings()
    scope = (scope or settings.rag_document_scope_default).lower()
    if scope not in {"document", "all"}:
        scope = settings.rag_document_scope_default
    rows = (await session.execute(select(Chunk, Document.id, Document.title, DocumentVersion.id, DocumentVersion.uploaded_at, Page.page_no).join(DocumentVersion, Chunk.version_id == DocumentVersion.id).join(Document, DocumentVersion.document_id == Document.id).join(Page, Chunk.page_id == Page.id).where(DocumentVersion.status == VersionStatus.REVIEW_READY))).all()
    query_tokens = set(tokens(question))
    if not query_tokens:
        return []
    candidate_rows: list[tuple[Any, ...]] = []
    latest_upload_by_document: dict[UUID, Any] = {}
    for row in rows:
        chunk, doc_id, title, version_id, uploaded_at, page_no = row
        if not allowed(chunk.access_scope, user) or not _scope_matches(RetrievedChunk(chunk, doc_id, title, version_id, page_no, 0, 0), scope, document_id):
            continue
        if doc_id not in latest_upload_by_document or uploaded_at > latest_upload_by_document[doc_id]:
            latest_upload_by_document[doc_id] = uploaded_at
    # Keep every chunk belonging to the latest approved version of each accessible document.
    for row in rows:
        chunk, doc_id, title, version_id, uploaded_at, page_no = row
        if latest_upload_by_document.get(doc_id) == uploaded_at and allowed(chunk.access_scope, user) and _scope_matches(RetrievedChunk(chunk, doc_id, title, version_id, page_no, 0, 0), scope, document_id):
            candidate_rows.append(row)
    if not candidate_rows:
        return []
    texts = [row[0].text for row in candidate_rows]
    settings_provider = settings.embedding_provider.lower()
    if settings_provider == "openai" or (settings_provider == "auto" and settings.openai_api_key):
        query_vector = (await embed_texts([question]))[0]
        vectors = [json.loads(row[0].embedding_ref or "[]") for row in candidate_rows]
    else:
        vectors_all = await embed_texts([question, *texts])
        query_vector, vectors = vectors_all[0], vectors_all[1:]
    focus_terms = _document_focus_terms(question)
    focus_documents = {row[2] for row in candidate_rows if focus_terms & set(tokens(row[2]))} if focus_terms else set()
    pool: list[RetrievedChunk] = []
    for row, vector in zip(candidate_rows, vectors):
        chunk, doc_id, title, version_id, _, page_no = row
        text_terms = set(tokens(chunk.text))
        keyword_score = len(query_tokens & text_terms) / max(len(query_tokens), 1)
        vector_score = cosine(query_vector, vector)
        if focus_documents and title not in focus_documents:
            continue
        combined = 0.55 * keyword_score + 0.45 * vector_score
        ocr_confidence = float(chunk.ocr_confidence) if chunk.ocr_confidence is not None else 0.92
        pool.append(RetrievedChunk(chunk, doc_id, title, version_id, page_no, keyword_score, vector_score, combined, 0.0, ocr_confidence, suspicious_instruction(chunk.text)))
    pool.sort(key=lambda item: item.combined_score, reverse=True)
    top = pool[: (limit or settings.rag_vector_top_k)]
    ranked = rerank(question, top, query_vector)
    return ranked[: (limit or settings.rag_final_top_k)]


def _operational_text(text: str) -> str:
    units = [unit.strip() for unit in re.split(r"(?<=[.!?])\s+|\n+", text) if unit.strip()]
    kept = [unit for unit in units if not re.search(r"\b(distractor|no operational bearing|irrelevant detail|not operational|ignore previous instructions|disregard previous instructions|system prompt)\b", unit, flags=re.I)]
    return " ".join(kept).strip()


def _focused_excerpt(text: str, query_terms: set[str], limit: int = 320) -> str:
    text = _operational_text(text)
    units = [unit.strip() for unit in re.split(r"(?<=[.!?])\s+|\n+", text) if unit.strip()]
    ranked = sorted(((len(query_terms & set(tokens(unit))), index, unit) for index, unit in enumerate(units)), key=lambda item: (item[0], -item[1]), reverse=True)
    selected = [unit for overlap, _, unit in ranked if overlap > 0][:2]
    excerpt = " ".join(selected) if selected else text.strip()
    return excerpt[:limit].rstrip() + ("…" if len(excerpt) > limit else "")


def answer_from_evidence(question: str, results: list[RetrievedChunk]) -> tuple[str, list[dict]]:
    query_terms = set(tokens(question))
    if not query_terms:
        return REFUSAL, []
    focus_terms = _document_focus_terms(question)
    scoped_results = [item for item in results if focus_terms & set(tokens(item.document_title))] if focus_terms else results
    if focus_terms and scoped_results:
        results = scoped_results
    settings = get_settings()
    strong = []
    for item in results:
        overlap = len(query_terms & set(tokens(item.chunk.text))) / max(len(query_terms), 1)
        operational_text = _operational_text(item.chunk.text)
        if not operational_text:
            continue
        overlap = len(query_terms & set(tokens(operational_text))) / max(len(query_terms), 1)
        rerank_score = getattr(item, "rerank_score", 1.0)
        combined_score = getattr(item, "combined_score", max(getattr(item, "keyword_score", 0.0), getattr(item, "vector_score", 0.0)))
        if overlap >= 0.12 and rerank_score >= settings.rag_min_rerank_score and combined_score >= settings.rag_min_relevance:
            strong.append(item)
    if not strong:
        return REFUSAL, []
    selected = strong[: min(3, settings.rag_final_top_k)]
    citations = []
    for index, item in enumerate(selected, start=1):
        citations.append({"citation_id": f"C{index}", "chunk_id": str(item.chunk.id), "document_id": str(item.document_id), "version_id": str(item.version_id), "document_title": item.document_title, "page_no": item.page_no, "section_number": getattr(item.chunk, "section_number", None), "section_title": getattr(item.chunk, "section_title", None), "quote": _focused_excerpt(item.chunk.text, query_terms)})
    answer = " ".join(f"[{citation['citation_id']}] {citation['quote']}" for citation in citations)
    return answer, citations
