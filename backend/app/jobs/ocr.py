from __future__ import annotations

import asyncio
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from celery.exceptions import MaxRetriesExceededError
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.jobs.celery_app import celery_app
from app.models import DocumentVersion, File, Page, VersionStatus
from app.services.comparison import compare_versions
from app.services.intelligence import analyze_pages
from app.services.intelligence_persistence import persist_intelligence
from app.services.rag import build_chunks

COMMAND_TIMEOUT_SECONDS = 90
PDF_TEXT_MINIMUM = 40


def _safe_error(exc: Exception) -> str:
    message = str(exc).strip().replace("\n", " ")
    message = re.sub(r"/(?:[^ ]+/)+", "<path>", message)
    return message[:500] or exc.__class__.__name__


def _run(command: list[str], *, timeout: int = COMMAND_TIMEOUT_SECONDS) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"OCR subprocess timeout after {timeout}s: {command[0]}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "process failed").strip().splitlines()[-1]
        raise RuntimeError(f"{command[0]} failed: {detail[:300]}")
    return result


def _extract_pdf_page(path: Path, page_no: int) -> tuple[str, float]:
    direct = _run(["pdftotext", "-layout", "-f", str(page_no), "-l", str(page_no), str(path), "-"]).stdout.strip()
    if len(direct) >= PDF_TEXT_MINIMUM:
        return direct, 0.94
    if shutil.which("pdftoppm") is None or shutil.which("tesseract") is None:
        raise RuntimeError("Scanned PDF requires pdftoppm and tesseract, but an OCR executable is unavailable")
    with tempfile.TemporaryDirectory(prefix="kmrl-ocr-") as temp_dir:
        prefix = str(Path(temp_dir) / "page")
        _run(["pdftoppm", "-f", str(page_no), "-l", str(page_no), "-r", "150", "-png", str(path), prefix])
        image = Path(f"{prefix}-{page_no}.png")
        if not image.exists():
            raise RuntimeError(f"PDF page {page_no} could not be rendered for OCR")
        ocr = _run(["tesseract", str(image), "stdout"]).stdout.strip()
        return ocr, 0.72 if len(ocr) >= 30 else 0.42


def extract_pages(path: Path, mime_type: str) -> list[tuple[str, float]]:
    if not path.exists():
        raise RuntimeError("Uploaded source file is missing")
    if mime_type == "text/plain" or path.suffix.lower() in {".txt", ".md", ".csv"}:
        return [(path.read_text(errors="replace"), 0.98)]
    if mime_type == "application/pdf" or path.suffix.lower() == ".pdf":
        info = _run(["pdfinfo", str(path)], timeout=30).stdout
        pages = next((int(line.split(":", 1)[1].strip()) for line in info.splitlines() if line.startswith("Pages:")), 1)
        return [_extract_pdf_page(path, page_no) for page_no in range(1, pages + 1)]
    if shutil.which("tesseract") is None:
        raise RuntimeError("Tesseract executable not found")
    ocr = _run(["tesseract", str(path), "stdout"]).stdout.strip()
    return [(ocr, 0.88 if len(ocr) >= 30 else 0.42)]


async def _set_stage(session, version: DocumentVersion, stage: str, *, status: VersionStatus | None = None) -> None:
    version.processing_stage = stage
    if status is not None:
        version.status = status
    await session.commit()


async def process_version(version_id: str) -> None:
    async with AsyncSessionLocal() as session:
        version = await session.scalar(select(DocumentVersion).where(DocumentVersion.id == version_id))
        source = await session.scalar(select(File).where(File.version_id == version_id))
        if version is None or source is None:
            return
        version.error_message = None
        await _set_stage(session, version, "ocr_processing", status=VersionStatus.PROCESSING)
        try:
            page_data = extract_pages(Path(source.object_key), source.mime_type)
            await session.execute(delete(Page).where(Page.version_id == version.id))
            for page_no, (text, confidence) in enumerate(page_data, start=1):
                session.add(Page(version_id=version.id, page_no=page_no, image_key=source.object_key, ocr_text=text, ocr_confidence=confidence))
            await session.flush()
            await _set_stage(session, version, "ocr_completed")
            intelligence = analyze_pages([(page_no, text) for page_no, (text, _) in enumerate(page_data, start=1)])
            await persist_intelligence(session, version.id, intelligence)
            await _set_stage(session, version, "chunking")
            await build_chunks(session, version.id)
            await _set_stage(session, version, "embedding")
            await _set_stage(session, version, "indexing")
            previous = await session.scalar(select(DocumentVersion).where(DocumentVersion.document_id == version.document_id, DocumentVersion.id != version.id, DocumentVersion.uploaded_at < version.uploaded_at).order_by(DocumentVersion.uploaded_at.desc()))
            if previous is not None:
                await compare_versions(session, previous.id, version.id)
            await _set_stage(session, version, "ready", status=VersionStatus.REVIEW_READY)
        except Exception as exc:
            await session.rollback()
            failed = await session.scalar(select(DocumentVersion).where(DocumentVersion.id == version_id))
            if failed is not None:
                failed.status = VersionStatus.FAILED
                failed.processing_stage = "failed"
                failed.error_message = _safe_error(exc)
                await session.commit()
            raise


@celery_app.task(bind=True, name="kmrl.jobs.process_document", max_retries=2, acks_late=True)
def process_document(self, version_id: str) -> dict[str, str]:
    try:
        asyncio.run(process_version(version_id))
        return {"version_id": version_id, "status": "review_ready"}
    except MaxRetriesExceededError:
        raise
    except Exception as exc:
        try:
            raise self.retry(exc=RuntimeError(_safe_error(exc)), countdown=5)
        except MaxRetriesExceededError:
            raise
