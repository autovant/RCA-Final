"""
File management endpoints.

These endpoints expose small helper utilities that are useful while the full
upload pipeline is still under construction: clients can discover which file
types are supported and validate metadata before attempting an upload.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast

from fastapi import (
    APIRouter,
    Depends,
    File as UploadDependency,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field, UUID4, validator, ConfigDict
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.config.feature_flags import COMPRESSED_INGESTION
from core.db.database import get_db
from core.db.models import File as FileModel, Job, User
from core.jobs.service import JobService
from core.files.service import FileService
from core.security.auth import get_current_user
from core.metrics import MetricsCollector

router = APIRouter()
job_service = JobService()
file_service = FileService()


def _resolve_allowed_types() -> List[str]:
    base_types = {ext.lower() for ext in settings.files.ALLOWED_FILE_TYPES}
    if settings.feature_flags.is_enabled(COMPRESSED_INGESTION.key):
        base_types.update({"gz", "zip"})
    return sorted(base_types)

class SupportedFileTypesResponse(BaseModel):
    """Response containing the whitelisted extensions."""

    allowed_types: List[str]
    max_file_size_mb: int


class FileValidationRequest(BaseModel):
    """Metadata used to validate whether an upload would be accepted."""

    filename: str = Field(..., description="Original filename supplied by the client")
    file_size: int = Field(..., ge=0, description="Size of the file in bytes")

    @validator("filename")
    def _not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("filename must not be empty")
        return value


class FileValidationResponse(BaseModel):
    """Validation outcome for the supplied metadata."""

    is_allowed: bool
    reasons: List[str] = Field(default_factory=list)


class FileResponse(BaseModel):
    """Representation of a stored file."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    job_id: UUID4
    filename: str
    original_filename: str
    content_type: Optional[str]
    file_size: int
    checksum: str
    processed: bool
    processed_at: Optional[datetime]
    created_at: Optional[datetime]
    metadata: Optional[Dict[str, Any]] = None


@router.get("/supported-types", response_model=SupportedFileTypesResponse)
async def supported_file_types() -> SupportedFileTypesResponse:
    """Return the list of allowed file types and the current size limit."""
    return SupportedFileTypesResponse(
        allowed_types=_resolve_allowed_types(),
        max_file_size_mb=settings.files.MAX_FILE_SIZE_MB,
    )


@router.post("/validate", response_model=FileValidationResponse)
async def validate_file(metadata: FileValidationRequest) -> FileValidationResponse:
    """
    Check whether the provided file metadata adheres to the configured policy.

    This is a synchronous check that does not persist any state – it allows
    front-ends to provide quick feedback before streaming bytes.
    """
    reasons: List[str] = []

    extension = Path(metadata.filename).suffix.lstrip(".").lower()
    allowed_extensions = set(_resolve_allowed_types())
    if extension not in allowed_extensions:
        reasons.append(f"Unsupported file extension: .{extension or '<none>'}")

    max_bytes = settings.files.MAX_FILE_SIZE_MB * 1024 * 1024
    if metadata.file_size > max_bytes:
        reasons.append(
            f"File size {metadata.file_size} exceeds limit of {max_bytes} bytes"
        )

    is_allowed = not reasons
    return FileValidationResponse(is_allowed=is_allowed, reasons=reasons)


@router.post("/upload", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    job_id: Optional[UUID4] = Form(None),
    file: UploadFile = UploadDependency(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Persist an uploaded file and attach it to the specified job."""
    job_obj: Optional[Job] = None
    job_id_str: Optional[str] = None

    if job_id is not None:
        job_obj = await db.get(Job, str(job_id))
        if job_obj is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found",
            )
        job_id_str = str(job_obj.id)
    else:
        default_provider = settings.llm.DEFAULT_PROVIDER or "copilot"
        default_model = (
            settings.llm.OLLAMA_MODEL
            if default_provider == "ollama"
            else "gpt-4"
        )

        job_obj = Job(
            job_type="rca_analysis",
            user_id=str(current_user.id),
            input_manifest={"files": []},
            provider=default_provider,
            model=default_model,
            priority=0,
            status="draft",  # Start as draft to prevent worker from picking up before file is attached
            source={
                "created_via": "file-upload",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        db.add(job_obj)
        await db.flush()
        job_id_str = str(job_obj.id)
        await job_service.create_job_event(
            job_id_str,
            "created",
            {"input_manifest": job_obj.input_manifest},
            session=db,
        )

    assert job_obj is not None and job_id_str is not None  # for type checkers

    user_id = str(current_user.id)
    job_owner_id = str(getattr(job_obj, "user_id", "") or "")
    is_superuser = bool(getattr(current_user, "is_superuser", False))
    if job_owner_id and job_owner_id != user_id and not is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not permitted to upload files for this job",
        )

    manifest = job_obj.input_manifest if isinstance(job_obj.input_manifest, dict) else {}
    source = job_obj.source if isinstance(job_obj.source, dict) else {}
    telemetry_tenant_id = manifest.get("tenant_id")
    platform_label = (
        source.get("platform")
        or manifest.get("platform")
        or source.get("created_via")
        or "api"
    )

    stored = await file_service.ingest_upload(
        db,
        job_id_str,
        file,
        uploader=user_id,
        tenant_id=telemetry_tenant_id,
        platform=platform_label,
    )

    manifest_files = list(manifest.get("files") or [])
    stored_id = str(stored.id)
    if stored_id not in manifest_files:
        manifest_files.append(stored_id)
    manifest["files"] = manifest_files
    
    # Prepare update values
    update_values = {
        "input_manifest": manifest,
        "updated_at": datetime.now(timezone.utc),
    }
    
    # If job was created in draft status (no job_id provided), transition to pending now that file is attached
    job_status = str(getattr(job_obj, "status", ""))
    if job_status == "draft":
        update_values["status"] = "pending"
    
    await db.execute(
        update(Job)
        .where(Job.id == job_id_str)
        .values(**update_values)
    )

    await job_service.create_job_event(
        job_id_str,
        "file-uploaded",
        {
            "file_id": str(stored.id),
            "filename": stored.original_filename,
            "size": stored.file_size,
            "content_type": stored.content_type,
        },
        session=db,
    )
    
    # If job was transitioned from draft to pending, emit a ready event
    if job_status == "draft":
        await job_service.create_job_event(
            job_id_str,
            "ready",
            {
                "status": "pending",
                "files_attached": len(manifest_files),
                "message": "Job ready for processing",
            },
            session=db,
        )

    await db.commit()
    await job_service.publish_session_events(db)
    MetricsCollector.record_http_request("POST", "/api/files/upload", 201, 0)
    return FileResponse.model_validate(stored)


@router.get("/jobs/{job_id}", response_model=List[FileResponse])
async def list_job_files(
    job_id: UUID4,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[FileResponse]:
    """List files that were uploaded for a job."""
    job = await job_service.get_job(str(job_id))
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    user_id = str(current_user.id)
    job_owner_id = str(getattr(job, "user_id", "") or "")
    is_superuser = bool(getattr(current_user, "is_superuser", False))
    if job_owner_id != user_id and not is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not permitted to access files for this job",
        )

    result = await db.execute(
        select(FileModel)
        .where(FileModel.job_id == str(job_id))
        .order_by(FileModel.created_at.asc())
    )
    files = result.scalars().all()
    return [FileResponse.model_validate(file) for file in files]


__all__ = ["router"]
