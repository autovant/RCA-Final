"""
File management endpoints.

These endpoints expose small helper utilities that are useful while the full
upload pipeline is still under construction: clients can discover which file
types are supported and validate metadata before attempting an upload.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File as UploadDependency,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field, UUID4, validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.db.database import get_db
from core.db.models import File as FileModel, User
from core.jobs.service import JobService
from core.files.service import FileService
from core.security.auth import get_current_user
from core.metrics import MetricsCollector

router = APIRouter()
job_service = JobService()
file_service = FileService()

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

    id: str
    job_id: str
    filename: str
    original_filename: str
    content_type: Optional[str]
    file_size: int
    checksum: str
    processed: bool
    processed_at: Optional[str]
    created_at: Optional[str]
    metadata: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


@router.get("/supported-types", response_model=SupportedFileTypesResponse)
async def supported_file_types() -> SupportedFileTypesResponse:
    """Return the list of allowed file types and the current size limit."""
    return SupportedFileTypesResponse(
        allowed_types=settings.files.ALLOWED_FILE_TYPES,
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
    if extension not in [ext.lower() for ext in settings.files.ALLOWED_FILE_TYPES]:
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
    job_id: UUID4 = Form(...),
    file: UploadFile = UploadDependency(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Persist an uploaded file and attach it to the specified job."""
    job = await job_service.get_job(str(job_id))
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    user_id = str(current_user.id)
    if job.user_id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not permitted to upload files for this job",
        )

    stored = await file_service.ingest_upload(
        db,
        str(job_id),
        file,
        uploader=user_id,
    )

    await job_service.create_job_event(
        str(job_id),
        "file-uploaded",
        {
            "file_id": str(stored.id),
            "filename": stored.original_filename,
            "size": stored.file_size,
            "content_type": stored.content_type,
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
    if job.user_id != user_id and not current_user.is_superuser:
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
