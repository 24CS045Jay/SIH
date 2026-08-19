from __future__ import annotations

import re
from dataclasses import replace

from app.core.config import get_settings
from app.services.rag_embeddings import cosine

_INSTRUCTION_RE = re.compile(r"\b(ignore|disregard|override|follow these instructions|reveal|system prompt|mark this document)\b", re.I)
_NOISE_RE = re.compile(r"\b(distractor|no operational bearing|irrelevant detail|not operational)\b", re.I)


def rerank(question: str, candidates: list, query_vector: list[float]) -> list:
    settings = get_settings()
    query_terms = set(re.findall(r"[a-z0-9]+", question.lower()))
    ranked = []
    for item in candidates:
        text_terms = set(re.findall(r"[a-z0-9]+", item.chunk.text.lower()))
        overlap = len(query_terms & text_terms) / max(1, len(query_terms))
        phrase_bonus = 0.12 if any(term in item.chunk.text.lower() for term in (question.lower(),)) else 0.0
        title_bonus = 0.10 if any(term in item.document_title.lower() for term in query_terms if len(term) > 4) else 0.0
        ocr_penalty = settings.rag_low_ocr_penalty if getattr(item, "ocr_confidence", 1.0) < settings.low_ocr_confidence_threshold else 0.0
        instruction_match = _INSTRUCTION_RE.search(item.chunk.text)
        safe_units = [unit for unit in re.split(r"(?<=[.!?])\s+|\n+", item.chunk.text) if unit.strip() and not _INSTRUCTION_RE.search(unit)]
        instruction_penalty = (0.05 if safe_units else 0.22) if instruction_match else 0.0
        noise_penalty = 0.30 if _NOISE_RE.search(item.chunk.text) and not safe_units else 0.0
        score = 0.40 * item.vector_score + 0.35 * item.keyword_score + 0.15 * overlap + phrase_bonus + title_bonus - ocr_penalty - instruction_penalty - noise_penalty
        ranked.append(replace(item, rerank_score=max(0.0, min(1.0, score)), suspicious_instruction=bool(_INSTRUCTION_RE.search(item.chunk.text))))
    return sorted(ranked, key=lambda item: item.rerank_score, reverse=True)


def suspicious_instruction(text: str) -> bool:
    return bool(_INSTRUCTION_RE.search(text))
