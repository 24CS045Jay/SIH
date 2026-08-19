from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from pathlib import Path
import re
from uuid import UUID

from fastapi import APIRouter, Depends, File as UploadFileDependency, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import selectinload
from fastapi.responses import FileResponse
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import get_current_user, require_roles
from app.db.session import get_db
from app.jobs.ocr import process_document
from app.models import Action, ActionEvent, Alert, Assignment, Change, Chunk, Comparison, Department, Document, DocumentClassification, DocumentVersion, ExtractedFact, File as StoredFile, MalwareStatus, Page, Role, Sensitivity, User, VersionStatus
from app.services.access import can_access_document
from app.schemas.documents import DocumentDetail, DocumentListItem, PageResponse, ProcessingStatusResponse, UploadResponse
from app.services.storage import version_storage_path

router = APIRouter(prefix="/documents", tags=["documents"])
ALLOWED_MIME = {"application/pdf", "image/png", "image/jpeg", "image/tiff", "text/plain", "text/markdown", "text/csv"}
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".txt", ".md", ".csv"}
MAGIC = {".pdf": (b"%PDF-",), ".png": (b"\x89PNG\r\n\x1a\n",), ".jpg": (b"\xff\xd8\xff",), ".jpeg": (b"\xff\xd8\xff",), ".tif": (b"II*\x00", b"MM\x00*"), ".tiff": (b"II*\x00", b"MM\x00*")}

def sniff_mime(extension: str, content: bytes) -> bool:
    if extension in MAGIC:
        return any(content.startswith(signature) for signature in MAGIC[extension])
    try:
        content.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False

def malware_scan(content: bytes) -> MalwareStatus:
    return MalwareStatus.INFECTED if b"X5O!P%@AP[4\\\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*" in content else MalwareStatus.CLEAN


def list_item(document: Document, owner_name: str, version: DocumentVersion) -> DocumentListItem:
    return DocumentListItem(id=document.id, title=document.title, type=document.type, owner_name=owner_name, classification=document.classification.value, sensitivity=document.sensitivity.value, created_at=document.created_at, version_id=version.id, version_label=version.version_label, status=version.status.value, uploaded_at=version.uploaded_at, processing_stage=version.processing_stage, error_message=version.error_message)


@router.post("/upload", response_model=UploadResponse, status_code=202)
async def upload_document(file: UploadFile = UploadFileDependency(...), current_user: dict = Depends(require_roles(Role.SYSTEM_ADMINISTRATOR, Role.DOCUMENT_ADMINISTRATOR, Role.REVIEWER, Role.DEPARTMENT_USER)), db: AsyncSession = Depends(get_db)) -> UploadResponse:
    filename = file.filename or "uploaded-file"
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS or (file.content_type and file.content_type not in ALLOWED_MIME):
        raise HTTPException(status_code=422, detail="Rejected file type. Accepted: PDF, PNG/JPEG/TIFF, or text files.")
    content = await file.read()
    max_size = get_settings().max_upload_size_mb * 1024 * 1024
    if len(content) == 0 or len(content) > max_size:
        raise HTTPException(status_code=422, detail=f"File must be non-empty and no larger than {get_settings().max_upload_size_mb} MB.")
    if not sniff_mime(extension, content):
        raise HTTPException(status_code=422, detail="File content does not match its extension or allowed MIME family.")
    malware_status = malware_scan(content)
    if malware_status == MalwareStatus.INFECTED:
        raise HTTPException(status_code=422, detail="Malware scanner rejected the upload.")
    digest = sha256(content).hexdigest()
    duplicate = await db.scalar(select(DocumentVersion).where(DocumentVersion.hash == digest))
    if duplicate:
        raise HTTPException(status_code=409, detail=f"Duplicate file detected; existing version is {duplicate.id}.")
    owner_id = UUID(current_user["sub"])
    title = Path(filename).stem.replace("_", " ").strip() or "Untitled document"
    normalized_title = re.sub(r"\s+v\d+$", "", title, flags=re.IGNORECASE).strip()
    document = await db.scalar(select(Document).where(Document.title.in_([title, normalized_title])))
    if document is None:
        document = Document(title=normalized_title, type=extension.lstrip("."), owner_id=owner_id, classification=DocumentClassification.OTHER, sensitivity=Sensitivity.INTERNAL)
        db.add(document)
        await db.flush()
    labels = set((await db.execute(select(DocumentVersion.version_label).where(DocumentVersion.document_id == document.id))).scalars().all())
    existing_count = len(labels)
    explicit_label = re.search(r"\s+(v\d+)$", title, flags=re.IGNORECASE)
    requested_label = explicit_label.group(1).lower() if explicit_label else None
    if requested_label and requested_label not in labels:
        version_label = requested_label
    else:
        next_number = existing_count + 1
        while f"v{next_number}" in labels:
            next_number += 1
        version_label = f"v{next_number}"
    version = DocumentVersion(document_id=document.id, version_label=version_label, hash=digest, status=VersionStatus.QUEUED)
    db.add(version)
    await db.flush()
    path = version_storage_path(version.id, filename)
    path.write_bytes(content)
    db.add(StoredFile(version_id=version.id, object_key=str(path), mime_type=file.content_type or "application/octet-stream", size=len(content), malware_status=malware_status))
    await db.commit()
    try:
        process_document.delay(str(version.id))
    except Exception as exc:
        version.status = VersionStatus.FAILED
        version.processing_stage = "failed"
        version.error_message = "OCR queue unavailable; upload was stored but processing could not be started."
        await db.commit()
        raise HTTPException(status_code=503, detail="OCR queue unavailable. The upload was stored as failed and can be retried.") from exc
    return UploadResponse(document_id=document.id, version_id=version.id, status=VersionStatus.QUEUED.value, message="Upload accepted and OCR job queued.")


