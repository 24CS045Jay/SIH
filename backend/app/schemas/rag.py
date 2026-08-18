from __future__ import annotations

from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class RAGRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=3, max_length=2000)


class Citation(BaseModel):
    citation_id: str
    chunk_id: UUID
    document_id: UUID
    version_id: UUID
    document_title: str
    page_no: int
    quote: str
    source_url: str


class RAGResponse(BaseModel):
    answer: str
    refusal: bool
    citations: list[Citation]
    disclaimer: str = "AI-generated answer — verify against source"
