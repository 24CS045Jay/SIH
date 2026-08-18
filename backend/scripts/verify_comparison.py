from __future__ import annotations
import asyncio
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.jobs.ocr import process_version

BASE = "http://127.0.0.1:8032/api/v1"
ROOT = Path(__file__).resolve().parent

def api(path: str, method: str = "GET", token: str | None = None, payload: dict | None = None, multipart: tuple[str, bytes] | None = None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    body = None
    if multipart:
        boundary = "----KMRLPhase8Boundary"
        filename, content = multipart
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: text/plain\r\n\r\n").encode() + content + f"\r\n--{boundary}--\r\n".encode()
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif payload is not None:
        body = json.dumps(payload).encode(); headers["Content-Type"] = "application/json"
    with urlopen(Request(BASE + path, data=body, headers=headers, method=method)) as response:
        return response.status, json.loads(response.read())

def login():
    _, result = api("/auth/login", "POST", payload={"email": "reviewer.demo@kmrl.example", "password": "demo-password"})
    return result["access_token"]

def upload(token: str, path: Path):
    _, result = api("/documents/upload", "POST", token=token, multipart=(path.name, path.read_bytes()))
    return result

async def main():
    token = login()
    v2 = upload(token, ROOT / "maintenance_manual_v2.txt")
    await process_version(str(v2["version_id"]))
    v3 = upload(token, ROOT / "maintenance_manual_v3.txt")
    await process_version(str(v3["version_id"]))
    _, comparisons = api("/comparisons", token=token)
    comparison = next(item for item in comparisons if item["new_version_id"] == v3["version_id"])
    _, detail = api(f"/comparisons/{comparison['id']}", token=token)
    assert detail["status"] == "completed"
    assert len(detail["changes"]) == 3, detail
    quotes = " ".join((change.get("new_span") or {}).get("quote", "") for change in detail["changes"])
    assert "14 days" in quotes and "revised brake checklist" in quotes and "10 days" in quotes, quotes
    _, candidate = api(f"/comparisons/{comparison['id']}/changes/{detail['changes'][0]['id']}/action", "POST", token=token)
    assert candidate["status"] == "draft", candidate
    assert candidate["message"] == "Draft action candidate created for human review", candidate
    print("version_labels", v2.get("status"), v3.get("status"))
    print("exact_changes", len(detail["changes"]))
    print("change_types", [change["change_type"] for change in detail["changes"]])
    print("action_candidate", candidate["action_id"], candidate["status"])
    print("comparison verification passed")

if __name__ == "__main__": asyncio.run(main())
