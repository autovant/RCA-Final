"""Tests for the file upload service."""

import io
import uuid
import pytest

pytest.importorskip("aiofiles")

from fastapi import UploadFile
from starlette import status
from fastapi import HTTPException

from core.files.service import FileService
from core.db.models import File


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
    upload = UploadFile(filename=filename, file=file_obj, content_type=content_type)
    return upload


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
        session,
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
async def test_ingest_upload_detects_duplicates(tmp_path):
    file_service = FileService()
    file_service._uploads_root = tmp_path  # type: ignore[attr-defined]

    session = _DummySession(existing=object())
    upload = _upload_file("duplicate.log", b"INFO already stored\n")

    with pytest.raises(HTTPException) as exc:
        await file_service.ingest_upload(session, "job-1", upload)

    assert exc.value.status_code == status.HTTP_409_CONFLICT
