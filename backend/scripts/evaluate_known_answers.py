from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

API = os.getenv("KMRL_API_BASE", "http://127.0.0.1:8000/api/v1")
ROOT = Path(__file__).resolve().parent


def api(path: str, method: str = "GET", payload: dict | None = None, token: str | None = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(payload).encode() if payload is not None else None
    with urlopen(Request(API + path, method=method, data=body, headers=headers)) as response:
        return response.status, json.loads(response.read())


def main() -> None:
    _, login = api("/auth/login", "POST", {"email": "reviewer.demo@kmrl.example", "password": "demo-password"})
    token = login["access_token"]
    questions = json.loads((ROOT / "known_answer_questions.json").read_text())
    results = []
    for item in questions:
        _, answer = api("/search/ask", "POST", {"question": item["question"]}, token)
        titles = {citation["document_title"] for citation in answer["citations"]}
        expected_titles = item.get("expected_titles", [])
        if item.get("refusal"):
            assert answer["refusal"] and answer["answer"] == "Information not available in the approved documents", (item, answer)
            matched = True
        else:
            assert not answer["refusal"] and len(answer["citations"]) >= item["minimum_citations"], (item, answer)
            matched = any(any(expected in title for title in titles) for expected in expected_titles)
            assert matched, {"id": item["id"], "question": item["question"], "titles": sorted(titles)}
        results.append({"id": item["id"], "refusal": answer["refusal"], "citations": len(answer["citations"]), "source_titles": sorted(titles), "expected_source_matched": matched})
    print(json.dumps({"questions": len(results), "results": results}, indent=2))
    print("known-answer RAG evaluation passed")


if __name__ == "__main__":
    main()
