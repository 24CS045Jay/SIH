from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8027/api/v1"


def json_request(path: str, method: str = "GET", payload: dict | None = None, token: str | None = None):
    headers = {"Content-Type": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    request = Request(BASE + path, data=json.dumps(payload).encode() if payload else None, headers=headers, method=method)
    with urlopen(request) as response:
        return response.status, json.loads(response.read())


def upload(path: Path, token: str):
    boundary = "----kmrlphase6boundary"
    body = b"--" + boundary.encode() + b"\r\nContent-Disposition: form-data; name=\"file\"; filename=\"synthetic-maintenance-manual.txt\"\r\nContent-Type: text/plain\r\n\r\n" + path.read_bytes() + b"\r\n--" + boundary.encode() + b"--\r\n"
    request = Request(BASE + "/documents/upload", data=body, headers={"Authorization": f"Bearer {token}", "Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
    with urlopen(request) as response:
        return json.loads(response.read())

_, login = json_request("/auth/login", "POST", {"email": "engineering.demo@kmrl.example", "password": "demo-password"})
token = login["access_token"]
result = upload(Path("/tmp/kmrl_synthetic_maintenance_manual.txt"), token)
print("upload", result)
for _ in range(30):
    _, state = json_request(f"/documents/{result['document_id']}/status", token=token)
    if state["status"] in {"review_ready", "failed"}: break
    time.sleep(0.4)
assert state["status"] == "review_ready", state
_, answer = json_request("/search/ask", "POST", {"question": "What changed in the brake inspection frequency, who is affected, and what action is required?"}, token)
assert answer["refusal"] is False and answer["citations"], answer
assert "30 days" in answer["answer"] and "14 days" in answer["answer"], answer
assert all(item["source_url"].endswith("/source") and item["page_no"] >= 1 for item in answer["citations"])
_, refusal = json_request("/search/ask", "POST", {"question": "What is the approved cafeteria menu for next Tuesday?"}, token)
assert refusal["refusal"] is True and refusal["answer"] == "Information not available in the approved documents", refusal
print("in_corpus", answer["answer"][:220], "citations", len(answer["citations"]))
print("out_of_corpus", refusal["answer"])
print("Phase 6 RAG verification passed.")
