from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, MetaData
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Role(str, Enum):
    SYSTEM_ADMINISTRATOR = "system_administrator"
    DOCUMENT_ADMINISTRATOR = "document_administrator"
    REVIEWER = "reviewer"
    DEPARTMENT_USER = "department_user"
    EXECUTIVE_VIEWER = "executive_viewer"
    AUDITOR = "auditor"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class DocumentClassification(str, Enum):
    ENGINEERING = "engineering"
    MAINTENANCE = "maintenance"
    INCIDENT = "incident"
    PROCUREMENT = "procurement"
    REGULATION = "regulation"
    ENVIRONMENT = "environment"
    HR = "hr"
    LEGAL = "legal"
    GOVERNANCE = "governance"
    OTHER = "other"


class Sensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"


class VersionStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    REVIEW_READY = "review_ready"
    FAILED = "failed"
    ARCHIVED = "archived"


class MalwareStatus(str, Enum):
    PENDING = "pending"
    CLEAN = "clean"
    INFECTED = "infected"
    QUARANTINED = "quarantined"


class ReviewerState(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CORRECTED = "corrected"


class ActionPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionStatus(str, Enum):
    PROPOSED = "proposed"
    PENDING_APPROVAL = "pending_approval"
    ASSIGNED = "assigned"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ActionEventType(str, Enum):
    CREATED = "created"
    APPROVED = "approved"
    ASSIGNED = "assigned"
    ACKNOWLEDGED = "acknowledged"
    STATUS_CHANGED = "status_changed"
    COMMENTED = "commented"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RoutingState(str, Enum):
    PENDING = "pending"
    RECOMMENDED = "recommended"
    APPROVED = "approved"
    ROUTED = "routed"
    DISMISSED = "dismissed"


class ComparisonStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ChangeType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"


class ImpactLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FeedbackReason(str, Enum):
    INCORRECT_CLASSIFICATION = "incorrect_classification"
    INCORRECT_ENTITY = "incorrect_entity"
    INCORRECT_ACTION = "incorrect_action"
    INCORRECT_PRIORITY = "incorrect_priority"
    INCORRECT_ROUTING = "incorrect_routing"
    OTHER = "other"


class UUIDPrimaryKeyMixin:
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
