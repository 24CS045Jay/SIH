from __future__ import annotations

from enum import Enum
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DocumentType(str, Enum):
    CIRCULAR = "circular"
    MAINTENANCE = "maintenance"
    INVOICE = "invoice"
    DIRECTIVE = "directive"
    REPORT = "report"
    POLICY = "policy"
    MEMO = "memo"
    INCIDENT = "incident"
    OTHER = "other"


class Span(StrictModel):
    page_no: int = Field(ge=1)
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    quote: str = Field(min_length=1)


class ClassificationPrediction(StrictModel):
    document_type: DocumentType
    confidence: float = Field(ge=0, le=1)
    evidence: Span


class EntityPrediction(StrictModel):
    entity_type: Literal["date", "department", "asset", "vendor", "location", "identifier", "money"]
    value: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    source_span: Span


class ActionPrediction(StrictModel):
    title: str = Field(min_length=1)
    suggested_department: str | None
    confidence: float = Field(ge=0, le=1)
    evidence: Span


class DeadlinePrediction(StrictModel):
    status: Literal["found", "no_deadline_found", "ambiguous"]
    explicit_date: str | None
    relative_text: str | None
    confidence: float = Field(ge=0, le=1)
    evidence: Span | None


class KeyFact(StrictModel):
    text: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    source_span: Span


class SummaryPrediction(StrictModel):
    executive_summary: str = Field(min_length=1, max_length=1200)
    key_facts: list[KeyFact] = Field(min_length=1, max_length=10)
    confidence: float = Field(ge=0, le=1)


class PriorityPrediction(StrictModel):
    priority: Literal["critical", "high", "medium", "low"]
    confidence: float = Field(ge=0, le=1)
    reason_codes: list[Literal["Safety-related change", "Regulatory deadline detected", "Explicit urgency", "Operational impact", "No elevated signal"]] = Field(min_length=1)
    evidence: list[Span] = Field(min_length=1)


class RoutingPrediction(StrictModel):
    department: Literal["Rolling Stock Engineering", "Maintenance/Quality", "Maintenance Planning", "Procurement/Finance", "Safety/Compliance", "HR/Training", "Executive"]
    confidence: float = Field(ge=0, le=1)
    why: str = Field(min_length=1)
    evidence: Span


class IntelligenceResult(StrictModel):
    classification: ClassificationPrediction
    entities: list[EntityPrediction] = Field(min_length=3)
    actions: list[ActionPrediction]
    deadline: DeadlinePrediction
    summary: SummaryPrediction
    priority: PriorityPrediction
    routing: RoutingPrediction


class IntelligenceFieldResponse(StrictModel):
    prediction_id: UUID
    field: str
    value: str
    confidence: float
    source_span: Span | None
    review_state: str
    source: Literal["AI-suggested", "human-entered"]


class IntelligenceCardResponse(StrictModel):
    version_id: UUID
    document_id: UUID
    title: str
    classification: IntelligenceFieldResponse
    summary: IntelligenceFieldResponse
    key_facts: list[IntelligenceFieldResponse]
    entities: list[IntelligenceFieldResponse]
    actions: list[IntelligenceFieldResponse]
    deadline: IntelligenceFieldResponse
    priority: IntelligenceFieldResponse
    routing: IntelligenceFieldResponse


class CorrectionRequest(StrictModel):
    field: str = Field(min_length=1)
    correction: str = Field(min_length=1)
    reason: Literal["incorrect_classification", "incorrect_entity", "incorrect_action", "incorrect_priority", "incorrect_routing", "other"]
