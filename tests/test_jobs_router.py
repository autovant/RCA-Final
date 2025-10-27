from datetime import datetime

import pytest
from fastapi import HTTPException

from apps.api.routers import jobs as jobs_router


class _FakeFingerprint:
    def __init__(self, session_id: str):
        self._payload = {
            "session_id": session_id,
            "tenant_id": "3fbb72a3-5a0c-4e19-b665-382e8df1ad9c",
            "fingerprint_status": "available",
            "visibility_scope": "multi_tenant",
            "summary_text": "Example summary",
            "relevance_threshold": 0.42,
            "safeguard_notes": {"notes": ["ok"]},
            "created_at": "2024-08-31T12:00:00+00:00",
            "updated_at": "2024-08-31T12:05:00+00:00",
        }
        self.embedding_vector = [0.1, 0.2]

    def to_dict(self):  # pragma: no cover - trivially exercised
        return self._payload


class _FingerprintServiceStub:
    def __init__(self, fingerprint):
        self._fingerprint = fingerprint

    async def get_job_fingerprint(self, job_id: str):  # pragma: no cover - simple stub
        return self._fingerprint


class _FakeJobRecord:
    def __init__(self, status: str = "running"):
        self.status = status


class _FakeJobEvent:
    def __init__(self, event_id: str, job_id: str, event_type: str, created_at: str = "2024-01-01T00:00:00"):
        self._payload = {
            "id": event_id,
            "job_id": job_id,
            "event_type": event_type,
            "data": {"message": event_type},
            "created_at": created_at,
        }

    def to_dict(self):
        return self._payload


class _JobServiceEventsStub:
    def __init__(self, job=None, events=None):
        self._job = job
        self._events = events or []
        self.last_since = None

    async def get_job(self, job_id: str):
        return self._job

    async def get_job_events_since(self, job_id: str, since):
        self.last_since = since
        return list(self._events)


class _JobServiceActionStub:
    def __init__(self, job=None, cancel_result=True, restart_result=None, pause_result=True, resume_result=True):
        self._job = job
        self._cancel_result = cancel_result
        self._restart_result = restart_result
        self._pause_result = pause_result
        self._resume_result = resume_result
        self.cancel_calls = []
        self.restart_calls = []
        self.pause_calls = []
        self.resume_calls = []

    async def get_job(self, job_id: str):
        return self._job

    async def cancel_job(self, job_id: str, reason: str = "User cancelled"):
        self.cancel_calls.append((job_id, reason))
        return self._cancel_result

    async def restart_job(self, job_id: str):
        self.restart_calls.append(job_id)
        return self._restart_result

    async def pause_job(self, job_id: str, reason: str = "Paused"):
        self.pause_calls.append((job_id, reason))
        return self._pause_result

    async def resume_job(self, job_id: str, note: str = "Resumed"):
        self.resume_calls.append((job_id, note))
        return self._resume_result


@pytest.mark.asyncio
async def test_get_job_fingerprint_returns_payload(monkeypatch):
    fingerprint = _FakeFingerprint("7d7f7651-a5a9-40f5-b3a3-5f51051d6a0e")
    service = _FingerprintServiceStub(fingerprint)
    monkeypatch.setattr(jobs_router, "job_service", service)

    response = await jobs_router.get_job_fingerprint("7d7f7651-a5a9-40f5-b3a3-5f51051d6a0e")

    assert response.job_id == "7d7f7651-a5a9-40f5-b3a3-5f51051d6a0e"
    assert response.tenant_id == "3fbb72a3-5a0c-4e19-b665-382e8df1ad9c"
    assert response.fingerprint_status == "available"
    assert response.visibility_scope == "multi_tenant"
    assert response.summary_text == "Example summary"
    assert response.relevance_threshold == pytest.approx(0.42)
    assert response.safeguard_notes == {"notes": ["ok"]}
    assert response.embedding_present is True
    assert response.created_at == "2024-08-31T12:00:00+00:00"
    assert response.updated_at == "2024-08-31T12:05:00+00:00"


class _FingerprintServiceMissingStub:
    async def get_job_fingerprint(self, job_id: str):  # pragma: no cover - simple stub
        return None


