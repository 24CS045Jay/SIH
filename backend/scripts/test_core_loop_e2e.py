from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.jobs.ocr import process_version

API = os.getenv("KMRL_API_BASE", "http://127.0.0.1:8000/api/v1")
CORPUS = Path(__file__).resolve().parent / "demo_corpus" / "Safety Circular S-101.pdf"


def request(path: str, method: str = "GET", payload: dict | None = None, token: str | None = None, multipart: tuple[str, bytes] | None = None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None
    if multipart:
        boundary = "----KMRLPhase13Boundary"
        filename, content = multipart
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: application/pdf\r\n\r\n").encode() + content + f"\r\n--{boundary}--\r\n".encode()
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif payload is not None:
        body = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    try:
        with urlopen(Request(API + path, method=method, data=body, headers=headers)) as response:
            return response.status, response.headers.get("X-Trace-ID"), json.loads(response.read())
    except HTTPError as exc:
        return exc.code, exc.headers.get("X-Trace-ID"), json.loads(exc.read().decode())


def login(email: str) -> tuple[str, dict]:
    status, trace, data = request("/auth/login", "POST", {"email": email, "password": "demo-password"})
    assert status == 200 and trace, data
    return data["access_token"], data["user"]


def main() -> None:
    reviewer_token, reviewer = login("reviewer.demo@kmrl.example")
    owner_token, owner = login("engineering.demo@kmrl.example")
    audit_token, _ = login("auditor.demo@kmrl.example")
    assert CORPUS.exists(), CORPUS
    upload_bytes = CORPUS.read_bytes() + f"\n% phase13-rehearsal-{time.time_ns()}\n".encode()
    status, trace, uploaded = request("/documents/upload", "POST", token=reviewer_token, multipart=("Safety Circular S-101 Rehearsal.pdf", upload_bytes))
    assert status == 202 and trace, uploaded
    asyncio.run(process_version(str(uploaded["version_id"])))
    document_id = uploaded["document_id"]
    status, trace, processing = request(f"/documents/{document_id}/status", token=reviewer_token)
    assert status == 200 and trace and processing["status"] == "review_ready", processing
    status, trace, card = request(f"/documents/{document_id}/intelligence", token=reviewer_token)
    assert status == 200 and trace and card["classification"]["value"] and card["entities"], card
    status, trace, alerts = request(f"/alerts?status=draft", token=reviewer_token)
    assert status == 200 and trace, alerts
    alert = next(item for item in alerts if item["source_version_id"] == uploaded["version_id"])
    alert_id = alert["id"]
    status, _, denied = request(f"/alerts/{alert_id}/transition", "POST", {"target": "approved"}, reviewer_token)
    assert status == 409, denied
    status, _, reviewed = request(f"/alerts/{alert_id}/transition", "POST", {"target": "needs_review"}, reviewer_token)
    assert status == 200 and reviewed["status"] == "needs_review", reviewed
    status, _, approved = request(f"/alerts/{alert_id}/transition", "POST", {"target": "approved", "suggested_action": "Complete the circular control review and record evidence."}, reviewer_token)
    assert status == 200 and approved["status"] == "approved", approved
    status, _, shared = request(f"/alerts/{alert_id}/quick-share", "POST", {"assignee_id": owner["id"], "excerpt": approved["source_excerpt"] or approved["title"], "summary": "Synthetic circular control review", "action": approved["suggested_action"], "deadline": approved["deadline"]}, reviewer_token)
    assert status == 200 and shared["status"] == "assigned", shared
    status, _, action = request(f"/alerts/{alert_id}/create-action", "POST", token=reviewer_token)
    assert status == 200 and action["status"] == "open", action
    action_id = action["id"]
    for target in ("acknowledged", "in_progress", "completed"):
        status, _, action = request(f"/actions/{action_id}/transition", "POST", {"target": target, "detail": f"Phase 13 rehearsal: {target}", "completion_evidence": "Synthetic completion evidence recorded." if target == "completed" else None}, owner_token)
        assert status == 200 and action["status"] == target, action
    status, _, closed = request(f"/actions/{action_id}/transition", "POST", {"target": "closed", "detail": "Reviewer verified synthetic completion evidence."}, reviewer_token)
    assert status == 200 and closed["status"] == "closed" and len(closed["events"]) >= 5, closed
    status, trace, audit = request("/audit/events?limit=200", token=audit_token)
    assert status == 200 and trace, audit
    path_events = [item for item in audit["items"] if item.get("detail", {}).get("path", "").find(str(action_id)) >= 0 or item.get("detail", {}).get("path", "").find(str(alert_id)) >= 0 or item.get("detail", {}).get("path", "").find(str(document_id)) >= 0]
    event_types = {item["event_type"] for item in path_events}
    assert {"view", "edit", "share", "status_change"}.issubset(event_types), event_types
    print(json.dumps({"document_id": str(document_id), "intelligence_fields": len(card["entities"]), "alert_id": str(alert_id), "action_id": str(action_id), "final_status": closed["status"], "audit_event_types": sorted(event_types)}, indent=2))
    print("core loop integration verification passed")


if __name__ == "__main__":
    main()
