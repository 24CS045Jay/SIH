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

REFUSAL = "Information not available in the approved documents"
TOKEN_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = {"the", "is", "a", "an", "and", "or", "of", "for", "to", "in", "on", "what", "who", "how", "are", "was", "were", "this", "that", "from", "with"}


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


async def build_chunks(session: AsyncSession, version_id: UUID | str) -> int:
    vid = UUID(str(version_id)) if isinstance(version_id, str) else version_id
    version = await session.scalar(select(DocumentVersion).where(DocumentVersion.id == vid))
    if version is None: return 0
    doc_row = (await session.execute(select(Document, User).join(User, Document.owner_id == User.id).where(Document.id == version.document_id))).first()
    if doc_row is None: return 0
    document, owner = doc_row
    pages = (await session.execute(select(Page).where(Page.version_id == vid).order_by(Page.page_no))).scalars().all()
    await session.execute(delete(Chunk).where(Chunk.version_id == vid))
    count = 0
    for page in pages:
        for text in chunk_text(page.ocr_text or ""):
            scope = {"roles": [role.value for role in Role], "department_id": str(owner.department_id) if owner.department_id else None, "sensitivity": document.sensitivity.value}
            session.add(Chunk(version_id=vid, page_id=page.id, text=text, embedding_ref=json.dumps(embedding(text), separators=(",", ":")), access_scope=scope))
            count += 1
    await session.flush()
    return count


def allowed(scope: dict, user: dict) -> bool:
    role = user.get("role")
    if role in {Role.SYSTEM_ADMINISTRATOR.value, Role.DOCUMENT_ADMINISTRATOR.value, Role.REVIEWER.value, Role.AUDITOR.value}:
        return True
    roles = scope.get("roles") or []
    if roles and role not in roles: return False
    if role == Role.EXECUTIVE_VIEWER.value:
        return scope.get("sensitivity", "internal") in {"public", "internal"}
    department_id = user.get("department_id")
    return not scope.get("department_id") or scope.get("department_id") == department_id


async def retrieve(session: AsyncSession, question: str, user: dict, limit: int = 6) -> list[RetrievedChunk]:
    rows = (await session.execute(select(Chunk, Document.id, Document.title, DocumentVersion.id, Page.page_no).join(DocumentVersion, Chunk.version_id == DocumentVersion.id).join(Document, DocumentVersion.document_id == Document.id).join(Page, Chunk.page_id == Page.id).where(DocumentVersion.status == "review_ready"))).all()
    query_tokens = set(tokens(question))
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


def answer_from_evidence(question: str, results: list[RetrievedChunk]) -> tuple[str, list[dict]]:
    # Refusal safety gate: vector similarity may rank candidates, but an answer
    # requires meaningful lexical overlap with approved evidence as well.
    strong = [item for item in results if item.keyword_score >= 0.12]
    if not strong: return REFUSAL, []
    citations = [{"citation_id": f"C{i}", "chunk_id": str(item.chunk.id), "document_id": str(item.document_id), "version_id": str(item.version_id), "document_title": item.document_title, "page_no": item.page_no, "quote": item.chunk.text[:320]} for i, item in enumerate(strong, start=1)]
    evidence = " ".join(f"[{citation['citation_id']}] {citation['quote']}" for citation in citations)
    answer = f"Based on the approved evidence, {evidence}"
    return answer, citations