@pytest.mark.asyncio
async def test_get_job_fingerprint_missing_returns_404(monkeypatch):
    monkeypatch.setattr(jobs_router, "job_service", _FingerprintServiceMissingStub())

    with pytest.raises(HTTPException) as exc:
        await jobs_router.get_job_fingerprint("non-existent")

    assert exc.value.status_code == 404
    assert "Fingerprint not found" in exc.value.detail


@pytest.mark.asyncio
async def test_job_events_returns_trimmed_list(monkeypatch):
    job = _FakeJobRecord()
    events = [
        _FakeJobEvent("evt-1", "job-123", "queued", created_at="2024-01-01T00:00:00"),
        _FakeJobEvent("evt-2", "job-123", "running", created_at="2024-01-01T00:05:00"),
        _FakeJobEvent("evt-3", "job-123", "completed", created_at="2024-01-01T00:10:00"),
    ]
    service = _JobServiceEventsStub(job=job, events=events)
    monkeypatch.setattr(jobs_router, "job_service", service)

    responses = await jobs_router.job_events("job-123", since=None, limit=2)

    assert len(responses) == 2
    assert [event.id for event in responses] == ["evt-2", "evt-3"]
    assert service.last_since is None


@pytest.mark.asyncio
async def test_job_events_returns_empty_when_no_events(monkeypatch):
    job = _FakeJobRecord()
    service = _JobServiceEventsStub(job=job, events=[])
    monkeypatch.setattr(jobs_router, "job_service", service)

    responses = await jobs_router.job_events("job-789", since=None, limit=5)

    assert responses == []
    assert service.last_since is None


@pytest.mark.asyncio
async def test_job_events_invalid_since_raises(monkeypatch):
    job = _FakeJobRecord()
    service = _JobServiceEventsStub(job=job, events=[])
    monkeypatch.setattr(jobs_router, "job_service", service)

    with pytest.raises(HTTPException) as exc:
        await jobs_router.job_events("job-456", since="not-a-valid-timestamp")

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_job_events_since_filter_passed_to_service(monkeypatch):
    job = _FakeJobRecord()
    service = _JobServiceEventsStub(job=job, events=[])
    monkeypatch.setattr(jobs_router, "job_service", service)

    await jobs_router.job_events("job-123", since="2024-06-01T12:30:00Z")

    assert service.last_since == datetime(2024, 6, 1, 12, 30)


@pytest.mark.asyncio
async def test_job_events_missing_job_returns_404(monkeypatch):
    service = _JobServiceEventsStub(job=None, events=[])
    monkeypatch.setattr(jobs_router, "job_service", service)

    with pytest.raises(HTTPException) as exc:
        await jobs_router.job_events("job-missing", since=None)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_cancel_job_success(monkeypatch):
    job = _FakeJobRecord(status="running")
    service = _JobServiceActionStub(job=job, cancel_result=True)
    monkeypatch.setattr(jobs_router, "job_service", service)

    payload = jobs_router.JobCancelRequest(reason="maintenance window")
    response = await jobs_router.cancel_job("job-123", payload)

    assert response.status == "cancelled"
    assert response.job_id == "job-123"
    assert service.cancel_calls == [("job-123", "maintenance window")]


@pytest.mark.asyncio
async def test_cancel_job_conflict_when_terminal(monkeypatch):
    job = _FakeJobRecord(status="completed")
    service = _JobServiceActionStub(job=job)
    monkeypatch.setattr(jobs_router, "job_service", service)

    with pytest.raises(HTTPException) as exc:
        await jobs_router.cancel_job("job-123", jobs_router.JobCancelRequest())

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_cancel_job_missing(monkeypatch):
    service = _JobServiceActionStub(job=None)
    monkeypatch.setattr(jobs_router, "job_service", service)

    with pytest.raises(HTTPException) as exc:
        await jobs_router.cancel_job("job-123")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_pause_job_success(monkeypatch):
    job = _FakeJobRecord(status="running")
    service = _JobServiceActionStub(job=job)
    monkeypatch.setattr(jobs_router, "job_service", service)

    payload = jobs_router.JobPauseRequest(reason="human review")
    response = await jobs_router.pause_job("job-321", payload)

    assert response.status == "paused"
    assert response.job_id == "job-321"
    assert service.pause_calls == [("job-321", "human review")]


