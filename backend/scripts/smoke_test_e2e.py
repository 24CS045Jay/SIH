"""Fast pre-demo smoke test for the live KMRL API.

Usage:
  KMRL_API_BASE=http://localhost:8000/api/v1 python scripts/smoke_test_e2e.py

The script uses real seeded users and never inserts directly into the database.
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path
from urllib import error, request

BASE = os.getenv("KMRL_API_BASE", "http://localhost:8000/api/v1").rstrip("/")
PASSWORD = os.getenv("KMRL_DEMO_PASSWORD", "demo-password")
TIMEOUT = float(os.getenv("KMRL_SMOKE_TIMEOUT", "15"))


def request_json(method: str, path: str, *, headers: dict[str, str] | None = None, body: dict | None = None) -> dict | list:
    payload = json.dumps(body).encode() if body is not None else None
    request_headers = {"Accept": "application/json", **(headers or {})}
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
    req = request.Request(f"{BASE}{path}", data=payload, headers=request_headers, method=method)
    try:
        with request.urlopen(req, timeout=TIMEOUT) as response:
            return json.loads(response.read().decode())
    except error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:300]
        raise RuntimeError(f"{method} {path} -> HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"{method} {path} -> network error: {exc.reason}") from exc


def upload_text(path: str, headers: dict[str, str], file_path: Path) -> dict:
    boundary = f"----kmrl-smoke-{uuid.uuid4().hex}"
    content = file_path.read_bytes()
    parts = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{file_path.name}\"\r\nContent-Type: text/plain\r\n\r\n".encode(),
        content,
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    body = b"".join(parts)
    req_headers = {**headers, "Content-Type": f"multipart/form-data; boundary={boundary}", "Content-Length": str(len(body))}
    req = request.Request(f"{BASE}{path}", data=body, headers=req_headers, method="POST")
    try:
        with request.urlopen(req, timeout=TIMEOUT) as response:
            return json.loads(response.read().decode())
    except error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:300]
        raise RuntimeError(f"POST {path} -> HTTP {exc.code}: {detail}") from exc


def main() -> int:
    health = request_json("GET", "/health")
    assert health.get("status") in {"ok", "degraded"}, health
    users = request_json("GET", "/auth/demo-users")
    assert isinstance(users, list) and users, "No seeded demo users returned"
    user = next((item for item in users if item.get("role") == "system_administrator"), users[0])
    def login_headers(selected: dict) -> dict[str, str]:
        login = request_json("POST", "/auth/login", body={"email": selected["email"], "password": PASSWORD})
        return {"Authorization": f"Bearer {login['access_token']}"}
    headers = login_headers(user)
    for path in ("/auth/me", "/dashboard/summary", "/documents"):
        request_json("GET", path, headers=headers)
    auditor = next((item for item in users if item.get("role") == "auditor"), None)
    audit_headers = login_headers(auditor) if auditor else headers
    for path in ("/audit/events", "/audit/governance"):
        request_json("GET", path, headers=audit_headers)

    fixture = Path(os.getenv("KMRL_SMOKE_FILE", "/tmp/kmrl-smoke.txt"))
    run_marker = uuid.uuid4().hex[:10]
    fixture.write_text(f"KMRL smoke-test document {run_marker}. Brake inspection evidence is reviewed by the Maintenance Planning department.", encoding="utf-8")
    upload = upload_text("/documents/upload", headers, fixture)
    document_id = upload["document_id"]

    status = None
    for _ in range(30):
        status = request_json("GET", f"/documents/{document_id}/status", headers=headers)
        if status.get("status") in {"review_ready", "failed"}:
            break
        time.sleep(1)
    if status is None or status.get("status") != "review_ready":
        raise RuntimeError(f"Smoke upload did not reach review_ready: {status}")

    answer = request_json("POST", "/search/ask", headers=headers, body={"question": "What evidence is reviewed by the Maintenance Planning department?", "scope": "document", "document_id": document_id})
    assert answer.get("refusal") is False, answer
    assert answer.get("citations"), answer
    print(f"SMOKE_PASS user={user['email']} document={document_id} citations={len(answer['citations'])}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"SMOKE_FAIL {exc}", file=sys.stderr)
        raise
