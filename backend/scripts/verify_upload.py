from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8022/api/v1"


def json_request(path: str, method: str = "GET", payload: dict | None = None, token: str | None = None):
    headers = {"Content-Type": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    request = Request(BASE + path, data=json.dumps(payload).encode() if payload else None, headers=headers, method=method)
    with urlopen(request) as response:
        return json.loads(response.read())


def upload(path: Path, token: str):
    boundary = "----kmrlphase4boundary"
    content = path.read_bytes()
    body = b"--" + boundary.encode() + b"\r\nContent-Disposition: form-data; name=\"file\"; filename=\"phase4-demo.pdf\"\r\nContent-Type: application/pdf\r\n\r\n" + content + b"\r\n--" + boundary.encode() + b"--\r\n"
    request = Request(BASE + "/documents/upload", data=body, headers={"Authorization": f"Bearer {token}", "Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
    with urlopen(request) as response:
        return json.loads(response.read())


login = json_request("/auth/login", "POST", {"email": "engineering.demo@kmrl.example", "password": "demo-password"})
token = login["access_token"]
result = upload(Path("/tmp/kmrl_phase4_demo2.pdf")
, token)
print("upload", result)
for _ in range(20):
    status = json_request(f"/documents/{result['document_id']}/status", token=token)
    print("status", status)
    if status["status"] in {"review_ready", "failed"}: break
    time.sleep(0.5)
detail = json_request(f"/documents/{result['document_id']}", token=token)
assert len(detail["pages"]) == 2, detail
assert any(page["low_confidence"] for page in detail["pages"]), detail
print("detail_pages", len(detail["pages"]), "low_confidence_pages", sum(page["low_confidence"] for page in detail["pages"]))
