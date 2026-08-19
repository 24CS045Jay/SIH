from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag import RetrievedChunk, retrieve


async def retrieve_hybrid(session: AsyncSession, question: str, user: dict, *, scope: str = "all", document_id: UUID | None = None, limit: int | None = None) -> list[RetrievedChunk]:
    return await retrieve(session, question, user, limit=limit, document_id=document_id, scope=scope)
