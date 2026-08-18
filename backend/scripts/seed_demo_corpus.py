from __future__ import annotations
import asyncio
import json
import os
from pathlib import Path
import sys
from urllib.request import Request, urlopen
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.jobs.ocr import process_version

API = os.getenv("KMRL_API_BASE", "http://127.0.0.1:8000/api/v1")
ROOT = Path(__file__).resolve().parent / "demo_corpus"
FILES = [
    ("Safety Circular S-101.pdf", "safety circular safety review deadline"),
    ("Maintenance Manual V2.pdf", "brake inspection frequency"),
    ("Maintenance Manual V3.pdf", "brake inspection frequency"),
    ("Purchase Order Correspondence P-44.pdf", "vendor purchase order"),
    ("Incident Report I-09.pdf", "incident platform door"),
    ("HR Training Notice H-12.pdf", "human factors training"),
    ("Environmental Compliance Note E-07.pdf", "environmental waste oil"),
]

def api(path: str, method: str = "GET", token: str | None = None, payload: dict | None = None, multipart: tuple[str, bytes] | None = None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    body = None
    if multipart:
        boundary = "----KMRLPhase9Boundary"
        filename, content = multipart
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: application/pdf\r\n\r\n").encode() + content + f"\r\n--{boundary}--\r\n".encode()
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif payload is not None:
        body = json.dumps(payload).encode(); headers["Content-Type"] = "application/json"
    with urlopen(Request(API + path, data=body, headers=headers, method=method)) as response:
        return response.status, json.loads(response.read())

def login() -> str:
    _, data = api("/auth/login", "POST", payload={"email": "reviewer.demo@kmrl.example", "password": "demo-password"})
    return data["access_token"]

def upload(token: str, path: Path) -> dict:
    _, data = api("/documents/upload", "POST", token=token, multipart=(path.name, path.read_bytes()))
    return data

async def main():
    token = login()
    results = []
    for filename, keyword in FILES:
        path = ROOT / filename
        data = upload(token, path)
        await process_version(str(data["version_id"]))
        results.append({"filename": filename, "document_id": data["document_id"], "version_id": data["version_id"], "keyword": keyword})
    ready = []
    for item in results:
        _, status = api(f"/documents/{item['document_id']}/status", token=token)
        assert status["status"] == "review_ready", status
        ready.append(status)
    _, comparisons = api("/comparisons", token=token)
    v2 = next(item for item in results if item["filename"] == "Maintenance Manual V2.pdf")
    v3 = next(item for item in results if item["filename"] == "Maintenance Manual V3.pdf")
    comparison = next(item for item in comparisons if item["new_version_id"] == v3["version_id"])
    _, detail = api(f"/comparisons/{comparison['id']}", token=token)
    assert len(detail["changes"]) == 3, detail
    rag_results = []
    for item in results:
        question = f"What does the approved document say about {item['keyword']}?"
        _, answer = api("/search/ask", "POST", token=token, payload={"question": question})
        assert answer["refusal"] is False and answer["citations"], {"filename": item["filename"], "answer": answer}
        rag_results.append({"filename": item["filename"], "citations": len(answer["citations"])})
    print(json.dumps({"processed_documents": len(results), "statuses": ready, "maintenance_manual_changes": len(detail["changes"]), "rag_results": rag_results}, indent=2, default=str))
    print("demo corpus seed verification passed")

if __name__ == "__main__": asyncio.run(main())
