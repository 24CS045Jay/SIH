from __future__ import annotations

from app.models import Document, Role

BROAD_ROLES = {
    Role.SYSTEM_ADMINISTRATOR.value,
    Role.DOCUMENT_ADMINISTRATOR.value,
    Role.REVIEWER.value,
    Role.AUDITOR.value,
}


def can_access_document(document: Document, user: dict) -> bool:
    role = user.get("role")
    if role in BROAD_ROLES:
        return True
    if role == Role.EXECUTIVE_VIEWER.value:
        return document.sensitivity.value in {"public", "internal"}
    if role == Role.DEPARTMENT_USER.value:
        department_id = user.get("department_id")
        return bool(department_id and document.owner_id and str(document.owner.department_id if document.owner else "") == str(department_id))
    return False


def can_access_scope(scope: dict, user: dict) -> bool:
    role = user.get("role")
    if role in BROAD_ROLES:
        return True
    if role == Role.EXECUTIVE_VIEWER.value:
        return scope.get("sensitivity", "internal") in {"public", "internal"}
    if role == Role.DEPARTMENT_USER.value:
        department_id = user.get("department_id")
        scoped_department = scope.get("department_id")
        return bool(department_id and scoped_department and str(department_id) == str(scoped_department))
    return False
