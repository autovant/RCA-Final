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