from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

API = os.getenv("KMRL_API_BASE", "http://localhost:8000/api/v1")
EMAIL = os.getenv("KMRL_DEMO_EMAIL", "reviewer.demo@kmrl.example")
PASSWORD = os.getenv("KMRL_DEMO_PASSWORD", "demo-password")
REFUSAL = "Information not available in the approved documents"


def main() -> int:
    eval_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("rag_evaluation.json")
    cases = json.loads(eval_path.read_text())
    login = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    login.raise_for_status()
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    metrics = {"total": len(cases), "passed": 0, "retrieval_hits": 0, "refusal_correct": 0, "citation_valid": 0, "document_scope_correct": 0, "answer_supported": 0}
    for case in cases:
        response = requests.post(f"{API}/search/ask", headers=headers, json={"question": case["question"], "scope": case.get("scope", "all"), **({"document_id": case["document_id"]} if case.get("document_id") else {})}, timeout=60)
        payload = response.json()
        refused = payload.get("refusal") is True and payload.get("answer") == REFUSAL
        if case.get("expected_refusal"):
            metrics["refusal_correct"] += int(refused)
            passed = refused
        else:
            citations = payload.get("citations", [])
            hit = bool(citations)
            scope_ok = not case.get("expected_document_title") or any(case["expected_document_title"].lower() in citation.get("document_title", "").lower() for citation in citations)
            supported = not payload.get("refusal") and all(citation.get("quote") for citation in citations)
            metrics["retrieval_hits"] += int(hit)
            metrics["citation_valid"] += int(hit and supported)
            metrics["document_scope_correct"] += int(hit and scope_ok)
            metrics["answer_supported"] += int(supported)
            passed = hit and supported and scope_ok
        label = "PASS" if passed else "FAIL"
        print(f"[{label}] {case.get('id', 'case')}: {payload.get('answer', '')[:180]}")
        metrics["passed"] += int(passed)
        if not passed:
            print(json.dumps(payload, indent=2))
    print(json.dumps(metrics, indent=2))
    return 0 if metrics["passed"] == metrics["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
