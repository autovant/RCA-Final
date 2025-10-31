"""Tests for the file upload service."""

import io
import uuid
from pathlib import Path
from typing import Any, Dict, cast

import pytest

pytest.importorskip("aiofiles")

from fastapi import HTTPException
from fastapi import UploadFile
from starlette import status
from starlette.datastructures import Headers

from core.config import settings
from core.config.feature_flags import COMPRESSED_INGESTION
from core.db.models import File
from core.files import extraction
from core.files.service import FileService
from core.files.telemetry import PipelineStatus


class _DummyResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _DummySession:
    def __init__(self, existing=None):
        self.existing = existing
        self.added = []

    async def execute(self, _stmt):
        return _DummyResult(self.existing)

    async def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        return None

    async def refresh(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()


def _upload_file(filename: str, content: bytes, content_type: str = "text/plain") -> UploadFile:
    file_obj = io.BytesIO(content)
    headers = Headers({"content-type": content_type}) if content_type else None
    return UploadFile(file=file_obj, filename=filename, headers=headers)


@pytest.mark.asyncio
async def test_ingest_upload_persists_file(tmp_path):
    file_service = FileService()
    file_service._uploads_root = tmp_path  # type: ignore[attr-defined]
    session = _DummySession()

    upload = _upload_file(
        "sample.log",
        b"INFO start\nERROR failure occurred\n",
    )

    stored: File = await file_service.ingest_upload(
        cast(Any, session),
        job_id="job-123",
        upload=upload,
        uploader="tester",
    )

    assert session.added, "file record should be added to the session"
    on_disk = tmp_path / "job-123" / stored.filename
    assert on_disk.exists(), "uploaded file should be written to disk"
    assert stored.metadata["uploader"] == "tester"
    assert stored.file_size == on_disk.stat().st_size


@pytest.mark.asyncio
async def test_ingest_upload_allows_duplicate_files(tmp_path):
    """Duplicate uploads are now allowed - each creates a new job."""
    file_service = FileService()
    file_service._uploads_root = tmp_path  # type: ignore[attr-defined]

    session = _DummySession(existing=object())
    upload = _upload_file("duplicate.log", b"INFO already stored\n")

    # This should NOT raise an exception anymore - duplicates are allowed
    result = await file_service.ingest_upload(cast(Any, session), "job-1", upload)
    
    # Verify the file was successfully ingested
    assert result is not None
    assert result.filename == "duplicate.log"


@pytest.mark.asyncio
async def test_zip_archive_selects_first_supported_member(tmp_path, monkeypatch):
    file_service = FileService()
    file_service._uploads_root = tmp_path  # type: ignore[attr-defined]
    session = _DummySession()

    flag_set = settings.feature_flags
    was_enabled = flag_set.is_enabled(COMPRESSED_INGESTION.key)
    flag_set.enable(COMPRESSED_INGESTION.key)

    async def fake_write_to_disk(self, job_id, upload):
        job_dir = self._uploads_root / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        archive_path = job_dir / "bundle.zip"
        archive_path.write_bytes(b"zipdata")
        await upload.seek(0)
        return archive_path, len(b"zipdata"), "checksum-zip"

    async def noop_scan(self, _path):
        return None

    class DummyExtractor:
        def extract(self, archive_path, destination):
            destination.mkdir(parents=True, exist_ok=True)

            unsupported_path = destination / "notes.exe"
            unsupported_path.write_text("skip", encoding="utf-8")
            supported_path = destination / "report.log"
            supported_path.write_text("include me", encoding="utf-8")

            unsupported = extraction.ExtractedFile(
                path=unsupported_path,
                original_path="notes.exe",
                size_bytes=unsupported_path.stat().st_size,
            )
            supported = extraction.ExtractedFile(
                path=supported_path,
                original_path="reports/report.log",
                size_bytes=supported_path.stat().st_size,
            )

            total_size = unsupported.size_bytes + supported.size_bytes
            return extraction.ExtractionResult(
                destination=destination,
                files=[unsupported, supported],
                total_size_bytes=total_size,
                duration_seconds=0.12,
                warnings=[],
                _owns_destination=False,
            )

    monkeypatch.setattr(FileService, "_write_to_disk", fake_write_to_disk, raising=False)
    monkeypatch.setattr(FileService, "_enforce_scan", noop_scan, raising=False)
    monkeypatch.setattr(
        "core.files.service.validation.validate_extraction_result", lambda _result: []
    )
    monkeypatch.setattr("core.files.service.extraction.ArchiveExtractor", lambda: DummyExtractor())

    upload = _upload_file("bundle.zip", b"zipdata")
    try:
        stored: File = await file_service.ingest_upload(
            cast(Any, session),
            job_id="zip-job",
            upload=upload,
        )
    finally:
        if not was_enabled:
            flag_set.disable(COMPRESSED_INGESTION.key)

    stored_filename = cast(str, stored.filename)
    stored_path = Path(cast(str, stored.file_path))
    stored_size = cast(int, stored.file_size)
    stored_metadata = cast(Dict[str, Any], stored.metadata)

    assert stored_filename == "report.log"
    assert stored_metadata["source_archive"] == "bundle.zip"
    assert stored_metadata["source_archive_member"] == "reports/report.log"
    assert stored_path.exists()
    assert stored_size == stored_path.stat().st_size


@pytest.mark.asyncio
async def test_zip_archive_without_supported_members_errors(tmp_path, monkeypatch):
    file_service = FileService()
    file_service._uploads_root = tmp_path  # type: ignore[attr-defined]
    session = _DummySession()

    flag_set = settings.feature_flags
    was_enabled = flag_set.is_enabled(COMPRESSED_INGESTION.key)
    flag_set.enable(COMPRESSED_INGESTION.key)

    async def fake_write_to_disk(self, job_id, upload):
        job_dir = self._uploads_root / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        archive_path = job_dir / "bundle.zip"
        archive_path.write_bytes(b"zipdata")
        await upload.seek(0)
        return archive_path, len(b"zipdata"), "checksum-zip"

    async def noop_scan(self, _path):
        return None

    class DummyExtractor:
        def extract(self, archive_path, destination):
            destination.mkdir(parents=True, exist_ok=True)

            only_path = destination / "ignore.exe"
            only_path.write_text("ignore", encoding="utf-8")
            extracted = extraction.ExtractedFile(
                path=only_path,
                original_path="ignore.exe",
                size_bytes=only_path.stat().st_size,
            )

            return extraction.ExtractionResult(
                destination=destination,
                files=[extracted],
                total_size_bytes=extracted.size_bytes,
                duration_seconds=0.05,
                warnings=[],
                _owns_destination=False,
            )

    monkeypatch.setattr(FileService, "_write_to_disk", fake_write_to_disk, raising=False)
    monkeypatch.setattr(FileService, "_enforce_scan", noop_scan, raising=False)
    monkeypatch.setattr(
        "core.files.service.validation.validate_extraction_result", lambda _result: []
    )
    monkeypatch.setattr("core.files.service.extraction.ArchiveExtractor", lambda: DummyExtractor())

    upload = _upload_file("bundle.zip", b"zipdata")

    try:
        with pytest.raises(HTTPException) as exc:
            await file_service.ingest_upload(
                cast(Any, session), job_id="zip-job", upload=upload
            )
    finally:
        if not was_enabled:
            flag_set.disable(COMPRESSED_INGESTION.key)

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "supported" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_zip_archive_partial_emits_skipped_metadata(tmp_path, monkeypatch):
    file_service = FileService()
    file_service._uploads_root = tmp_path  # type: ignore[attr-defined]
    session = _DummySession()

    flag_set = settings.feature_flags
    was_enabled = flag_set.is_enabled(COMPRESSED_INGESTION.key)
    flag_set.enable(COMPRESSED_INGESTION.key)

    async def fake_write_to_disk(self, job_id, upload):
        job_dir = self._uploads_root / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        archive_path = job_dir / "bundle.zip"
        archive_path.write_bytes(b"zipdata")
        await upload.seek(0)
        return archive_path, len(b"zipdata"), "checksum-zip"

    async def noop_scan(self, _path):
        return None

    class DummyExtractor:
        def extract(self, archive_path, destination):
            destination.mkdir(parents=True, exist_ok=True)

            unsupported_path = destination / "notes.exe"
            unsupported_path.write_text("skip", encoding="utf-8")
            supported_primary_path = destination / "report.log"
            supported_primary_path.write_text("include", encoding="utf-8")
            supported_extra_path = destination / "extra.log"
            supported_extra_path.write_text("second", encoding="utf-8")

            unsupported = extraction.ExtractedFile(
                path=unsupported_path,
                original_path="notes.exe",
                size_bytes=unsupported_path.stat().st_size,
            )
            supported_primary = extraction.ExtractedFile(
                path=supported_primary_path,
                original_path="reports/report.log",
                size_bytes=supported_primary_path.stat().st_size,
            )
            supported_extra = extraction.ExtractedFile(
                path=supported_extra_path,
                original_path="reports/extra.log",
                size_bytes=supported_extra_path.stat().st_size,
            )

            total_size = (
                unsupported.size_bytes
                + supported_primary.size_bytes
                + supported_extra.size_bytes
            )
            return extraction.ExtractionResult(
                destination=destination,
                files=[unsupported, supported_primary, supported_extra],
                total_size_bytes=total_size,
                duration_seconds=0.2,
                warnings=[],
                _owns_destination=False,
            )

    captured_event: Dict[str, Any] = {}

    async def capture_persist(_session, event):
        captured_event["event"] = event
        return event

    monkeypatch.setattr(FileService, "_write_to_disk", fake_write_to_disk, raising=False)
    monkeypatch.setattr(FileService, "_enforce_scan", noop_scan, raising=False)
    monkeypatch.setattr(
        "core.files.service.validation.validate_extraction_result", lambda _result: []
    )
    monkeypatch.setattr("core.files.service.extraction.ArchiveExtractor", lambda: DummyExtractor())
    monkeypatch.setattr("core.files.service.persist_upload_telemetry_event", capture_persist)

    upload = _upload_file("bundle.zip", b"zipdata")
    job_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    try:
        stored: File = await file_service.ingest_upload(
            cast(Any, session),
            job_id=str(job_id),
            upload=upload,
            tenant_id=str(tenant_id),
            telemetry_enabled=True,
        )
    finally:
        if not was_enabled:
            flag_set.disable(COMPRESSED_INGESTION.key)

    assert stored is not None
    event = captured_event.get("event")
    assert event is not None, "telemetry event should be emitted for partial ingest"
    assert event.status == PipelineStatus.PARTIAL

    metadata = event.metadata
    assert metadata["skipped_count"] == 2
    assert metadata["skipped_supported_member_count"] == 1
    assert metadata["skipped_unsupported_member_count"] == 1
    assert metadata["partial_reason"] == "archive_members_skipped"
    assert set(metadata["warnings"]).issuperset(
        {
            "archive_multiple_files_present",
            "archive_multiple_supported_members",
            "unsupported_archive_members_skipped",
            "additional_supported_members_skipped",
        }
    )
    assert metadata["warning_count"] == len(metadata["warnings"])
    assert set(metadata["skipped_items"]) == {"notes.exe", "reports/extra.log"}


@pytest.mark.asyncio
async def test_corrupted_archive_returns_retriable_error(tmp_path, monkeypatch):
    file_service = FileService()
    file_service._uploads_root = tmp_path  # type: ignore[attr-defined]
    session = _DummySession()

    flag_set = settings.feature_flags
    was_enabled = flag_set.is_enabled(COMPRESSED_INGESTION.key)
    flag_set.enable(COMPRESSED_INGESTION.key)

    async def fake_write_to_disk(self, job_id, upload):
        job_dir = self._uploads_root / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        archive_path = job_dir / "bundle.zip"
        archive_path.write_bytes(b"zipdata")
        await upload.seek(0)
        return archive_path, len(b"zipdata"), "checksum-zip"

    async def noop_scan(self, _path):
        return None

    class FailingExtractor:
        def extract(self, archive_path, destination):
            raise extraction.ArchiveExtractionError("CRC mismatch detected")

    monkeypatch.setattr(FileService, "_write_to_disk", fake_write_to_disk, raising=False)
    monkeypatch.setattr(FileService, "_enforce_scan", noop_scan, raising=False)
    monkeypatch.setattr(
        "core.files.service.validation.validate_extraction_result", lambda _result: []
    )
    monkeypatch.setattr("core.files.service.extraction.ArchiveExtractor", lambda: FailingExtractor())

    upload = _upload_file("bundle.zip", b"zipdata")

    try:
        with pytest.raises(HTTPException) as exc:
            await file_service.ingest_upload(
                cast(Any, session),
                job_id="zip-job",
                upload=upload,
                telemetry_enabled=True,
            )
    finally:
        if not was_enabled:
            flag_set.disable(COMPRESSED_INGESTION.key)

    assert exc.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "retry" in str(exc.value.detail).lower()
