from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, Department, Document, DocumentVersion, Page, Role, User
from app.services.access import can_access_scope

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


def tokens(text: str) -> list[str]:
    return [token for token in TOKEN_RE.findall(text.lower()) if token not in STOPWORDS]


def embedding(text: str, dimensions: int = 24) -> list[float]:
    vector = [0.0] * dimensions
    for token in tokens(text):
        digest = hashlib.sha256(token.encode()).digest()
        index = digest[0] % dimensions
        vector[index] += 1.0
    length = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / length, 4) for value in vector]


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def chunk_text(text: str, size: int = 900, overlap: int = 120) -> list[str]:
    normalized = text.strip()
    if not normalized: return []
    chunks = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + size)
        if end < len(normalized):
            boundary = normalized.rfind("\n", start, end)
            if boundary > start + size // 2: end = boundary
        chunks.append(normalized[start:end].strip())
        if end >= len(normalized): break
        start = max(end - overlap, start + 1)
    return [item for item in chunks if item]


async def build_chunks(session: AsyncSession, version_id: UUID) -> int:
    version = await session.scalar(select(DocumentVersion).where(DocumentVersion.id == version_id))
    if version is None: return 0
    doc_row = (await session.execute(select(Document, User).join(User, Document.owner_id == User.id).where(Document.id == version.document_id))).first()
    if doc_row is None: return 0
    document, owner = doc_row
    pages = (await session.execute(select(Page).where(Page.version_id == version_id).order_by(Page.page_no))).scalars().all()
    await session.execute(delete(Chunk).where(Chunk.version_id == version_id))
    count = 0
    for page in pages:
        for text in chunk_text(page.ocr_text or ""):
            scope = {"roles": [role.value for role in Role], "department_id": str(owner.department_id) if owner.department_id else None, "sensitivity": document.sensitivity.value}
            session.add(Chunk(version_id=version_id, page_id=page.id, text=text, embedding_ref=json.dumps(embedding(text), separators=(",", ":")), access_scope=scope))
            count += 1
    await session.flush()
    return count


def allowed(scope: dict, user: dict) -> bool:
    return can_access_scope(scope, user)


async def retrieve(session: AsyncSession, question: str, user: dict, limit: int = 6) -> list[RetrievedChunk]:
    rows = (await session.execute(select(Chunk, Document.id, Document.title, DocumentVersion.id, Page.page_no).join(DocumentVersion, Chunk.version_id == DocumentVersion.id).join(Document, DocumentVersion.document_id == Document.id).join(Page, Chunk.page_id == Page.id).where(DocumentVersion.status == "review_ready"))).all()
    query_tokens = set(tokens(question))
    if not query_tokens:
        return []
    query_embedding = embedding(question)
    results: list[RetrievedChunk] = []
    for chunk, document_id, title, version_id, page_no in rows:
        if not allowed(chunk.access_scope, user): continue
        text_tokens = set(tokens(chunk.text))
        keyword_score = len(query_tokens & text_tokens) / max(len(query_tokens), 1)
        try: vector_score = cosine(query_embedding, json.loads(chunk.embedding_ref or "[]"))
        except (TypeError, ValueError, json.JSONDecodeError): vector_score = 0.0
        results.append(RetrievedChunk(chunk, document_id, title, version_id, page_no, keyword_score, vector_score))
    results.sort(key=lambda item: 0.55 * item.keyword_score + 0.45 * item.vector_score, reverse=True)
    return results[:limit]


def _focused_excerpt(text: str, query_terms: set[str], limit: int = 300) -> str:
    """Return only the most query-relevant sentences/lines from a chunk."""
    units = [unit.strip() for unit in re.split(r"(?<=[.!?])\s+|\n+", text) if unit.strip()]
    ranked = sorted(
        ((len(query_terms & set(tokens(unit))), index, unit) for index, unit in enumerate(units)),
        key=lambda item: (item[0], -item[1]),
        reverse=True,
    )
    selected = [unit for overlap, _, unit in ranked if overlap > 0][:2]
    excerpt = " ".join(selected) if selected else text.strip()
    return excerpt[:limit].rstrip() + ("…" if len(excerpt) > limit else "")


def answer_from_evidence(question: str, results: list[RetrievedChunk]) -> tuple[str, list[dict]]:
    # Vector similarity is only a ranking signal. A response requires meaningful
    # overlap with several content terms so random questions cannot be answered
    # from a merely nearby embedding bucket.
    query_terms = set(tokens(question))
    if not query_terms:
        return REFUSAL, []
    minimum_overlap = max(1, math.ceil(len(query_terms) * 0.25))
    strong = []
    for item in results:
        overlap = len(query_terms & set(tokens(item.chunk.text)))
        if overlap >= minimum_overlap:
            strong.append((overlap, item))
    if not strong:
        return REFUSAL, []
    strong.sort(key=lambda pair: (pair[0], 0.55 * pair[1].keyword_score + 0.45 * pair[1].vector_score), reverse=True)
    selected = [item for _, item in strong[:3]]
    citations = []
    for index, item in enumerate(selected, start=1):
        citations.append({"citation_id": f"C{index}", "chunk_id": str(item.chunk.id), "document_id": str(item.document_id), "version_id": str(item.version_id), "document_title": item.document_title, "page_no": item.page_no, "quote": _focused_excerpt(item.chunk.text, query_terms)})
    answer = "Relevant evidence from the approved documents:\n" + "\n".join(f"[{citation['citation_id']}] {citation['quote']}" for citation in citations)
    return answer, citations
