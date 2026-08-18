from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.jobs.celery_app import celery_app
from app.models import DocumentVersion, File, Page, VersionStatus


def extract_pages(path: Path, mime_type: str) -> list[tuple[str, float]]:
    if mime_type == "text/plain" or path.suffix.lower() in {".txt", ".md", ".csv"}:
        return [(path.read_text(errors="replace"), 0.98)]
    if mime_type == "application/pdf" or path.suffix.lower() == ".pdf":
        info = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=False)
        pages = 1
        for line in info.stdout.splitlines():
            if line.startswith("Pages:"):
                pages = int(line.split(":", 1)[1].strip())
        extracted: list[tuple[str, float]] = []
        for page_no in range(1, pages + 1):
            result = subprocess.run(["pdftotext", "-layout", "-f", str(page_no), "-l", str(page_no), str(path), "-"], capture_output=True, text=True, check=False)
            text = result.stdout.strip()
            extracted.append((text, 0.92 if len(text) >= 40 else 0.46))
        return extracted
    try:
        result = subprocess.run(["tesseract", str(path), "stdout"], capture_output=True, text=True, check=False)
        text = result.stdout.strip()
        return [(text, 0.88 if len(text) >= 30 and result.returncode == 0 else 0.42)]
    except FileNotFoundError:
        return [("OCR engine unavailable in local demo environment.", 0.35)]


async def process_version(version_id: str) -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as session:
        version = await session.scalar(select(DocumentVersion).where(DocumentVersion.id == version_id))
        source = await session.scalar(select(File).where(File.version_id == version_id))
        if version is None or source is None:
            return
        version.status = VersionStatus.PROCESSING
        await session.commit()
        try:
            pages = extract_pages(Path(source.object_key), source.mime_type)
            await session.execute(delete(Page).where(Page.version_id == version.id))
            for page_no, (text, confidence) in enumerate(pages, start=1):
                session.add(Page(version_id=version.id, page_no=page_no, image_key=source.object_key, ocr_text=text, ocr_confidence=confidence))
            version.status = VersionStatus.REVIEW_READY
            await session.commit()
        except Exception:
            version.status = VersionStatus.FAILED
            await session.commit()
            raise


@celery_app.task(name="kmrl.jobs.process_document")
def process_document(version_id: str) -> dict[str, str]:
    asyncio.run(process_version(version_id))
    return {"version_id": version_id, "status": "review_ready"}
