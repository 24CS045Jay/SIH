from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8025/api/v1"


def json_request(path: str, method: str = "GET", payload: dict | None = None, token: str | None = None):
    headers = {"Content-Type": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    request = Request(BASE + path, data=json.dumps(payload).encode() if payload else None, headers=headers, method=method)
    with urlopen(request) as response:
        return response.status, json.loads(response.read())


def upload(path: Path, token: str):
    boundary = "----kmrlphase5boundary"
    body = b"--" + boundary.encode() + b"\r\nContent-Disposition: form-data; name=\"file\"; filename=\"synthetic-circular.txt\"\r\nContent-Type: text/plain\r\n\r\n" + path.read_bytes() + b"\r\n--" + boundary.encode() + b"--\r\n"
    request = Request(BASE + "/documents/upload", data=body, headers={"Authorization": f"Bearer {token}", "Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
    with urlopen(request) as response:
        return json.loads(response.read())

status, login = json_request("/auth/login", "POST", {"email": "reviewer.demo@kmrl.example", "password": "demo-password"})
assert status == 200
token = login["access_token"]
result = upload(Path("/tmp/kmrl_synthetic_circular.txt"), token)
print("upload", result)
for _ in range(30):
    _, processing = json_request(f"/documents/{result['document_id']}/status", token=token)
    if processing["status"] in {"review_ready", "failed"}: break
    time.sleep(0.4)
assert processing["status"] == "review_ready", processing
status, card = json_request(f"/documents/{result['document_id']}/intelligence", token=token)
assert status == 200, card
assert card["classification"]["value"] == "circular", card
assert len(card["entities"]) >= 3, card
assert card["priority"]["value"] in {"critical", "high", "medium", "low"}, card
assert card["priority"]["confidence"] >= 0, card
assert card["deadline"]["value"] != "No deadline found", card
for item in [card["classification"], card["summary"], card["deadline"], card["priority"], card["routing"]] + card["entities"]:
    assert item["source_span"] is not None, item
field = card["classification"]["field"]
status, correction = json_request(f"/documents/{result['document_id']}/intelligence/corrections", "POST", {"field": field, "correction": "circular", "reason": "incorrect_classification"}, token)
assert status == 200 and correction["source"] == "human-entered", correction
print("status", processing["status"], "classification", card["classification"]["value"], "entities", len(card["entities"]), "priority", card["priority"]["value"], "reasons", card["priority"]["value"], "deadline", card["deadline"]["value"], "feedback", correction["source"])
print("Phase 5 synthetic circular verification passed.")
