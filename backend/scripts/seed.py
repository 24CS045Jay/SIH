"""Seed synthetic Phase 2 & 3 reference data and demo documents.

Creates synthetic departments, demo RBAC users, and processes initial demo documents.
"""
from __future__ import annotations

import asyncio
import hashlib
from hashlib import sha256
from pathlib import Path
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.jobs.ocr import process_version
import app.models
from app.models import Base, Department, Document, DocumentClassification, DocumentVersion, File as StoredFile, Role, Sensitivity, User, UserStatus, VersionStatus
from app.services.storage import version_storage_path


DEPARTMENT_NAMES = [
    "Rolling Stock Engineering",
    "Maintenance/Quality",
    "Maintenance Planning",
    "Procurement/Finance",
    "Safety/Compliance",
    "HR/Training",
    "Executive",
]

DEMO_USERS = [
    ("System Administrator", "admin.demo@kmrl.example", Role.SYSTEM_ADMINISTRATOR, "Executive"),
    ("Document Administrator", "documents.demo@kmrl.example", Role.DOCUMENT_ADMINISTRATOR, "Maintenance Planning"),
    ("Review Lead", "reviewer.demo@kmrl.example", Role.REVIEWER, "Safety/Compliance"),
    ("Engineering User", "engineering.demo@kmrl.example", Role.DEPARTMENT_USER, "Rolling Stock Engineering"),
    ("Maintenance User", "maintenance.demo@kmrl.example", Role.DEPARTMENT_USER, "Maintenance/Quality"),
    ("Executive Viewer", "executive.demo@kmrl.example", Role.EXECUTIVE_VIEWER, "Executive"),
    ("Audit User", "auditor.demo@kmrl.example", Role.AUDITOR, "Safety/Compliance"),
]

DEMO_DOCUMENTS = [
    {
        "filename": "synthetic_circular.txt",
        "title": "Safety inspection of trainset TS-17 at Aluva Depot",
        "owner_email": "reviewer.demo@kmrl.example",
        "classification": DocumentClassification.REGULATION,
        "sensitivity": Sensitivity.INTERNAL,
        "content": """CIRCULAR No. KMRL/RS/2026/042
Date: 18/08/2026
To: Rolling Stock Engineering; Safety/Compliance; Maintenance Planning
Subject: Safety inspection of trainset TS-17 at Aluva Depot

All departments shall complete the safety inspection and submit the compliance report within 30 days. Maintenance Planning must schedule the inspection, and Rolling Stock Engineering must record asset TS-17 findings. The regulatory deadline is 18/09/2026. Estimated provision: INR 250000.""",
    },
    {
        "filename": "synthetic_maintenance_manual.txt",
        "title": "Brake inspection frequency change manual",
        "owner_email": "engineering.demo@kmrl.example",
        "classification": DocumentClassification.MAINTENANCE,
        "sensitivity": Sensitivity.INTERNAL,
        "content": """SYNTHETIC MAINTENANCE MANUAL MM-2026-09
Brake inspection frequency change

Effective 01/09/2026, brake inspections for trainset TS-17 and all Series-2 trainsets change from every 30 days to every 14 days. The affected stakeholders are Rolling Stock Engineering and Maintenance Planning. Maintenance Planning must update the preventive-maintenance schedule, and Rolling Stock Engineering must record the inspection result after each cycle. Safety/Compliance must verify the first completed cycle.""",
    },
    {
        "filename": "rolling_stock_quality_audit.txt",
        "title": "Rolling Stock Quality Audit Report 2026",
        "owner_email": "maintenance.demo@kmrl.example",
        "classification": DocumentClassification.ENGINEERING,
        "sensitivity": Sensitivity.PUBLIC,
        "content": """KMRL ROLLING STOCK QUALITY & MAINTENANCE AUDIT REPORT
Date: 15/08/2026
Department: Maintenance/Quality

1. OVERVIEW: Quarterly review of trainsets TS-01 through TS-25 operating on the Kochi Metro Line 1.
2. FINDINGS: HVAC performance across all trainsets met standard compliance thresholds. Brake pad wear rates on TS-17 require scheduled replacement before 25/09/2026.
3. COMPLIANCE: Safety/Compliance and Rolling Stock Engineering have confirmed zero critical incidents in Q2 2026.""",
    },
]


def demo_password_hash() -> str:
    return "sha256$" + hashlib.sha256(b"demo-password").hexdigest()


def main() -> None:
    settings = get_settings()
    url = settings.database_url
    if "+asyncpg" in url:
        database_url = url.replace("+asyncpg", "+psycopg")
    elif "+aiosqlite" in url:
        database_url = url.replace("+aiosqlite", "")
    else:
        database_url = url

    engine = create_engine(database_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)

    versions_to_process = []

    with Session(engine) as session:
        departments = {}
        for name in DEPARTMENT_NAMES:
            department = session.scalar(select(Department).where(Department.name == name))
            if department is None:
                department = Department(name=name)
                session.add(department)
                session.flush()
            departments[name] = department

        users_by_email = {}
        for name, email, role, department_name in DEMO_USERS:
            user = session.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(
                    name=name,
                    email=email,
                    password_hash=demo_password_hash(),
                    role=role,
                    status=UserStatus.ACTIVE,
                    department=departments[department_name],
                )
                session.add(user)
                session.flush()
            users_by_email[email] = user

        for doc_info in DEMO_DOCUMENTS:
            content_bytes = doc_info["content"].encode("utf-8")
            digest = sha256(content_bytes).hexdigest()
            existing_ver = session.scalar(select(DocumentVersion).where(DocumentVersion.hash == digest))
            if existing_ver is not None:
                continue

            owner = users_by_email[doc_info["owner_email"]]
            doc = Document(
                title=doc_info["title"],
                type="txt",
                owner_id=owner.id,
                classification=doc_info["classification"],
                sensitivity=doc_info["sensitivity"],
            )
            session.add(doc)
            session.flush()

            ver = DocumentVersion(
                document_id=doc.id,
                version_label="v1",
                hash=digest,
                status=VersionStatus.QUEUED,
            )
            session.add(ver)
            session.flush()

            path = version_storage_path(ver.id, doc_info["filename"])
            path.write_bytes(content_bytes)

            session.add(StoredFile(
                version_id=ver.id,
                object_key=str(path),
                mime_type="text/plain",
                size=len(content_bytes),
            ))
            versions_to_process.append(str(ver.id))

        for qv in session.scalars(select(DocumentVersion).where(DocumentVersion.status == VersionStatus.QUEUED)).all():
            if str(qv.id) not in versions_to_process:
                versions_to_process.append(str(qv.id))

        session.commit()

    print(f"Seeded {len(DEPARTMENT_NAMES)} departments and {len(DEMO_USERS)} synthetic demo users.")

    if versions_to_process:
        print(f"Processing OCR, Intelligence extraction, and RAG indexing for {len(versions_to_process)} demo documents...")
        for vid in versions_to_process:
            asyncio.run(process_version(vid))
        print("Demo documents processed successfully into review_ready state.")
    else:
        print("Demo documents already seeded.")


if __name__ == "__main__":
    main()
