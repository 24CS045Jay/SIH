from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings
REFUSAL = "Information not available in the approved documents"


@dataclass
class GuardrailDecision:
    allowed: bool
    reason: str


def evidence_gate(results: list, scope: str, document_id: str | None = None) -> GuardrailDecision:
    settings = get_settings()
    if not results:
        return GuardrailDecision(False, "no_relevant_evidence")
    if scope == "document" and document_id and any(str(item.document_id) != str(document_id) for item in results):
        return GuardrailDecision(False, "document_scope_mismatch")
    strong = [item for item in results if item.rerank_score >= settings.rag_min_rerank_score and item.combined_score >= settings.rag_min_relevance]
    if not strong:
        return GuardrailDecision(False, "below_relevance_threshold")
    if all(getattr(item, "suspicious_instruction", False) for item in strong):
        return GuardrailDecision(False, "instruction_like_evidence_only")
    return GuardrailDecision(True, "evidence_sufficient")


def refusal_response() -> str:
    return REFUSAL
