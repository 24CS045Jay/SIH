from __future__ import annotations

from typing import Iterable

from app.services.rag import REFUSAL


def validate_citations(answer: str, citations: list[dict], evidence_ids: Iterable[str]) -> tuple[str, list[dict]]:
    allowed = {str(item) for item in evidence_ids}
    valid = [citation for citation in citations if str(citation.get("chunk_id")) in allowed and citation.get("quote") and citation.get("document_id") and citation.get("version_id")]
    if answer != REFUSAL and not valid:
        return REFUSAL, []
    return answer, valid
