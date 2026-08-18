from __future__ import annotations
from difflib import SequenceMatcher
import re
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import ActionPriority, Change, ChangeType, Comparison, ComparisonStatus, DocumentVersion, ImpactLevel, Page


def _paragraphs(pages: list[Page]) -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []
    for page in pages:
        for paragraph in re.split(r"\n\s*\n|\n(?=\d+\.|[-*])", page.ocr_text or ""):
            text = " ".join(paragraph.split()).strip()
            is_header = "KMRL DOCUMENT INTELLIGENCE PORTAL" in text or text.startswith("Fictional controlled copy") or re.fullmatch(r"Maintenance Manual V[23](?: — scanned supporting page)?", text, flags=re.IGNORECASE)
            if text and not is_header:
                rows.append((page.page_no, text))
    return rows


def _span(row: tuple[int, str] | None, side: str) -> dict[str, Any] | None:
    if row is None: return None
    page_no, text = row
    return {"side": side, "page_no": page_no, "text": text, "start": 0, "end": len(text), "quote": text}


def _interpret(old: str, new: str, change_type: ChangeType) -> tuple[str, str, ActionPriority, str, ImpactLevel]:
    combined = f"{old} {new}".lower()
    if "brake" in combined and ("day" in combined or "frequency" in combined or "inspection" in combined):
        return ("The required brake inspection interval has changed, affecting the maintenance control cadence.", "Rolling Stock Engineering", ActionPriority.CRITICAL, "Update the preventive-maintenance schedule and brief affected inspection teams.", ImpactLevel.CRITICAL)
    if "checklist" in combined:
        return ("A new checklist requirement has been added to the maintenance procedure.", "Maintenance/Quality", ActionPriority.HIGH, "Publish the new checklist and confirm completion for affected teams.", ImpactLevel.HIGH)
    if "deadline" in combined or "due" in combined or "within" in combined:
        return ("A new or changed deadline creates a time-bound compliance obligation.", "Safety/Compliance", ActionPriority.HIGH, "Record the deadline and assign an owner before the due date.", ImpactLevel.HIGH)
    if change_type == ChangeType.ADDED:
        return ("New operational text was added to the approved document.", "Maintenance Planning", ActionPriority.MEDIUM, "Review the added requirement and incorporate it into the operating plan.", ImpactLevel.MEDIUM)
    if change_type == ChangeType.REMOVED:
        return ("An existing requirement was removed from the document and should be checked for downstream impact.", "Maintenance Planning", ActionPriority.MEDIUM, "Confirm whether affected procedures and work instructions need revision.", ImpactLevel.MEDIUM)
    return ("The document text was modified and requires human review for operational impact.", "Maintenance Planning", ActionPriority.MEDIUM, "Review the changed text and update local procedures if required.", ImpactLevel.MEDIUM)


def compare_sections(old_pages: list[Page], new_pages: list[Page]) -> list[dict[str, Any]]:
    old = _paragraphs(old_pages); new = _paragraphs(new_pages)
    matcher = SequenceMatcher(a=[text for _, text in old], b=[text for _, text in new], autojunk=False)
    changes: list[dict[str, Any]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal": continue
        pairs: list[tuple[tuple[int, str] | None, tuple[int, str] | None, ChangeType]] = []
        width = max(i2 - i1, j2 - j1)
        for offset in range(width):
            old_row = old[i1 + offset] if i1 + offset < i2 else None
            new_row = new[j1 + offset] if j1 + offset < j2 else None
            ctype = ChangeType.MODIFIED if old_row and new_row else ChangeType.ADDED if new_row else ChangeType.REMOVED
            pairs.append((old_row, new_row, ctype))
        for old_row, new_row, ctype in pairs:
            old_text = old_row[1] if old_row else ""
            new_text = new_row[1] if new_row else ""
            interpretation, department, priority, required_action, impact = _interpret(old_text, new_text, ctype)
            changes.append({"change_type": ctype, "old_span": _span(old_row, "old"), "new_span": _span(new_row, "new"), "impact": impact, "interpretation": interpretation, "affected_department": department, "priority": priority, "required_action": required_action})
    return changes


async def compare_versions(session: AsyncSession, old_version_id, new_version_id) -> Comparison:
    existing = await session.scalar(select(Comparison).where(Comparison.old_version_id == old_version_id, Comparison.new_version_id == new_version_id))
    if existing: return existing
    old_pages = list((await session.execute(select(Page).where(Page.version_id == old_version_id).order_by(Page.page_no))).scalars().all())
    new_pages = list((await session.execute(select(Page).where(Page.version_id == new_version_id).order_by(Page.page_no))).scalars().all())
    comparison = Comparison(old_version_id=old_version_id, new_version_id=new_version_id, status=ComparisonStatus.PROCESSING)
    session.add(comparison); await session.flush()
    for data in compare_sections(old_pages, new_pages): session.add(Change(comparison_id=comparison.id, **data))
    comparison.status = ComparisonStatus.COMPLETED
    await session.flush()
    return comparison
