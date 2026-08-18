from __future__ import annotations

import json
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8020/api/v1"


def request(path: str, method: str = "GET", payload: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request_obj = Request(f"{BASE}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request_obj) as response:
            return response.status, json.loads(response.read())
    except Exception as exc:
        return getattr(exc, "code", 500), json.loads(exc.read()) if hasattr(exc, "read") else {"detail": str(exc)}


status, demo_users = request("/auth/demo-users")
assert status == 200 and len(demo_users) == 7
roles = {user["role"] for user in demo_users}
expected = {"system_administrator", "document_administrator", "reviewer", "department_user", "executive_viewer", "auditor"}
assert expected.issubset(roles), roles

for user in demo_users:
    status, login = request("/auth/login", "POST", {"email": user["email"], "password": "demo-password"})
    assert status == 200, (user, login)
    token = login["access_token"]
    status, me = request("/auth/me", token=token)
    assert status == 200 and me["role"] == user["role"]
    denied_status, denied = request("/rbac/admin/users", token=token)
    if user["role"] in {"system_administrator", "document_administrator"}:
        assert denied_status == 200, (user, denied)
    else:
        assert denied_status == 403, (user, denied)
    print(f"{user['role']}: login=200, me=200, admin_endpoint={denied_status}")

print("All six seeded roles passed authentication and RBAC checks.")
