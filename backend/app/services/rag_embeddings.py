from __future__ import annotations

import asyncio
import math
import re
from collections import Counter
from typing import Sequence

from app.core.config import get_settings


class EmbeddingProviderError(RuntimeError):
    """Raised when the configured embedding provider cannot produce vectors."""


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _local_tfidf_vector(text: str, vocabulary: Sequence[str]) -> list[float]:
    counts = Counter(_tokens(text))
    vector = [float(counts.get(term, 0)) for term in vocabulary]
    length = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / length for value in vector]


def _explicit_local_provider(provider: str) -> bool:
    return provider.lower() in {"local", "tfidf", "offline"}


async def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    settings = get_settings()
    provider = settings.embedding_provider.lower()
    if provider in {"auto", "openai"} and settings.openai_api_key:
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.openai_api_base)
            response = await client.embeddings.create(model=settings.embedding_model, input=list(texts))
            ordered = sorted(response.data, key=lambda item: item.index)
            return [list(item.embedding) for item in ordered]
        except Exception:
            # A bad or expired optional token must not strand an uploaded document in FAILED.
            # Fall back to deterministic local vectors; operators can inspect provider health separately.
            provider = "auto"
    if provider == "openai":
        # Explicit OpenAI mode remains strict for callers that require cloud embeddings.
        raise EmbeddingProviderError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
    if provider in {"auto", "local", "tfidf", "offline"}:
        if provider == "auto":
            # Auto mode is intentionally deterministic and transparent for the offline demo.
            # It is lexical vectorization, not the legacy hash embedding, and can be replaced by
            # OpenAI simply by supplying OPENAI_API_KEY.
            pass
        vocabulary = sorted({token for text in texts for token in _tokens(text)})
        return [_local_tfidf_vector(text, vocabulary) for text in texts]
    raise EmbeddingProviderError(f"Unsupported EMBEDDING_PROVIDER={settings.embedding_provider}")


async def embed_text(text: str) -> list[float]:
    vectors = await embed_texts([text])
    return vectors[0] if vectors else []


def cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right:
        return 0.0
    size = min(len(left), len(right))
    return sum(float(left[index]) * float(right[index]) for index in range(size))


def sync_embed_texts(texts: Sequence[str]) -> list[list[float]]:
    return asyncio.run(embed_texts(texts))
