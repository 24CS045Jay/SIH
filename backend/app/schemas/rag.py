from __future__ import annotations

from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class RAGRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=3, max_length=2000)
    document_id: UUID | None = None
    scope: str | None = Field(default=None, pattern="^(document|all)$")


class Citation(BaseModel):
    citation_id: str
    chunk_id: UUID
    document_id: UUID
    version_id: UUID
    document_title: str
    page_no: int
    section_number: str | None = None
    section_title: str | None = None
    quote: str
    source_url: str


class RAGResponse(BaseModel):
    answer: str
    refusal: bool
    citations: list[Citation]
    disclaimer: str = "AI-generated answer — verify against source"
    scope: str | None = None
    refusal_reason: str | None = None
    diagnostics: dict | None = None
