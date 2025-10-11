"""
File management endpoints.

These endpoints expose small helper utilities that are useful while the full
upload pipeline is still under construction: clients can discover which file
types are supported and validate metadata before attempting an upload.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field, validator

from core.config import settings

router = APIRouter()


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


__all__ = ["router"]
