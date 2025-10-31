"""Tests for core JobService behaviours."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from core.jobs.service import JobService


class _FakeResult:
    def __init__(self, job):
        self._job = job

    def scalar_one_or_none(self):
        return self._job


class _FakeTransaction:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSession:
    def __init__(self, job):
        self._job = job
        self.info = {}

    async def execute(self, _statement):
        return _FakeResult(self._job)

    def begin(self):
        return _FakeTransaction(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSessionContext:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeCreateJobSession:
    def __init__(self, file_map):
        self._file_map = file_map
        self.added = []
        self.flushed = False
        self.committed = False
        self.refreshed = []
        self.info = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed = True

    async def commit(self):
        self.committed = True

    async def refresh(self, obj):
        self.refreshed.append(obj)

    async def get(self, _model, pk):
        return self._file_map.get(str(pk))

    def begin(self):
        return _FakeTransaction(self)


@pytest.mark.asyncio
async def test_complete_job_updates_record(monkeypatch):
    service = JobService()
    job_id = "job-123"
    fake_job = SimpleNamespace(
        id=job_id,
        status="running",
        result_data=None,
        outputs={},
        ticketing={},
        completed_at=None,
        updated_at=None,
    )

    fake_session = _FakeSession(fake_job)
    service._session_factory = lambda: _FakeSessionContext(fake_session)  # type: ignore[attr-defined]

    published_calls = []

    async def fake_publish_session_events(session):
        published_calls.append(session)

    async def fake_create_job_event(job_id_arg, event_type, data, *, session):
        assert job_id_arg == job_id
        assert event_type == "completed"
        assert "result" in data
        assert session is fake_session

    monkeypatch.setattr(service, "_publish_session_events", fake_publish_session_events)
    monkeypatch.setattr(service, "create_job_event", fake_create_job_event)

    result_payload = {
        "outputs": {"json": {"summary": "done"}},
        "ticketing": {"platform": "jira"},
    }

    before = datetime.now(timezone.utc)
    await service.complete_job(job_id, result_payload)
    after = datetime.now(timezone.utc)

    assert fake_job.status == "completed"
    assert fake_job.result_data == result_payload
    assert fake_job.outputs == result_payload["outputs"]
    assert fake_job.ticketing == result_payload["ticketing"]
    assert fake_job.completed_at is not None and before <= fake_job.completed_at <= after
    assert fake_job.updated_at is not None and before <= fake_job.updated_at <= after

    assert published_calls == [fake_session]


@pytest.mark.asyncio
async def test_create_job_resets_file_state_when_reusing_upload(monkeypatch):
    service = JobService()
    file_id = "file-123"
    existing_file = SimpleNamespace(
        id=file_id,
        job_id="old-job",
        processed=True,
        processed_at=datetime.now(timezone.utc),
        processing_error="boom",
    )

    fake_session = _FakeCreateJobSession({file_id: existing_file})
    service._session_factory = lambda: fake_session  # type: ignore[assignment]

    events = []

    async def fake_create_job_event(job_id_arg, event_type, data, *, session):
        events.append((job_id_arg, event_type, data, session))

    async def fake_publish_session_events(_session):
        return None

    monkeypatch.setattr(service, "create_job_event", fake_create_job_event)
    monkeypatch.setattr(service, "_publish_session_events", fake_publish_session_events)

    job = await service.create_job(
        user_id="user-1",
        job_type="analysis",
        input_manifest={"files": [file_id]},
        file_ids=[file_id],
    )

    assert existing_file.job_id == job.id
    assert existing_file.processed is False
    assert existing_file.processed_at is None
    assert existing_file.processing_error is None
    assert fake_session.committed is True
    assert fake_session.flushed is True
    assert events[0][0] == job.id
    assert events[0][1] == "created"


@pytest.mark.asyncio
async def test_update_job_status_resets_completion_metadata(monkeypatch):
    service = JobService()
    job_id = "job-456"
    fake_job = SimpleNamespace(
        id=job_id,
        status="completed",
        result_data={"outputs": {"text": "done"}},
        outputs={"text": "done"},
        ticketing={"existing": True},
        completed_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        started_at=None,
        error_message="old",
    )

    fake_session = _FakeSession(fake_job)
    service._session_factory = lambda: _FakeSessionContext(fake_session)  # type: ignore[assignment]

    events = []

    async def fake_create_job_event(job_id_arg, event_type, data, *, session):
        events.append((job_id_arg, event_type, data, session))

    async def fake_publish_session_events(session_arg):
        return None

    monkeypatch.setattr(service, "create_job_event", fake_create_job_event)
    monkeypatch.setattr(service, "_publish_session_events", fake_publish_session_events)

    await service.update_job_status(job_id, "running")

    assert fake_job.status == "running"
    assert fake_job.completed_at is None
    assert fake_job.error_message is None
    assert fake_job.result_data is None
    assert fake_job.outputs == {}
    assert events[0][2]["status"] == "running"

    await service.update_job_status(job_id, "pending")

    assert fake_job.status == "pending"
    assert fake_job.started_at is None
    assert fake_job.completed_at is None
    assert fake_job.result_data is None
    assert fake_job.outputs == {}


@pytest.mark.asyncio
async def test_cancel_job_updates_fields(monkeypatch):
    service = JobService()
    job_id = "job-cancel"
    fake_job = SimpleNamespace(
        id=job_id,
        status="running",
        error_message=None,
        completed_at=None,
        updated_at=None,
    )

    fake_session = _FakeSession(fake_job)
    service._session_factory = lambda: _FakeSessionContext(fake_session)  # type: ignore[assignment]

    events = []

    async def fake_create_job_event(job_id_arg, event_type, data, *, session):
        events.append((job_id_arg, event_type, data, session))

    async def fake_publish_session_events(session_arg):
        return None

    monkeypatch.setattr(service, "create_job_event", fake_create_job_event)
    monkeypatch.setattr(service, "_publish_session_events", fake_publish_session_events)

    result = await service.cancel_job(job_id, reason="User stop")

    assert result is True
    assert fake_job.status == "cancelled"
    assert fake_job.error_message == "User stop"
    assert fake_job.completed_at is not None
    assert fake_job.updated_at is not None
    assert events[0][1] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_job_returns_false_when_already_terminal(monkeypatch):
    service = JobService()
    job_id = "job-terminal"
    fake_job = SimpleNamespace(
        id=job_id,
        status="completed",
        error_message=None,
        completed_at=None,
        updated_at=None,
    )

    fake_session = _FakeSession(fake_job)
    service._session_factory = lambda: _FakeSessionContext(fake_session)  # type: ignore[assignment]

    async def fake_publish_session_events(_session):
        return None

    monkeypatch.setattr(service, "create_job_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(service, "_publish_session_events", fake_publish_session_events)

    result = await service.cancel_job(job_id, reason="noop")

    assert result is False
    assert fake_job.status == "completed"


@pytest.mark.asyncio
async def test_pause_job_transitions_running_job(monkeypatch):
    service = JobService()
    job_id = "job-pause"
    fake_job = SimpleNamespace(
        id=job_id,
        status="running",
        updated_at=None,
    )

    fake_session = _FakeSession(fake_job)
    service._session_factory = lambda: _FakeSessionContext(fake_session)  # type: ignore[assignment]

    events = []

    async def fake_create_job_event(job_id_arg, event_type, data, *, session):
        events.append((job_id_arg, event_type, data, session))

    async def fake_publish_session_events(_session):
        return None

    monkeypatch.setattr(service, "create_job_event", fake_create_job_event)
    monkeypatch.setattr(service, "_publish_session_events", fake_publish_session_events)

    result = await service.pause_job(job_id, reason="maintenance window")

    assert result is True
    assert fake_job.status == "paused"
    assert fake_job.updated_at is not None
    assert events[0][1] == "paused"
    assert events[0][2]["reason"] == "maintenance window"


@pytest.mark.asyncio
async def test_pause_job_returns_false_when_not_running(monkeypatch):
    service = JobService()
    job_id = "job-not-running"
    fake_job = SimpleNamespace(
        id=job_id,
        status="completed",
        updated_at=None,
    )

    fake_session = _FakeSession(fake_job)
    service._session_factory = lambda: _FakeSessionContext(fake_session)  # type: ignore[assignment]

    async def fake_publish_session_events(_session):
        return None

    monkeypatch.setattr(service, "create_job_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(service, "_publish_session_events", fake_publish_session_events)

    result = await service.pause_job(job_id)

    assert result is False
    assert fake_job.status == "completed"


@pytest.mark.asyncio
async def test_resume_job_transitions_paused_job(monkeypatch):
    service = JobService()
    job_id = "job-resume"
    fake_job = SimpleNamespace(
        id=job_id,
        status="paused",
        updated_at=None,
    )

    fake_session = _FakeSession(fake_job)
    service._session_factory = lambda: _FakeSessionContext(fake_session)  # type: ignore[assignment]

    events = []

    async def fake_create_job_event(job_id_arg, event_type, data, *, session):
        events.append((job_id_arg, event_type, data, session))

    async def fake_publish_session_events(_session):
        return None

    monkeypatch.setattr(service, "create_job_event", fake_create_job_event)
    monkeypatch.setattr(service, "_publish_session_events", fake_publish_session_events)

    result = await service.resume_job(job_id, note="resume note")

    assert result is True
    assert fake_job.status == "running"
    assert fake_job.updated_at is not None
    assert events[0][1] == "resumed"
    assert events[0][2]["message"] == "resume note"


@pytest.mark.asyncio
async def test_resume_job_returns_false_when_not_paused(monkeypatch):
    service = JobService()
    job_id = "job-not-paused"
    fake_job = SimpleNamespace(
        id=job_id,
        status="running",
        updated_at=None,
    )

    fake_session = _FakeSession(fake_job)
    service._session_factory = lambda: _FakeSessionContext(fake_session)  # type: ignore[assignment]

    async def fake_publish_session_events(_session):
        return None

    monkeypatch.setattr(service, "create_job_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(service, "_publish_session_events", fake_publish_session_events)

    result = await service.resume_job(job_id)

    assert result is False
    assert fake_job.status == "running"


@pytest.mark.asyncio
async def test_restart_job_resets_state_and_files(monkeypatch):
    service = JobService()
    job_id = "job-restart"
    file_record = SimpleNamespace(
        processed=True,
        processed_at=datetime.now(timezone.utc),
        processing_error="not good",
    )
    fake_job = SimpleNamespace(
        id=job_id,
        status="failed",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        error_message="boom",
        result_data={"foo": "bar"},
        outputs={"data": 1},
        updated_at=None,
        retry_count=3,
        max_retries=3,
        files=[file_record],
    )

    fake_session = _FakeSession(fake_job)
    service._session_factory = lambda: _FakeSessionContext(fake_session)  # type: ignore[assignment]

    events = []

    async def fake_create_job_event(job_id_arg, event_type, data, *, session):
        events.append((job_id_arg, event_type, data, session))

    async def fake_publish_session_events(session_arg):
        return None

    monkeypatch.setattr(service, "create_job_event", fake_create_job_event)
    monkeypatch.setattr(service, "_publish_session_events", fake_publish_session_events)

    restarted = await service.restart_job(job_id)

    assert restarted is fake_job
    assert fake_job.status == "pending"
    assert fake_job.started_at is None
    assert fake_job.completed_at is None
    assert fake_job.error_message is None
    assert fake_job.result_data is None
    assert fake_job.outputs == {}
    assert fake_job.retry_count == 2
    assert file_record.processed is False
    assert file_record.processed_at is None
    assert file_record.processing_error is None
    assert events[0][1] == "restart-requested"
    assert events[1][1] == "pending"