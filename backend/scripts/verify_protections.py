from pathlib import Path
import sys
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import get_settings
from app.models import AuditEvent, Document, DocumentClassification, DocumentVersion, Sensitivity, VersionStatus

engine = create_engine(get_settings().database_url.replace("+asyncpg", "+psycopg"))

with Session(engine) as session:
    owner = session.query(__import__("app.models", fromlist=["User"]).User).first()
    document = Document(owner_id=owner.id, title="Temporary protection test", type="synthetic", classification=DocumentClassification.OTHER, sensitivity=Sensitivity.INTERNAL)
    session.add(document)
    session.flush()
    version = DocumentVersion(document_id=document.id, version_label="v-test", hash=str(uuid4()), status=VersionStatus.READY)
    session.add(version)
    session.flush()
    version.version_label = "blocked-update"
    try:
        session.flush()
    except ValueError as exc:
        print(f"document_versions update blocked: {exc}")
        session.rollback()
    else:
        raise AssertionError("document_versions update was not blocked")

    audit = AuditEvent(actor_id=None, event_type="verification", object_type="test", object_id=uuid4(), hash="synthetic")
    session.add(audit)
    session.flush()
    session.delete(audit)
    try:
        session.flush()
    except ValueError as exc:
        print(f"audit_events delete blocked: {exc}")
    else:
        raise AssertionError("audit_events delete was not blocked")
    session.rollback()