@pytest.mark.asyncio
async def test_pause_job_conflict_when_not_running(monkeypatch):
    job = _FakeJobRecord(status="completed")
    service = _JobServiceActionStub(job=job)
    monkeypatch.setattr(jobs_router, "job_service", service)

    with pytest.raises(HTTPException) as exc:
        await jobs_router.pause_job("job-321")

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_pause_job_missing(monkeypatch):
    service = _JobServiceActionStub(job=None)
    monkeypatch.setattr(jobs_router, "job_service", service)

    with pytest.raises(HTTPException) as exc:
        await jobs_router.pause_job("job-missing")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_resume_job_success(monkeypatch):
    job = _FakeJobRecord(status="paused")
    service = _JobServiceActionStub(job=job)
    monkeypatch.setattr(jobs_router, "job_service", service)

    payload = jobs_router.JobResumeRequest(note="resume now")
    response = await jobs_router.resume_job("job-654", payload)

    assert response.status == "running"
    assert response.job_id == "job-654"
    assert service.resume_calls == [("job-654", "resume now")]


@pytest.mark.asyncio
async def test_resume_job_conflict_when_not_paused(monkeypatch):
    job = _FakeJobRecord(status="running")
    service = _JobServiceActionStub(job=job)
    monkeypatch.setattr(jobs_router, "job_service", service)

    with pytest.raises(HTTPException) as exc:
        await jobs_router.resume_job("job-654")

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_resume_job_missing(monkeypatch):
    service = _JobServiceActionStub(job=None)
    monkeypatch.setattr(jobs_router, "job_service", service)

    with pytest.raises(HTTPException) as exc:
        await jobs_router.resume_job("job-missing")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_retry_job_success(monkeypatch):
    existing = _FakeJobRecord(status="failed")
    restarted = _FakeJobRecord(status="pending")
    service = _JobServiceActionStub(job=existing, restart_result=restarted)
    monkeypatch.setattr(jobs_router, "job_service", service)

    response = await jobs_router.retry_job("job-456")

    assert response.status == "pending"
    assert response.job_id == "job-456"
    assert service.restart_calls == ["job-456"]


@pytest.mark.asyncio
async def test_retry_job_conflict_when_not_terminal(monkeypatch):
    existing = _FakeJobRecord(status="running")
    service = _JobServiceActionStub(job=existing)
    monkeypatch.setattr(jobs_router, "job_service", service)

    with pytest.raises(HTTPException) as exc:
        await jobs_router.retry_job("job-789")

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_retry_job_missing(monkeypatch):
    service = _JobServiceActionStub(job=None)
    monkeypatch.setattr(jobs_router, "job_service", service)

    with pytest.raises(HTTPException) as exc:
        await jobs_router.retry_job("job-000")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_stream_job_events_returns_event_source(monkeypatch):
    job = _FakeJobRecord()
    service = _JobServiceEventsStub(job=job, events=[])
    monkeypatch.setattr(jobs_router, "job_service", service)

    calls = []

    async def _fake_generator():
        yield {"event": "job-event", "data": "{}"}

    def _fake_event_stream(job_id: str):
        calls.append(job_id)
        return _fake_generator()

    class _EventSourceResponseStub:
        def __init__(self, source):
            self.source = source

    monkeypatch.setattr(jobs_router, "job_event_stream", _fake_event_stream)
    monkeypatch.setattr(jobs_router, "EventSourceResponse", _EventSourceResponseStub)

    response = await jobs_router.stream_job_events("job-123")

    assert isinstance(response, _EventSourceResponseStub)
    assert calls == ["job-123"]
    assert response.source is not None


@pytest.mark.asyncio
async def test_stream_job_events_missing_job(monkeypatch):
    service = _JobServiceEventsStub(job=None, events=[])
    monkeypatch.setattr(jobs_router, "job_service", service)

    with pytest.raises(HTTPException) as exc:
        await jobs_router.stream_job_events("unknown-job")

    assert exc.value.status_code == 404

