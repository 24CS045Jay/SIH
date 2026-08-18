from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.models.base import ActionPriority, ChangeType, ComparisonStatus, ImpactLevel, ActionStatus

class ChangeResponse(BaseModel):
    id: UUID
    change_type: ChangeType
    old_span: dict | None
    new_span: dict | None
    impact: ImpactLevel
    interpretation: str
    affected_department: str | None
    priority: ActionPriority
    required_action: str | None
    action_id: UUID | None = None

class ComparisonResponse(BaseModel):
    id: UUID
    old_version_id: UUID
    new_version_id: UUID
    status: ComparisonStatus
    old_title: str | None = None
    new_title: str | None = None
    old_document_id: UUID | None = None
    new_document_id: UUID | None = None
    changes: list[ChangeResponse]
