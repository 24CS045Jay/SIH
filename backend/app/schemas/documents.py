from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class UploadResponse(BaseModel):
    document_id: UUID
    version_id: UUID
    status: str
    duplicate: bool = False
    message: str


class DocumentListItem(BaseModel):
    id: UUID
    title: str
    type: str
    owner_name: str
    classification: str
    sensitivity: str
    created_at: datetime
    version_id: UUID
    version_label: str
    status: str
    uploaded_at: datetime
    processing_stage: str = "queued"
    error_message: str | None = None


class PageResponse(BaseModel):
    id: UUID
    page_no: int
    ocr_text: str | None
    ocr_confidence: float | None
    low_confidence: bool
    image_url: str | None


class DocumentDetail(BaseModel):
    document: DocumentListItem
    pages: list[PageResponse]
    source_url: str


class ProcessingStatusResponse(BaseModel):
    version_id: UUID
    status: str
    processing_stage: str = "queued"
    page_count: int
    low_confidence_pages: int
    error_message: str | None = None
