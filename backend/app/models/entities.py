from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    ActionEventType, ActionPriority, ActionStatus, AlertStatus, Base, ChangeType, ComparisonStatus,
    CreatedAtMixin, DocumentClassification, FeedbackReason, ImpactLevel, MalwareStatus,
    ReviewerState, Role, RoutingState, Sensitivity, UUIDPrimaryKeyMixin, UserStatus,
    VersionStatus,
)


def enum_type(enum_cls: type) -> SAEnum:
    return SAEnum(enum_cls, name=enum_cls.__name__.lower(), native_enum=True, values_callable=lambda values: [item.value for item in values])


class Department(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "departments"
    name: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    parent: Mapped["Department | None"] = relationship(remote_side="Department.id", back_populates="children")
    children: Mapped[list["Department"]] = relationship(back_populates="parent")
    users: Mapped[list["User"]] = relationship(back_populates="department")


class User(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "users"
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(enum_type(Role), nullable=False, index=True)
    department_id: Mapped[UUID | None] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[UserStatus] = mapped_column(enum_type(UserStatus), nullable=False, default=UserStatus.ACTIVE, index=True)
    department: Mapped["Department | None"] = relationship(back_populates="users")
    owned_documents: Mapped[list["Document"]] = relationship(back_populates="owner", foreign_keys="Document.owner_id")
    owned_actions: Mapped[list["Action"]] = relationship(back_populates="owner", foreign_keys="Action.owner_id")
    action_events: Mapped[list["ActionEvent"]] = relationship(back_populates="actor")
    assignments: Mapped[list["Assignment"]] = relationship(back_populates="assignee", foreign_keys="Assignment.assignee_id")
    audit_events: Mapped[list["AuditEvent"]] = relationship(back_populates="actor")
    feedback: Mapped[list["Feedback"]] = relationship(back_populates="reviewer")


class Document(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "documents"
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    type: Mapped[str] = mapped_column(String(120), nullable=False)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    classification: Mapped[DocumentClassification] = mapped_column(enum_type(DocumentClassification), nullable=False, index=True)
    sensitivity: Mapped[Sensitivity] = mapped_column(enum_type(Sensitivity), nullable=False, default=Sensitivity.INTERNAL, index=True)
    owner: Mapped["User"] = relationship(back_populates="owned_documents", foreign_keys=[owner_id])
    versions: Mapped[list["DocumentVersion"]] = relationship(back_populates="document", cascade="save-update, merge", passive_deletes=True)


class DocumentVersion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "document_versions"
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False, index=True)
    version_label: Mapped[str] = mapped_column(String(80), nullable=False)
    hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    status: Mapped[VersionStatus] = mapped_column(enum_type(VersionStatus), nullable=False, default=VersionStatus.PROCESSING, index=True)
    processing_stage: Mapped[str] = mapped_column(String(40), nullable=False, default="queued", index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    document: Mapped["Document"] = relationship(back_populates="versions")
    files: Mapped[list["File"]] = relationship(back_populates="version", cascade="save-update, merge", passive_deletes=True)
    pages: Mapped[list["Page"]] = relationship(back_populates="version", cascade="save-update, merge", passive_deletes=True)
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="version", cascade="save-update, merge", passive_deletes=True)
    extracted_facts: Mapped[list["ExtractedFact"]] = relationship(back_populates="version", cascade="save-update, merge", passive_deletes=True)
    actions: Mapped[list["Action"]] = relationship(back_populates="source_version")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="source_version")
    old_comparisons: Mapped[list["Comparison"]] = relationship(back_populates="old_version", foreign_keys="Comparison.old_version_id")
    new_comparisons: Mapped[list["Comparison"]] = relationship(back_populates="new_version", foreign_keys="Comparison.new_version_id")
    __table_args__ = (UniqueConstraint("document_id", "version_label", name="uq_document_versions_document_version_label"), Index("ix_document_versions_document_status", "document_id", "status"))


class File(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "files"
    version_id: Mapped[UUID] = mapped_column(ForeignKey("document_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(String(160), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    malware_status: Mapped[MalwareStatus] = mapped_column(enum_type(MalwareStatus), nullable=False, default=MalwareStatus.PENDING, index=True)
    version: Mapped["DocumentVersion"] = relationship(back_populates="files")


class Page(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "pages"
    version_id: Mapped[UUID] = mapped_column(ForeignKey("document_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    image_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(nullable=True)
    version: Mapped["DocumentVersion"] = relationship(back_populates="pages")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="page", cascade="save-update, merge", passive_deletes=True)
    __table_args__ = (UniqueConstraint("version_id", "page_no", name="uq_pages_version_page_no"), Index("ix_pages_version_page_no", "version_id", "page_no"))


class Chunk(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "chunks"
    version_id: Mapped[UUID] = mapped_column(ForeignKey("document_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    page_id: Mapped[UUID | None] = mapped_column(ForeignKey("pages.id", ondelete="SET NULL"), nullable=True, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_scope: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    section_number: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    section_title: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
    subsection: Mapped[str | None] = mapped_column(String(300), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ocr_confidence: Mapped[float | None] = mapped_column(nullable=True)
    parent_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped["DocumentVersion"] = relationship(back_populates="chunks")
    page: Mapped["Page | None"] = relationship(back_populates="chunks")


class ExtractedFact(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "extracted_facts"
    version_id: Mapped[UUID] = mapped_column(ForeignKey("document_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    field: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    source_span: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    confidence: Mapped[float] = mapped_column(nullable=False)
    reviewer_state: Mapped[ReviewerState] = mapped_column(enum_type(ReviewerState), nullable=False, default=ReviewerState.PENDING, index=True)
    version: Mapped["DocumentVersion"] = relationship(back_populates="extracted_facts")


class Action(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "actions"
    source_version_id: Mapped[UUID] = mapped_column(ForeignKey("document_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    owner_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    priority: Mapped[ActionPriority] = mapped_column(enum_type(ActionPriority), nullable=False, index=True)
    status: Mapped[ActionStatus] = mapped_column(enum_type(ActionStatus), nullable=False, default=ActionStatus.DRAFT, index=True)
    comments: Mapped[str] = mapped_column(Text, nullable=False, default="")
    completion_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    verified_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    source_version: Mapped["DocumentVersion"] = relationship(back_populates="actions")
    owner: Mapped["User | None"] = relationship(back_populates="owned_actions", foreign_keys=[owner_id])
    events: Mapped[list["ActionEvent"]] = relationship(back_populates="action", cascade="save-update, merge", passive_deletes=True)
    assignments: Mapped[list["Assignment"]] = relationship(back_populates="action")
    __table_args__ = (Index("ix_actions_status_priority_due_at", "status", "priority", "due_at"),)


class ActionEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "action_events"
    action_id: Mapped[UUID] = mapped_column(ForeignKey("actions.id", ondelete="RESTRICT"), nullable=False, index=True)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    event_type: Mapped[ActionEventType] = mapped_column(enum_type(ActionEventType), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    action: Mapped["Action"] = relationship(back_populates="events")
    actor: Mapped["User"] = relationship(back_populates="action_events")


class Alert(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "alerts"
    source_version_id: Mapped[UUID] = mapped_column(ForeignKey("document_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="AI-generated alert")
    priority: Mapped[ActionPriority] = mapped_column(enum_type(ActionPriority), nullable=False, index=True)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    suggested_department: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    suggested_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    source_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[AlertStatus] = mapped_column(enum_type(AlertStatus), nullable=False, default=AlertStatus.DRAFT, index=True)
    routing_state: Mapped[RoutingState] = mapped_column(enum_type(RoutingState), nullable=False, default=RoutingState.PENDING, index=True)
    source_version: Mapped["DocumentVersion"] = relationship(back_populates="alerts")
    assignments: Mapped[list["Assignment"]] = relationship(back_populates="alert")


class Assignment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assignments"
    alert_id: Mapped[UUID | None] = mapped_column(ForeignKey("alerts.id", ondelete="RESTRICT"), nullable=True, index=True)
    action_id: Mapped[UUID | None] = mapped_column(ForeignKey("actions.id", ondelete="RESTRICT"), nullable=True, index=True)
    assignee_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    assigned_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    alert: Mapped["Alert | None"] = relationship(back_populates="assignments")
    action: Mapped["Action | None"] = relationship(back_populates="assignments")
    assignee: Mapped["User"] = relationship(back_populates="assignments", foreign_keys=[assignee_id])
    assigner: Mapped["User"] = relationship(foreign_keys=[assigned_by])


class Comparison(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "comparisons"
    old_version_id: Mapped[UUID] = mapped_column(ForeignKey("document_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    new_version_id: Mapped[UUID] = mapped_column(ForeignKey("document_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    status: Mapped[ComparisonStatus] = mapped_column(enum_type(ComparisonStatus), nullable=False, default=ComparisonStatus.PENDING, index=True)
    old_version: Mapped["DocumentVersion"] = relationship(back_populates="old_comparisons", foreign_keys=[old_version_id])
    new_version: Mapped["DocumentVersion"] = relationship(back_populates="new_comparisons", foreign_keys=[new_version_id])
    changes: Mapped[list["Change"]] = relationship(back_populates="comparison", cascade="save-update, merge", passive_deletes=True)
    __table_args__ = (Index("ix_comparisons_versions", "old_version_id", "new_version_id"),)


class Change(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "changes"
    comparison_id: Mapped[UUID] = mapped_column(ForeignKey("comparisons.id", ondelete="CASCADE"), nullable=False, index=True)
    change_type: Mapped[ChangeType] = mapped_column(enum_type(ChangeType), nullable=False, index=True)
    old_span: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    new_span: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    impact: Mapped[ImpactLevel] = mapped_column(enum_type(ImpactLevel), nullable=False, index=True)
    interpretation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    affected_department: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    priority: Mapped[ActionPriority] = mapped_column(enum_type(ActionPriority), nullable=False, default=ActionPriority.MEDIUM, index=True)
    required_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    comparison: Mapped["Comparison"] = relationship(back_populates="changes")


class AuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_events"
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    object_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    object_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    hash: Mapped[str] = mapped_column(String(128), nullable=False)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    actor: Mapped["User | None"] = relationship(back_populates="audit_events")
    __table_args__ = (Index("ix_audit_events_object_timestamp", "object_type", "object_id", "timestamp"),)


class Feedback(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "feedback"
    prediction_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    reviewer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    correction: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[FeedbackReason] = mapped_column(enum_type(FeedbackReason), nullable=False, index=True)
    reviewer: Mapped["User"] = relationship(back_populates="feedback")
