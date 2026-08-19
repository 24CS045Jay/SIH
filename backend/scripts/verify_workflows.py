from __future__ import annotations
import json
from urllib.request import Request, urlopen

import os

BASE = os.getenv("KMRL_API_BASE", "http://127.0.0.1:8000/api/v1")

def request(path: str, method: str = "GET", payload: dict | None = None, token: str | None = None):
    headers = {"Content-Type": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    req = Request(BASE + path, data=json.dumps(payload).encode() if payload is not None else None, headers=headers, method=method)
    try:
        with urlopen(req) as response: return response.status, json.loads(response.read())
    except Exception as exc:
        if hasattr(exc, "code"):
            body = exc.read().decode()
            try:
                return exc.code, json.loads(body)
            except Exception:
                return exc.code, {"detail": body}
        raise

def login(email: str):
    status, data = request("/auth/login", "POST", {"email": email, "password": "demo-password"})
    assert status == 200, data
    return data["access_token"], data["user"]

reviewer_token, reviewer = login("reviewer.demo@kmrl.example")
owner_token, owner = login("engineering.demo@kmrl.example")
status, alerts = request("/alerts?priority=critical&status=draft", token=reviewer_token)
assert status == 200 and alerts, alerts
alert = alerts[-1]
status, denied = request(f"/alerts/{alert['id']}/transition", "POST", {"target": "approved"}, reviewer_token)
assert status == 409, denied
status, review = request(f"/alerts/{alert['id']}/transition", "POST", {"target": "needs_review", "suggested_action": "Inspect brake frequency change and update the maintenance schedule."}, reviewer_token)
assert status == 200 and review["status"] == "needs_review", review
status, approved = request(f"/alerts/{alert['id']}/transition", "POST", {"target": "approved", "title": "Brake inspection frequency change — review and route", "suggested_department": "Rolling Stock Engineering", "suggested_action": "Update the preventive-maintenance schedule and record the next inspection.", "detail": "Reviewer corrected the suggested action."}, reviewer_token)
assert status == 200 and approved["status"] == "approved", approved
status, shared = request(f"/alerts/{alert['id']}/quick-share", "POST", {"assignee_id": owner["id"], "excerpt": alert["source_excerpt"] or alert["title"], "summary": "Brake inspection frequency change", "action": approved["suggested_action"], "deadline": approved["deadline"]}, reviewer_token)
assert status == 200 and shared["status"] == "assigned", shared
status, action = request(f"/alerts/{alert['id']}/create-action", "POST", None, reviewer_token)
assert status == 200 and action["status"] == "open", action
action_id = action["id"]
for target, token, evidence in [("acknowledged", owner_token, None), ("in_progress", owner_token, None), ("completed", owner_token, "Completion evidence: maintenance schedule updated and inspection record attached in demo notes.")]:
    status, action = request(f"/actions/{action_id}/transition", "POST", {"target": target, "detail": f"Workflow verification: {target}", "completion_evidence": evidence}, token)
    assert status == 200 and action["status"] == target, action
status, closed = request(f"/actions/{action_id}/transition", "POST", {"target": "closed", "detail": "Reviewer verified completion evidence."}, reviewer_token)
assert status == 200 and closed["status"] == "closed", closed
assert len(closed["events"]) >= 4, closed
print("critical_gate", "passed")
print("alert_path", "draft -> needs_review -> approved -> assigned")
print("action_path", "open -> acknowledged -> in_progress -> completed -> closed")
print("timeline_events", len(closed["events"]))
print("workflow verification passed")
