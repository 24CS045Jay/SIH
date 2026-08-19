from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag import build_chunks


async def index_version(session: AsyncSession, version_id: UUID) -> int:
    """Index an OCR-complete version through structure-aware chunking and embeddings."""
    return await build_chunks(session, version_id)
