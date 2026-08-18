from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.base import ActionPriority, ActionStatus, AlertStatus

class AlertTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target: AlertStatus
    title: str | None = None
    suggested_department: str | None = None
    suggested_action: str | None = None
    deadline: datetime | None = None
    detail: str = ""

class QuickShareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assignee_id: UUID
    excerpt: str = Field(min_length=1, max_length=2000)
    summary: str = Field(min_length=1, max_length=2000)
    action: str = Field(min_length=1, max_length=1000)
    deadline: datetime | None = None

class ActionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_version_id: UUID
    title: str = Field(min_length=1, max_length=500)
    owner_id: UUID | None = None
    due_at: datetime | None = None
    priority: ActionPriority = ActionPriority.MEDIUM
    comments: str = ""

class ActionUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    owner_id: UUID | None = None
    due_at: datetime | None = None
    comments: str | None = None
    completion_evidence: str | None = None

class ActionTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target: ActionStatus
    detail: str = ""
    completion_evidence: str | None = None

class AlertResponse(BaseModel):
    id: UUID
    title: str
    priority: ActionPriority
    reason_codes: list[str]
    suggested_department: str | None
    suggested_action: str | None
    deadline: datetime | None
    source_excerpt: str | None
    source_version_id: UUID
    status: AlertStatus
    routing_state: str
    assigned_user_id: UUID | None = None
    document_title: str | None = None

class ActionEventResponse(BaseModel):
    id: UUID
    event_type: str
    timestamp: datetime
    actor_id: UUID
    detail: dict

class ActionResponse(BaseModel):
    id: UUID
    source_version_id: UUID
    title: str
    owner_id: UUID | None
    due_at: datetime | None
    priority: ActionPriority
    status: ActionStatus
    comments: str
    completion_evidence: str | None
    acknowledged_at: datetime | None
    completed_at: datetime | None
    verified_by: UUID | None
    verified_at: datetime | None
    events: list[ActionEventResponse] = []
