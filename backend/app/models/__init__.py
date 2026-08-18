from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from app.models.base import *
from app.models.entities import *


@event.listens_for(Session, "before_flush")
def enforce_immutable_and_append_only(session: Session, flush_context: object, instances: object) -> None:
    for obj in session.dirty:
        if isinstance(obj, DocumentVersion):
            changed = {attribute.key for attribute in inspect(obj).attrs if attribute.history.has_changes()}
            if changed - {"status"}:
                raise ValueError("document_versions are immutable; only processing status transitions are allowed")
        if isinstance(obj, AuditEvent):
            raise ValueError("audit_events are append-only and cannot be updated")
        if isinstance(obj, ActionEvent):
            raise ValueError("action_events are append-only and cannot be updated")
    for obj in session.deleted:
        if isinstance(obj, DocumentVersion):
            raise ValueError("document_versions are immutable and cannot be deleted")
        if isinstance(obj, AuditEvent):
            raise ValueError("audit_events are append-only and cannot be deleted")
        if isinstance(obj, ActionEvent):
            raise ValueError("action_events are append-only and cannot be deleted")


__all__ = [name for name in globals() if not name.startswith("_")]
