"""
File handling utilities for the RCA engine.

Provides helpers to persist uploads, perform lightweight scanning, and
construct database records while keeping the worker and API behaviour aligned.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

import aiofiles
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.db.models import File
from core.logging import get_logger

logger = get_logger(__name__)

_SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9._-]")


def _sanitise_filename(filename: str) -> str:
    stem, *rest = filename.split("/")
    name = stem or "upload"
    safe = _SAFE_FILENAME_RE.sub("_", name)
    return safe.strip("._") or "upload"


class FileService:
    """Encapsulates filesystem persistence and validation rules."""

    def __init__(self) -> None:
        self._uploads_root = Path(settings.files.UPLOAD_DIR).resolve()
        self._uploads_root.mkdir(parents=True, exist_ok=True)
        self._allowed_types = {ext.lower() for ext in settings.files.ALLOWED_FILE_TYPES}
        self._max_bytes = settings.files.MAX_FILE_SIZE_MB * 1024 * 1024

    async def ingest_upload(
        self,
        session: AsyncSession,
        job_id: str,
        upload: UploadFile,
        *,
        uploader: Optional[str] = None,
    ) -> File:
        """
        Persist an uploaded file to disk and create a database record.

        Args:
            session: Active database session
            job_id: Associated job identifier
            upload: FastAPI upload wrapper
            uploader: Optional uploader identifier (user id / email)

        Returns:
            File: Persisted file record
        """
        extension = (Path(upload.filename or "").suffix.lstrip(".") or "").lower()
        if extension and self._allowed_types and extension not in self._allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file extension '.{extension}'",
            )

        target_path, file_size, checksum = await self._write_to_disk(job_id, upload)

        if file_size > self._max_bytes:
            await self._delete_path(target_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File exceeds limit of {self._max_bytes} bytes",
            )

        await self._enforce_scan(target_path)

        # Ensure we do not store duplicate artefacts.
        existing = await session.execute(
            select(File).where(File.checksum == checksum)
        )
        duplicate = existing.scalar_one_or_none()
        if duplicate:
            await self._delete_path(target_path)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="File already uploaded",
            )

        metadata: Dict[str, Optional[str]] = {
            "uploader": uploader,
        }

        file_record = File(
            job_id=job_id,
            filename=target_path.name,
            original_filename=upload.filename or target_path.name,
            file_path=str(target_path),
            content_type=upload.content_type,
            file_size=file_size,
            checksum=checksum,
            metadata=metadata,
        )

        session.add(file_record)
        await session.flush()
        await session.refresh(file_record)
        logger.info("Stored upload %s for job %s", file_record.id, job_id)
        return file_record

    async def _write_to_disk(
        self, job_id: str, upload: UploadFile
    ) -> Tuple[Path, int, str]:
        """Stream the upload to disk under the configured directory."""
        safe_name = _sanitise_filename(upload.filename or "upload.dat")
        job_dir = self._uploads_root / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        dest_path = job_dir / safe_name
        suffix = 1
        while dest_path.exists():
            dest_path = job_dir / f"{safe_name}.{suffix}"
            suffix += 1

        hasher = hashlib.sha256()
        bytes_written = 0

        try:
            async with aiofiles.open(dest_path, "wb") as buffer:
                while True:
                    chunk = await upload.read(settings.files.CHUNK_SIZE)
                    if not chunk:
                        break
                    bytes_written += len(chunk)
                    hasher.update(chunk)
                    await buffer.write(chunk)
                    if bytes_written > self._max_bytes:
                        break
        finally:
            await upload.seek(0)

        logger.debug(
            "Persisted upload to %s (%d bytes)", dest_path, bytes_written
        )
        checksum = hasher.hexdigest()
        return dest_path, bytes_written, checksum

    async def _enforce_scan(self, path: Path) -> None:
        """Run a lightweight content validation scan on the stored file."""
        if not settings.files.ENABLE_FILE_VALIDATION:
            return

        async with aiofiles.open(path, "rb") as buffer:
            sample = await buffer.read(4096)

        if not sample:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty files are not allowed",
            )

        printable = sum(
            1 for byte in sample if 32 <= byte <= 126 or byte in (9, 10, 13)
        )
        fraction = printable / len(sample)
        if fraction < 0.6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File appears to be binary data which is not supported",
            )

    async def _delete_path(self, path: Path) -> None:
        try:
            await asyncio.to_thread(path.unlink, missing_ok=True)
        except Exception:  # pragma: no cover - best effort
            logger.warning("Unable to remove temporary upload %s", path)


__all__ = ["FileService"]
