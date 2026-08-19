from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class StructuredChunk:
    text: str
    page_no: int
    section: str | None
    section_title: str | None
    subsection: str | None
    chunk_index: int
    token_count: int
    ocr_confidence: float
    parent_context: str | None = None


_HEADING_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)\s*[.\-:]?\s+(.{3,})$")
_LIST_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)]|[a-z][.)])\s+")
_TABLE_RE = re.compile(r"\|+|\s{2,}\S+\s{2,}\S+")


def _tokens(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text, flags=re.UNICODE)


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 140:
        return False
    if stripped.isupper() and len(stripped.split()) <= 14:
        return True
    return bool(_HEADING_RE.fullmatch(stripped))


def _heading_parts(line: str) -> tuple[str | None, str]:
    stripped = line.strip()
    match = _HEADING_RE.fullmatch(stripped)
    if match:
        return match.group(1), match.group(2).strip()
    return None, stripped


def _paragraph_units(text: str) -> list[str]:
    units: list[str] = []
    buffer: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            if buffer:
                units.append(" ".join(buffer).strip())
                buffer = []
            continue
        if _is_heading(line) or _LIST_RE.match(line) or _TABLE_RE.search(line):
            if buffer:
                units.append(" ".join(buffer).strip())
                buffer = []
            units.append(line)
        else:
            buffer.append(line)
    if buffer:
        units.append(" ".join(buffer).strip())
    return [unit for unit in units if unit]


def chunk_pages(pages: list[tuple[int, str, float]], target_tokens: int = 360, max_tokens: int = 520) -> list[StructuredChunk]:
    chunks: list[StructuredChunk] = []
    section: str | None = None
    section_title: str | None = None
    subsection: str | None = None
    index = 0
    for page_no, text, confidence in pages:
        units = _paragraph_units(text or "")
        buffer: list[str] = []
        buffer_tokens = 0
        parent_context: str | None = None

        def flush() -> None:
            nonlocal index, buffer, buffer_tokens, parent_context
            if not buffer:
                return
            value = " ".join(buffer).strip()
            if value:
                context = " — ".join(item for item in (section, section_title, subsection) if item)
                chunks.append(StructuredChunk(value, page_no, section, section_title, subsection, index, len(_tokens(value)), confidence, context or parent_context))
                index += 1
            buffer = []
            buffer_tokens = 0
            parent_context = None

        for unit in units:
            if _is_heading(unit):
                flush()
                number, title = _heading_parts(unit)
                if number and number.count(".") >= 2:
                    subsection = title
                else:
                    section, section_title = number, title
                    subsection = None
                parent_context = title
                continue
            unit_tokens = len(_tokens(unit))
            if buffer and buffer_tokens + unit_tokens > max_tokens:
                flush()
            buffer.append(unit)
            buffer_tokens += unit_tokens
            if buffer_tokens >= target_tokens:
                flush()
        flush()
    return chunks
