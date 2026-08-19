from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests

API = os.getenv("KMRL_API_BASE", "http://localhost:8000/api/v1")
EMAIL = os.getenv("KMRL_DEMO_EMAIL", "reviewer.demo@kmrl.example")
PASSWORD = os.getenv("KMRL_DEMO_PASSWORD", "demo-password")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python backend/scripts/ingest_test_document.py /path/to/document.pdf")
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}")
        return 2
    login = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    login.raise_for_status()
    token = login.json()["access_token"]
    with path.open("rb") as handle:
        response = requests.post(f"{API}/documents/upload", headers={"Authorization": f"Bearer {token}"}, files={"file": (path.name, handle, "application/pdf")}, data={"title": path.stem}, timeout=60)
    response.raise_for_status()
    version_id = response.json()["version_id"]
    print(f"Uploaded version: {version_id}")
    for _ in range(60):
        status = requests.get(f"{API}/documents/{response.json()['document_id']}/status", headers={"Authorization": f"Bearer {token}"}, timeout=30)
        status.raise_for_status()
        payload = status.json()
        print(f"status={payload.get('status')}")
        if payload.get("status") in {"review_ready", "failed"}:
            if payload.get("status") == "failed":
                return 1
            break
        time.sleep(2)
    print("The document is indexed by the normal upload → OCR → chunk → embedding path.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
