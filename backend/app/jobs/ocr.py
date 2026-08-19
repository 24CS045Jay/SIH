from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

from sqlalchemy import delete, select

from uuid import UUID

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.jobs.celery_app import celery_app
from app.models import DocumentVersion, File, Page, VersionStatus
from app.services.intelligence import analyze_pages
from app.services.intelligence_persistence import persist_intelligence
from app.services.rag import build_chunks
from app.services.comparison import compare_versions


def extract_pages(path: Path, mime_type: str) -> list[tuple[str, float]]:
    if mime_type == "text/plain" or path.suffix.lower() in {".txt", ".md", ".csv"}:
        return [(path.read_text(errors="replace"), 0.98)]
    if mime_type == "application/pdf" or path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            extracted: list[tuple[str, float]] = []
            for page in reader.pages:
                text = (page.extract_text() or "").strip()
                low_quality_marker = any(marker in text.lower() for marker in ("low quality", "low-confidence", "faded ink", "faint stamp", "low-contrast"))
                extracted.append((text, 0.46 if low_quality_marker or len(text) < 40 else 0.92))
            if extracted and any(t for t, _ in extracted):
                return extracted
        except Exception:
            pass
        info = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=False)
        pages = 1
        for line in info.stdout.splitlines():
            if line.startswith("Pages:"):
                pages = int(line.split(":", 1)[1].strip())
        extracted = []
        for page_no in range(1, pages + 1):
            result = subprocess.run(["pdftotext", "-layout", "-f", str(page_no), "-l", str(page_no), str(path), "-"], capture_output=True, text=True, check=False)
            text = result.stdout.strip()
            low_quality_marker = any(marker in text.lower() for marker in ("low quality", "low-confidence", "faded ink", "faint stamp", "low-contrast"))
            extracted.append((text, 0.46 if low_quality_marker or len(text) < 40 else 0.92))
        return extracted
    try:
        result = subprocess.run(["tesseract", str(path), "stdout"], capture_output=True, text=True, check=False)
        text = result.stdout.strip()
        return [(text, 0.88 if len(text) >= 30 and result.returncode == 0 else 0.42)]
    except FileNotFoundError:
        return [("OCR engine unavailable in local demo environment.", 0.35)]


async def process_version(version_id: str | UUID) -> None:
    vid = UUID(str(version_id)) if isinstance(version_id, str) else version_id
    settings = get_settings()
    async with AsyncSessionLocal() as session:
        version = await session.scalar(select(DocumentVersion).where(DocumentVersion.id == vid))
        source = await session.scalar(select(File).where(File.version_id == vid))
        if version is None or source is None:
            return
        version.status = VersionStatus.PROCESSING
        await session.commit()
        try:
            page_data = extract_pages(Path(source.object_key), source.mime_type)
            await session.execute(delete(Page).where(Page.version_id == version.id))
            for page_no, (text, confidence) in enumerate(page_data, start=1):
                session.add(Page(version_id=version.id, page_no=page_no, image_key=source.object_key, ocr_text=text, ocr_confidence=confidence))
            await session.flush()
            intelligence = analyze_pages([(page_no, text) for page_no, (text, _) in enumerate(page_data, start=1)])
            await persist_intelligence(session, version.id, intelligence)
            await build_chunks(session, version.id)
            previous = await session.scalar(select(DocumentVersion).where(DocumentVersion.document_id == version.document_id, DocumentVersion.id != version.id, DocumentVersion.uploaded_at < version.uploaded_at).order_by(DocumentVersion.uploaded_at.desc()))
            if previous is not None:
                await compare_versions(session, previous.id, version.id)
            version.status = VersionStatus.REVIEW_READY
            await session.commit()
        except Exception:
            await session.rollback()
            version = await session.scalar(select(DocumentVersion).where(DocumentVersion.id == vid))
            if version is not None:
                version.status = VersionStatus.FAILED
                await session.commit()
            raise


@celery_app.task(name="kmrl.jobs.process_document")
def process_document(version_id: str) -> dict[str, str]:
    asyncio.run(process_version(version_id))
    return {"version_id": version_id, "status": "review_ready"}
