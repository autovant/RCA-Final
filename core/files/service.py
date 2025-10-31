"""
File handling utilities for the RCA engine.

Provides helpers to persist uploads, perform lightweight scanning, and
construct database records while keeping the worker and API behaviour aligned.
"""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import aiofiles
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.config.feature_flags import COMPRESSED_INGESTION, TELEMETRY_ENHANCED_METRICS
from core.db.models import File
from core.files import extraction, validation
from core.files.enhanced_archives import get_enhanced_extractor
from core.files.telemetry import (
    PartialUploadTelemetry,
    PipelineStage,
    PipelineStatus,
    UploadTelemetryEvent,
    sanitise_metadata,
    persist_upload_telemetry_event,
)
from core.logging import get_logger
from core.metrics.pipeline_metrics import PipelineMetricsCollector

logger = get_logger(__name__)

_SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9._-]")

_PIPELINE_METRICS = PipelineMetricsCollector()

_ARCHIVE_EXTENSIONS = {"gz", "zip", "tar", "7z", "rar", "bz2", "xz", "tgz"}
_INGEST_SLA_SECONDS = 4 * 60  # four-minute SLA
_INGEST_SLA_ABORT_THRESHOLD = _INGEST_SLA_SECONDS - 30  # abort 30 seconds early


def _is_archive_expanded_formats_enabled() -> bool:
    """Check if expanded archive formats feature is enabled."""
    env_value = os.getenv("ARCHIVE_EXPANDED_FORMATS_ENABLED", "").lower()
    return env_value in ("true", "1", "yes", "on")


def _append_warning(metadata: Dict[str, Any], warning: str) -> None:
    """Append a warning message to telemetry metadata."""

    existing = metadata.get("warnings")
    if not existing:
        metadata["warnings"] = [warning]
        return

    if isinstance(existing, list):
        existing.append(warning)
        return

    metadata["warnings"] = [existing, warning]


def _normalise_warning_values(value: Any) -> List[str]:
    """Coerce telemetry warning metadata to a list of strings."""

    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return [str(value)]


def _coerce_uuid(value: Optional[str]) -> Optional[uuid.UUID]:
    """Best-effort conversion of arbitrary identifiers to UUIDs."""

    if not value:
        return None

    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):  # pragma: no cover - defensive guard
        logger.debug("Unable to coerce value %r into UUID", value)
        return None


