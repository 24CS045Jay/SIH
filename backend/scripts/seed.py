"""Seed synthetic Phase 2 reference data only.

No documents, versions, files, pages, actions, or audit events are created here.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.models import Department, Role, User, UserStatus


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


def demo_password_hash() -> str:
    return "sha256$" + hashlib.sha256(b"demo-password").hexdigest()


def main() -> None:
    settings = get_settings()
    database_url = settings.database_url.replace("+asyncpg", "+psycopg")
    engine = create_engine(database_url, pool_pre_ping=True)
    with Session(engine) as session:
        departments = {}
        for name in DEPARTMENT_NAMES:
            department = session.scalar(select(Department).where(Department.name == name))
            if department is None:
                department = Department(name=name)
                session.add(department)
                session.flush()
            departments[name] = department

        for name, email, role, department_name in DEMO_USERS:
            user = session.scalar(select(User).where(User.email == email))
            if user is None:
                session.add(User(name=name, email=email, password_hash=demo_password_hash(), role=role, status=UserStatus.ACTIVE, department=departments[department_name]))
        session.commit()
    print(f"Seeded {len(DEPARTMENT_NAMES)} departments and {len(DEMO_USERS)} synthetic demo users. Documents remain empty.")


if __name__ == "__main__":
    main()
