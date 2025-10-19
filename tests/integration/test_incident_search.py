"""Integration-style tests for incident fingerprint search flows."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any, Dict, List, cast

import pytest

from core.jobs.fingerprint_service import FingerprintSearchService
from core.jobs.models import (
    FingerprintStatus,
    RelatedIncidentMatch,
    RelatedIncidentQuery,
    VisibilityScope,
)
from core.jobs.processor import FileSummary, JobProcessor
from core.jobs.service import JobService

pytestmark = pytest.mark.integration


class _JobServiceStub:
    async def create_job_event(self, *args, **kwargs):  # pragma: no cover - simple stub
        return None

    async def publish_session_events(self, session):  # pragma: no cover - simple stub
        return None


class _FakeResult:
    def __init__(self, record):
        self._record = record

    def scalar_one_or_none(self):
        return self._record

    def fetchall(self):  # pragma: no cover - unused in tests
        return []


class _FakeSession:
    def __init__(self):
        self.record = None
        self.added: List[Any] = []
        self.flush_calls = 0
        self.info: Dict[str, Any] = {}

    def begin(self):
        class _Txn:
            def __init__(self, session):
                self._session = session

            async def __aenter__(self):  # pragma: no cover - trivial wrapper
                return self._session

            async def __aexit__(self, exc_type, exc, tb):  # pragma: no cover - trivial wrapper
                return False

        return _Txn(self)

    async def __aenter__(self):  # pragma: no cover - compatibility shim
        return self

    async def __aexit__(self, exc_type, exc, tb):  # pragma: no cover - compatibility shim
        return False

    async def execute(self, stmt):  # pragma: no cover - minimal emulation
        return _FakeResult(self.record)

    def add(self, record):
        self.added.append(record)
        if getattr(record, "session_id", None) is not None:
            self.record = record

    async def flush(self):
        self.flush_calls += 1


class _SessionContext:
    def __init__(self, session: _FakeSession):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _EmbeddingServiceStub:
    def __init__(self, vector: List[float]):
        self._vector = vector

    async def embed_text(self, text: str) -> List[float]:
        return list(self._vector)


def _build_summary() -> FileSummary:
    return FileSummary(
        file_id="file-1",
        filename="file-1.log",
        checksum="checksum",
        file_size=10,
        content_type="text/plain",
        line_count=5,
        error_count=0,
        warning_count=0,
        critical_count=0,
        info_count=5,
        sample_head=["line1"],
        sample_tail=["line5"],
        top_keywords=["info"],
        chunk_count=1,
    )


@pytest.mark.asyncio
async def test_related_search_consumes_fingerprint_from_processor(monkeypatch):
    monkeypatch.setattr(
        "core.jobs.processor.settings",
        SimpleNamespace(
            RELATED_INCIDENTS_ENABLED=True,
            RELATED_INCIDENTS_DEFAULT_SCOPE="multi_tenant",
            RELATED_INCIDENTS_MIN_RELEVANCE=0.6,
        ),
    )
    job_service = _JobServiceStub()
    processor = JobProcessor(cast(JobService, job_service))
    fake_session = _FakeSession()
    processor._session_factory = lambda: _SessionContext(fake_session)  # type: ignore[assignment]

    embedding_vector = [0.25, 0.5, 0.75]

    async def _ensure_embedding():
        return _EmbeddingServiceStub(embedding_vector)

    monkeypatch.setattr(processor, "_ensure_embedding_service", _ensure_embedding)

    tenant_id = uuid.uuid4()
    job: Any = SimpleNamespace(id=uuid.uuid4(), input_manifest={"tenant_id": str(tenant_id)}, source={})

    dto = await processor._index_incident_fingerprint(  # type: ignore[arg-type]
        job,
        [_build_summary()],
        {"summary": "Integration summary"},
    )

    assert dto is not None
    assert dto.fingerprint_status is FingerprintStatus.AVAILABLE
    assert fake_session.record is not None
    fingerprint_record = fake_session.record

    service = FingerprintSearchService()
    service._session_factory = lambda: _SessionContext(fake_session)  # type: ignore[assignment]

    async def _load(session, session_uuid):
        assert session is fake_session
        assert session_uuid == fingerprint_record.session_id
        return fingerprint_record

    captured = {}

    async def _similarity(session, embedding, **kwargs):
        assert session is fake_session
        captured["embedding"] = list(embedding)
        captured["kwargs"] = kwargs
        return [
            RelatedIncidentMatch(
                session_id=str(uuid.uuid4()),
                tenant_id=str(tenant_id),
                relevance=0.91,
                summary="match",
                detected_platform="unknown",
                fingerprint_status=FingerprintStatus.AVAILABLE,
                safeguards=[],
            )
        ]

    monkeypatch.setattr(service, "_load_fingerprint", _load)
    monkeypatch.setattr(service, "_execute_similarity_query", _similarity)

    query = RelatedIncidentQuery(
        session_id=str(fingerprint_record.session_id),
        scope=VisibilityScope.TENANT_ONLY,
        min_relevance=0.4,
        limit=5,
    )

    result = await service.related_for_session(query)

    assert captured["embedding"] == embedding_vector
    assert captured["kwargs"]["source_tenant_id"] == tenant_id
    assert len(result.results) == 1
    assert result.results[0].fingerprint_status is FingerprintStatus.AVAILABLE
    assert result.results[0].summary == "match"
    assert result.audit_token is None