def _sanitise_filename(filename: str) -> str:
    stem, *_ = filename.split("/")
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
        tenant_id: Optional[str] = None,
        platform: str = "generic",
        feature_flags: Optional[Iterable[str]] = None,
        telemetry_enabled: Optional[bool] = None,
    ) -> File:
        """
        Persist an uploaded file to disk and create a database record.

        Args:
            session: Active database session.
            job_id: Associated job identifier.
            upload: FastAPI upload wrapper.
            uploader: Optional uploader identifier (user id / email).
            tenant_id: Optional tenant identifier used for telemetry/metrics.
            platform: Source platform label for metrics (e.g., blue_prism).
            feature_flags: Active feature flag keys for this request.
            telemetry_enabled: Override to force telemetry emission regardless of
                global configuration.

        Returns:
            File: Persisted file record.
        """

        original_path = Path(upload.filename or "")
        extension = (original_path.suffix.lstrip(".") or "").lower()

        telemetry_metadata: Dict[str, Any] = {}
        if upload.content_type:
            telemetry_metadata["content_type"] = upload.content_type
        if uploader:
            telemetry_metadata["uploader"] = uploader

        tenant_uuid = _coerce_uuid(tenant_id)
        job_uuid = _coerce_uuid(job_id)

        active_flags = {
            flag.strip().lower()
            for flag in (feature_flags or [])
            if flag and flag.strip()
        }

        telemetry_flag_active = (
            telemetry_enabled
            if telemetry_enabled is not None
            else settings.feature_flags.is_enabled(TELEMETRY_ENHANCED_METRICS.key)
        )
        if telemetry_flag_active:
            active_flags.add(TELEMETRY_ENHANCED_METRICS.key)

        started_at = datetime.now(timezone.utc)
        start_timer = time.perf_counter()

        file_size: Optional[int] = None
        file_record: Optional[File] = None
        checksum: Optional[str] = None
        pipeline_status = PipelineStatus.SUCCESS
        extraction_result: Optional[extraction.ExtractionResult] = None
        archive_path: Optional[Path] = None
        target_path: Optional[Path] = None
        selected_member: Optional[extraction.ExtractedFile] = None

        try:
            is_archive = extension in _ARCHIVE_EXTENSIONS
            if (
                extension
                and self._allowed_types
                and extension not in self._allowed_types
                and not is_archive
            ):
                telemetry_metadata.setdefault("error_reason", "unsupported_extension")
                telemetry_metadata["extension"] = extension
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported file extension '.{extension}'",
                )

            if is_archive and not settings.feature_flags.is_enabled(
                COMPRESSED_INGESTION.key
            ):
                telemetry_metadata.setdefault(
                    "error_reason", "compressed_ingest_disabled"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Compressed ingestion feature is disabled",
                )

            target_path, file_size, checksum = await self._write_to_disk(job_id, upload)
            telemetry_metadata["size_bytes"] = file_size
            telemetry_metadata["checksum"] = checksum

            if file_size > self._max_bytes:
                telemetry_metadata.setdefault("error_reason", "file_too_large")
                telemetry_metadata["limit_bytes"] = self._max_bytes
                await self._delete_path(target_path)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File exceeds limit of {self._max_bytes} bytes",
                )

            if is_archive:
                archive_path = target_path
                extraction_destination = self._build_extraction_destination(archive_path)
                
                # Use enhanced extractor if feature flag is enabled
                if _is_archive_expanded_formats_enabled():
                    try:
                        enhanced_extractor = get_enhanced_extractor()
                        extraction_info = await enhanced_extractor.extract(
                            archive_path,
                            extraction_destination,
                        )
                        # Convert enhanced result to standard format
                        extraction_result = extraction.ExtractionResult(
                            destination=extraction_destination,
                            files=[
                                extraction.ExtractedFile(
                                    path=extraction_destination / file_name,
                                    original_path=file_name,
                                    size_bytes=0,  # Size will be determined by file validator
                                )
                                for file_name in extraction_info.files
                            ],
                            total_size_bytes=extraction_info.compressed_size,
                            duration_seconds=0.0,  # Duration tracked separately in telemetry
                            warnings=[],
                        )
                        telemetry_metadata["archive_format"] = extraction_info.format
                        telemetry_metadata["enhanced_extraction"] = True
                    except Exception as err:
                        # Fall back to standard extractor
                        logger.info(
                            "Enhanced extractor failed for %s, falling back to standard: %s",
                            archive_path.name,
                            str(err),
                        )
                        telemetry_metadata["enhanced_extraction_fallback"] = True
                        extractor = extraction.ArchiveExtractor()
                        try:
                            extraction_result = await asyncio.to_thread(
                                extractor.extract,
                                archive_path,
                                destination=extraction_destination,
                            )
                        except extraction.ArchiveExtractionError as fallback_err:
                            violation = validation.map_extraction_error(fallback_err)
                            telemetry_metadata.setdefault("error_reason", violation.code)
                            telemetry_metadata["extraction_detail"] = violation.detail or violation.message
                            telemetry_metadata["extraction_exception"] = fallback_err.__class__.__name__
                            telemetry_metadata["extraction_message"] = str(fallback_err) or violation.message
                            retriable = not isinstance(
                                fallback_err,
                                (
                                    extraction.ExtractionTimeoutExceeded,
                                    extraction.ExtractionSizeLimitExceeded,
                                    extraction.UnsupportedArchiveTypeError,
                                ),
                            )
                            telemetry_metadata["extraction_retriable"] = retriable
                            if archive_path:
                                await self._delete_path(archive_path)
                            if retriable:
                                raise HTTPException(
                                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                    detail=(
                                        "Archive could not be processed. The upload may be corrupted; "
                                        "please retry."
                                    ),
                                ) from fallback_err
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=violation.message,
                            ) from fallback_err
                else:
                    # Standard extraction flow
                    extractor = extraction.ArchiveExtractor()
                    try:
                        extraction_result = await asyncio.to_thread(
                            extractor.extract,
                            archive_path,
                            destination=extraction_destination,
                        )
                    except extraction.ArchiveExtractionError as err:
                        violation = validation.map_extraction_error(err)
                        telemetry_metadata.setdefault("error_reason", violation.code)
                        telemetry_metadata["extraction_detail"] = violation.detail or violation.message
                        telemetry_metadata["extraction_exception"] = err.__class__.__name__
                        telemetry_metadata["extraction_message"] = str(err) or violation.message
                        retriable = not isinstance(
                            err,
                            (
                                extraction.ExtractionTimeoutExceeded,
                                extraction.ExtractionSizeLimitExceeded,
                                extraction.UnsupportedArchiveTypeError,
                            ),
                        )
                        telemetry_metadata["extraction_retriable"] = retriable
                        if archive_path:
                            await self._delete_path(archive_path)
                        if retriable:
                            raise HTTPException(
                                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                detail=(
                                    "Archive could not be processed. The upload may be corrupted; "
                                    "please retry."
                                ),
                            ) from err
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=violation.message,
                        ) from err

                violations = validation.validate_extraction_result(extraction_result)
                if violations:
                    telemetry_metadata.setdefault("error_reason", violations[0].code)
                    telemetry_metadata["extraction_violations"] = [
                        violation.code for violation in violations
                    ]
                    extraction_result.cleanup()
                    if archive_path:
                        await self._delete_path(archive_path)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=violations[0].message,
                    )

                if not extraction_result.files:
                    telemetry_metadata.setdefault("error_reason", "empty_archive")
                    telemetry_metadata["extraction_detail"] = "Archive contained no files"
                    extraction_result.cleanup()
                    if archive_path:
                        await self._delete_path(archive_path)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Archive did not contain any files",
                    )

                telemetry_metadata["archive_member_count"] = len(
                    extraction_result.files
                )
                telemetry_metadata["archive_upload_bytes"] = file_size
                telemetry_metadata["extracted_total_bytes"] = (
                    extraction_result.total_size_bytes
                )
                telemetry_metadata["extraction_duration_seconds"] = round(
                    extraction_result.duration_seconds,
                    3,
                )
                if extraction_result.warnings:
                    telemetry_metadata["warnings"] = list(extraction_result.warnings)

                selected_member = extraction_result.files[0]
                telemetry_metadata["archive_selected_member"] = (
                    selected_member.original_path
                )

                if archive_path.suffix.lower() == ".zip":
                    supported_members, unsupported_members = self._partition_extracted_members(
                        extraction_result.files
                    )
                    telemetry_metadata["archive_supported_member_count"] = len(
                        supported_members
                    )
                    if unsupported_members:
                        telemetry_metadata["archive_unsupported_members"] = [
                            member.original_path for member in unsupported_members
                        ]
                        telemetry_metadata["archive_unsupported_member_count"] = len(
                            unsupported_members
                        )

                    if not supported_members:
                        telemetry_metadata.setdefault(
                            "error_reason", "no_supported_members"
                        )
                        telemetry_metadata["allowed_extensions"] = sorted(
                            self._allowed_types
                        )
                        extraction_result.cleanup()
                        if archive_path:
                            await self._delete_path(archive_path)
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Archive does not contain supported file types",
                        )

                    selected_member = supported_members[0]
                    telemetry_metadata["archive_selected_member"] = (
                        selected_member.original_path
                    )

                    if len(extraction_result.files) > 1:
                        _append_warning(
                            telemetry_metadata,
                            "archive_multiple_files_present",
                        )
                        telemetry_metadata["archive_member_count"] = len(
                            extraction_result.files
                        )
                    additional_supported = supported_members[1:]
                    if additional_supported:
                        _append_warning(
                            telemetry_metadata,
                            "archive_multiple_supported_members",
                        )

                    skipped_members: List[str] = [
                        member.original_path for member in unsupported_members
                    ]
                    skipped_members.extend(
                        member.original_path for member in additional_supported
                    )
                    if skipped_members:
                        pipeline_status = PipelineStatus.PARTIAL
                        existing_warning_values = _normalise_warning_values(
                            telemetry_metadata.pop("warnings", None)
                        )
                        combined_warnings = [*existing_warning_values]
                        if unsupported_members:
                            combined_warnings.append(
                                "unsupported_archive_members_skipped"
                            )
                        if additional_supported:
                            combined_warnings.append(
                                "additional_supported_members_skipped"
                            )
                        partial_details = PartialUploadTelemetry(
                            skipped_items=skipped_members,
                            warnings=combined_warnings,
                            reason="archive_members_skipped",
                            extra={
                                "skipped_supported_member_count": len(
                                    additional_supported
                                ),
                                "skipped_unsupported_member_count": len(
                                    unsupported_members
                                ),
                            },
                        )
                        telemetry_metadata = partial_details.apply(telemetry_metadata)

                target_path = selected_member.path
                file_size = selected_member.size_bytes
                telemetry_metadata["size_bytes"] = file_size
                active_flags.add(COMPRESSED_INGESTION.key)

                elapsed_seconds = time.perf_counter() - start_timer
                if elapsed_seconds >= _INGEST_SLA_ABORT_THRESHOLD:
                    pipeline_status = PipelineStatus.PARTIAL
                    telemetry_metadata.setdefault("error_reason", "ingest_sla_guard")
                    telemetry_metadata["sla_elapsed_seconds"] = round(
                        elapsed_seconds, 3
                    )
                    telemetry_metadata["partial_reason"] = "ingest_sla_guard"
                    extraction_result.cleanup()
                    await self._delete_path(target_path)
                    if archive_path:
                        await self._delete_path(archive_path)
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Ingestion aborted before SLA breach; please retry with a smaller archive.",
                    )

            await self._enforce_scan(target_path)

            # Duplicate uploads are now allowed - each upload creates a new job
            file_metadata: Dict[str, Optional[str]] = {
                "uploader": uploader,
            }
            if archive_path:
                file_metadata["source_archive"] = archive_path.name
            if selected_member:
                file_metadata["source_archive_member"] = selected_member.original_path

            file_record = File(
                job_id=job_id,
                filename=target_path.name,
                original_filename=upload.filename or target_path.name,
                file_path=str(target_path),
                content_type=upload.content_type,
                file_size=file_size,
                checksum=checksum,
                metadata=file_metadata,
            )

            maybe_awaitable = session.add(file_record)
            if inspect.isawaitable(maybe_awaitable):
                await maybe_awaitable
            await session.flush()
            await session.refresh(file_record)
            logger.info("Stored upload %s for job %s", file_record.id, job_id)
            return file_record
        except HTTPException as exc:
            if pipeline_status != PipelineStatus.PARTIAL:
                pipeline_status = PipelineStatus.FAILED
            telemetry_metadata.setdefault("error_reason", "http_exception")
            telemetry_metadata["http_status"] = exc.status_code
            telemetry_metadata["error_detail"] = str(exc.detail)
            raise
        except Exception:
            pipeline_status = PipelineStatus.FAILED
            telemetry_metadata.setdefault("error_reason", "unexpected_exception")
            if extraction_result:
                extraction_result.cleanup()
            if archive_path and archive_path.exists():
                await self._delete_path(archive_path)
            if target_path and file_record is None:
                await self._delete_path(target_path)
            logger.exception("Unexpected error while ingesting upload for job %s", job_id)
            raise
        finally:
            completed_at = datetime.now(timezone.utc)
            duration_seconds = max(time.perf_counter() - start_timer, 0.0)
            feature_flag_list = sorted(active_flags)

            emit_metrics = telemetry_flag_active and settings.METRICS_ENABLED
            tenant_label = str(tenant_uuid) if tenant_uuid else "unknown"
            file_type_label = extension or "unknown"

            raw_metadata: Dict[str, Any] = {
                key: value for key, value in telemetry_metadata.items() if value is not None
            }
            if file_record is not None:
                raw_metadata.setdefault("file_id", str(file_record.id))
                raw_metadata.setdefault("size_bytes", file_size)

            event_metadata = sanitise_metadata(raw_metadata)

            if emit_metrics:
                _PIPELINE_METRICS.ingest.observe(
                    tenant_id=tenant_label,
                    platform=platform or "generic",
                    file_type=file_type_label,
                    size_bytes=file_size,
                    status=pipeline_status.value,
                    feature_flags=feature_flag_list,
                    duration_seconds=duration_seconds,
                )

            if (
                telemetry_flag_active
                and tenant_uuid
                and job_uuid
                and file_record is not None
            ):
                upload_uuid = _coerce_uuid(str(file_record.id))
                if upload_uuid is None:
                    logger.debug(
                        "Skipping telemetry persistence; upload id missing for job %s",
                        job_id,
                    )
                else:
                    event = UploadTelemetryEvent(
                        tenant_id=tenant_uuid,
                        job_id=job_uuid,
                        upload_id=upload_uuid,
                        stage=PipelineStage.INGEST,
                        feature_flags=feature_flag_list,
                        status=pipeline_status,
                        duration_ms=int(duration_seconds * 1000),
                        started_at=started_at,
                        completed_at=completed_at,
                        metadata=event_metadata,
                    )
                    try:
                        await persist_upload_telemetry_event(session, event)
                    except Exception:  # pragma: no cover - persistence best effort
                        logger.exception(
                            "Failed to persist upload telemetry event for job %s", job_id
                        )

    def _build_extraction_destination(self, archive_path: Path) -> Path:
        """Select a job-specific folder for archive extraction results."""

        base = archive_path.parent / f"{archive_path.stem}_extracted"
        candidate = base
        suffix = 1
        while candidate.exists():
            candidate = base.parent / f"{base.name}_{suffix}"
            suffix += 1
        return candidate

    def _is_supported_member(self, member: extraction.ExtractedFile) -> bool:
        """Return True when an extracted member has a permitted extension."""

        if not self._allowed_types:
            return True

        suffix = member.path.suffix.lstrip(".").lower()
        if not suffix and member.original_path:
            suffix = Path(member.original_path).suffix.lstrip(".").lower()
        if not suffix:
            return False
        return suffix in self._allowed_types

    def _partition_extracted_members(
        self, members: Iterable[extraction.ExtractedFile]
    ) -> Tuple[List[extraction.ExtractedFile], List[extraction.ExtractedFile]]:
        """Split extracted files into supported and unsupported groups."""

        supported: List[extraction.ExtractedFile] = []
        unsupported: List[extraction.ExtractedFile] = []
        for member in members:
            if self._is_supported_member(member):
                supported.append(member)
            else:
                unsupported.append(member)
        return supported, unsupported

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
        write_error = False

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
        except Exception:
            write_error = True
            raise
        finally:
            await upload.seek(0)
            if write_error:
                await self._delete_path(dest_path)

        logger.debug("Persisted upload to %s (%d bytes)", dest_path, bytes_written)
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
        except Exception:  # pragma: no cover - best effort cleanup
            logger.warning("Unable to remove temporary upload %s", path)


__all__ = ["FileService"]