@router.get("", response_model=list[DocumentListItem])
async def list_documents(search: str | None = None, document_type: str | None = Query(default=None, alias="type"), status_filter: str | None = Query(default=None, alias="status"), department_id: UUID | None = None, from_date: datetime | None = None, to_date: datetime | None = None, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[DocumentListItem]:
    latest_uploaded = select(func.max(DocumentVersion.uploaded_at)).where(DocumentVersion.document_id == Document.id).correlate(Document).scalar_subquery()
    query = select(Document, User.name, DocumentVersion).join(User, Document.owner_id == User.id).join(DocumentVersion, DocumentVersion.document_id == Document.id).where(DocumentVersion.uploaded_at == latest_uploaded)
    if current_user.get("role") == Role.DEPARTMENT_USER.value:
        query = query.where(User.department_id == UUID(current_user.get("department_id"))) if current_user.get("department_id") else query.where(False)
    elif current_user.get("role") == Role.EXECUTIVE_VIEWER.value:
        query = query.where(Document.sensitivity.in_([Sensitivity.PUBLIC, Sensitivity.INTERNAL]))
    if search: query = query.where(Document.title.ilike(f"%{search}%"))
    if document_type: query = query.where(Document.type == document_type)
    if status_filter: query = query.where(DocumentVersion.status == status_filter)
    if department_id: query = query.where(User.department_id == department_id)
    if from_date: query = query.where(Document.created_at >= from_date)
    if to_date: query = query.where(Document.created_at <= to_date)
    result = await db.execute(query.order_by(Document.created_at.desc()))
    return [list_item(document, owner_name, version) for document, owner_name, version in result.all()]


@router.get("/{document_id}", response_model=DocumentDetail)
async def document_detail(document_id: UUID, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> DocumentDetail:
    row = await db.execute(select(Document, User.name, DocumentVersion).join(User, Document.owner_id == User.id).options(selectinload(Document.owner)).join(DocumentVersion, DocumentVersion.document_id == Document.id).where(Document.id == document_id).order_by(DocumentVersion.uploaded_at.desc()).limit(1))
    result = row.first()
    if result is None: raise HTTPException(status_code=404, detail="Document not found")
    document, owner_name, version = result
    if not can_access_document(document, current_user): raise HTTPException(status_code=403, detail="Document is outside your access scope")
    pages = (await db.execute(select(Page).where(Page.version_id == version.id).order_by(Page.page_no))).scalars().all()
    threshold = get_settings().low_ocr_confidence_threshold
    return DocumentDetail(document=list_item(document, owner_name, version), pages=[PageResponse(id=page.id, page_no=page.page_no, ocr_text=page.ocr_text, ocr_confidence=page.ocr_confidence, low_confidence=(page.ocr_confidence or 0) < threshold, image_url=None) for page in pages], source_url=f"/api/v1/documents/{document.id}/source")


@router.get("/{document_id}/status", response_model=ProcessingStatusResponse)
async def document_status(document_id: UUID, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> ProcessingStatusResponse:
    version = await db.scalar(select(DocumentVersion).where(DocumentVersion.document_id == document_id).order_by(DocumentVersion.uploaded_at.desc()))
    if version is None: raise HTTPException(status_code=404, detail="Document not found")
    document = await db.scalar(select(Document).where(Document.id == document_id).options(selectinload(Document.owner)))
    if document is None: raise HTTPException(status_code=404, detail="Document not found")
    if not can_access_document(document, current_user): raise HTTPException(status_code=403, detail="Document is outside your access scope")
    pages = (await db.execute(select(Page).where(Page.version_id == version.id))).scalars().all()
    return ProcessingStatusResponse(version_id=version.id, status=version.status.value, processing_stage=version.processing_stage, page_count=len(pages), low_confidence_pages=sum(1 for page in pages if (page.ocr_confidence or 0) < get_settings().low_ocr_confidence_threshold), error_message=version.error_message)


@router.post("/{document_id}/retry", status_code=202)
async def retry_document(document_id: UUID, current_user: dict = Depends(require_roles(Role.SYSTEM_ADMINISTRATOR, Role.DOCUMENT_ADMINISTRATOR, Role.REVIEWER)), db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    version = await db.scalar(select(DocumentVersion).where(DocumentVersion.document_id == document_id).order_by(DocumentVersion.uploaded_at.desc()))
    document = await db.scalar(select(Document).where(Document.id == document_id))
    if version is None or document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if not can_access_document(document, current_user):
        raise HTTPException(status_code=403, detail="Document is outside your access scope")
    if version.status != VersionStatus.FAILED:
        raise HTTPException(status_code=409, detail="Only failed documents can be retried")
    version.status = VersionStatus.QUEUED
    version.processing_stage = "queued"
    version.error_message = None
    await db.commit()
    process_document.delay(str(version.id))
    return {"document_id": str(document.id), "version_id": str(version.id), "status": VersionStatus.QUEUED.value}


@router.delete("/{document_id}", status_code=204, response_model=None)
async def delete_document(document_id: UUID, current_user: dict = Depends(require_roles(Role.SYSTEM_ADMINISTRATOR, Role.DOCUMENT_ADMINISTRATOR)), db: AsyncSession = Depends(get_db)) -> None:
    document = await db.scalar(select(Document).where(Document.id == document_id))
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if not can_access_document(document, current_user):
        raise HTTPException(status_code=403, detail="Document is outside your access scope")
    version_ids = list((await db.execute(select(DocumentVersion.id).where(DocumentVersion.document_id == document_id))).scalars().all())
    if not version_ids:
        await db.execute(delete(Document).where(Document.id == document_id))
        await db.commit()
        return None
    file_paths = list((await db.execute(select(StoredFile.object_key).where(StoredFile.version_id.in_(version_ids)))).scalars().all())
    comparison_ids = list((await db.execute(select(Comparison.id).where((Comparison.old_version_id.in_(version_ids)) | (Comparison.new_version_id.in_(version_ids))))).scalars().all())
    action_ids = list((await db.execute(select(Action.id).where(Action.source_version_id.in_(version_ids)))).scalars().all())
    alert_ids = list((await db.execute(select(Alert.id).where(Alert.source_version_id.in_(version_ids)))).scalars().all())
    if alert_ids or action_ids:
        await db.execute(delete(Assignment).where((Assignment.alert_id.in_(alert_ids)) | (Assignment.action_id.in_(action_ids))))
    if action_ids:
        await db.execute(delete(ActionEvent).where(ActionEvent.action_id.in_(action_ids)))
        await db.execute(delete(Action).where(Action.id.in_(action_ids)))
    if alert_ids:
        await db.execute(delete(Alert).where(Alert.id.in_(alert_ids)))
    if comparison_ids:
        await db.execute(delete(Change).where(Change.comparison_id.in_(comparison_ids)))
        await db.execute(delete(Comparison).where(Comparison.id.in_(comparison_ids)))
    await db.execute(delete(ExtractedFact).where(ExtractedFact.version_id.in_(version_ids)))
    await db.execute(delete(Chunk).where(Chunk.version_id.in_(version_ids)))
    await db.execute(delete(Page).where(Page.version_id.in_(version_ids)))
    await db.execute(delete(StoredFile).where(StoredFile.version_id.in_(version_ids)))
    await db.execute(delete(DocumentVersion).where(DocumentVersion.id.in_(version_ids)))
    await db.execute(delete(Document).where(Document.id == document_id))
    await db.commit()
    for object_key in file_paths:
        try:
            path = Path(object_key)
            if path.exists():
                path.unlink()
            parent = path.parent
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
        except OSError:
            continue
    return None


@router.get("/{document_id}/source")
async def source_file(document_id: UUID, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> FileResponse:
    version = await db.scalar(select(DocumentVersion).where(DocumentVersion.document_id == document_id).order_by(DocumentVersion.uploaded_at.desc()))
    if version is None: raise HTTPException(status_code=404, detail="Document not found")
    document = await db.scalar(select(Document).where(Document.id == document_id).options(selectinload(Document.owner)))
    if document is None: raise HTTPException(status_code=404, detail="Document not found")
    if not can_access_document(document, current_user): raise HTTPException(status_code=403, detail="Document is outside your access scope")
    stored = await db.scalar(select(StoredFile).where(StoredFile.version_id == version.id))
    if stored is None or not Path(stored.object_key).exists(): raise HTTPException(status_code=404, detail="Source file not found")
    return FileResponse(stored.object_key, media_type=stored.mime_type, filename=Path(stored.object_key).name)
