"""Unit tests for related incident search and audit helpers."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any, Iterable, List

import pytest

from core.config import settings
from core.jobs.fingerprint_service import (
    FingerprintNotFoundError,
    FingerprintSearchService,
    FingerprintUnavailableError,
)
from core.jobs.models import (
    FingerprintStatus,
    RelatedIncidentMatch,
    RelatedIncidentQuery,
    RelatedIncidentSearchRequest,
    RelatedIncidentSearchResult,
    VisibilityScope,
)
from core.security.audit import AnalystAuditRecorder


class _FakeSessionContext:
    def __init__(self, session_obj):
        self._session = session_obj

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeFingerprintSession:
    def __init__(self):
        self.added: List[Any] = []
        self.flush_calls = 0

    def begin(self):
        session = self

        class _Txn:
            async def __aenter__(self):
                return session

            async def __aexit__(self, exc_type, exc, tb):
                return False

        return _Txn()

    def add(self, entry: Any) -> None:
        self.added.append(entry)

    async def flush(self) -> None:
        self.flush_calls += 1


class _FakeSession:
    def __init__(self):
        self.added: List[Any] = []

    def add_all(self, entries: Iterable[object]) -> None:
        self.added.extend(entries)

    async def flush(self) -> None:  # pragma: no cover - simple stub
        return None


@pytest.mark.asyncio
async def test_related_for_session_generates_audit_token(monkeypatch):
    service = FingerprintSearchService()
    fake_session = _FakeFingerprintSession()
    service._session_factory = lambda: _FakeSessionContext(fake_session)  # type: ignore[attr-defined]

    source_tenant = uuid.uuid4()
    fingerprint = SimpleNamespace(
        embedding_vector=[0.2, 0.4],
        tenant_id=source_tenant,
    )

    async def fake_load(session, session_uuid):
        assert session is fake_session
        assert isinstance(session_uuid, uuid.UUID)
        return fingerprint

    called_kwargs = {}

    async def fake_query(session, embedding, **kwargs):
        assert session is fake_session
        called_kwargs.update(kwargs)
        assert embedding == fingerprint.embedding_vector
        match_same = RelatedIncidentMatch(
            session_id=str(uuid.uuid4()),
            tenant_id=str(source_tenant),
            relevance=0.9,
            summary="same workspace",
            detected_platform="uipath",
            fingerprint_status=FingerprintStatus.AVAILABLE,
            safeguards=["safe"],
        )
        match_cross = RelatedIncidentMatch(
            session_id=str(uuid.uuid4()),
            tenant_id=str(uuid.uuid4()),
            relevance=0.8,
            summary="cross workspace",
            detected_platform="blue_prism",
            fingerprint_status=FingerprintStatus.AVAILABLE,
            safeguards=[],
        )
        return [match_same, match_cross]

    monkeypatch.setattr(service, "_load_fingerprint", fake_load)
    monkeypatch.setattr(service, "_execute_similarity_query", fake_query)

    query = RelatedIncidentQuery(
        session_id=str(uuid.uuid4()),
        scope=VisibilityScope.MULTI_TENANT,
        min_relevance=0.4,
        limit=5,
    )

    result = await service.related_for_session(query)

    assert len(result.results) == 2
    assert result.audit_token is not None
    assert called_kwargs["min_relevance"] == 0.4
    assert called_kwargs["limit"] == 5
    assert called_kwargs["source_tenant_id"] == source_tenant
    assert called_kwargs["exclude_session_id"] is not None


@pytest.mark.asyncio
async def test_related_for_session_missing_fingerprint(monkeypatch):
    service = FingerprintSearchService()
    fake_session = _FakeFingerprintSession()
    service._session_factory = lambda: _FakeSessionContext(fake_session)  # type: ignore[attr-defined]

    async def fake_load(session, session_uuid):
        return None

    monkeypatch.setattr(service, "_load_fingerprint", fake_load)

    query = RelatedIncidentQuery(session_id=str(uuid.uuid4()))
    with pytest.raises(FingerprintNotFoundError):
        await service.related_for_session(query)


@pytest.mark.asyncio
async def test_related_for_session_records_guardrail_when_embedding_missing(monkeypatch):
    service = FingerprintSearchService()
    fake_session = _FakeFingerprintSession()
    service._session_factory = lambda: _FakeSessionContext(fake_session)  # type: ignore[attr-defined]

    tenant_id = uuid.uuid4()
    session_id = uuid.uuid4()
    fingerprint = SimpleNamespace(
        session_id=session_id,
        tenant_id=tenant_id,
        embedding_vector=None,
        fingerprint_status=FingerprintStatus.DEGRADED.value,
        safeguard_notes={},
    )

    async def fake_load(session, session_uuid):
        assert session is fake_session
        assert session_uuid == session_id
        return fingerprint

    async def fail_query(*args, **kwargs):  # pragma: no cover - should not run
        raise AssertionError("Similarity query should not execute when fingerprint missing")

    monkeypatch.setattr(service, "_load_fingerprint", fake_load)
    monkeypatch.setattr(service, "_execute_similarity_query", fail_query)

    query = RelatedIncidentQuery(session_id=str(session_id))

    with pytest.raises(FingerprintUnavailableError):
        await service.related_for_session(query)

    assert fingerprint.fingerprint_status == FingerprintStatus.MISSING.value
    assert "fingerprint" in fingerprint.safeguard_notes
    guardrail_notes = fingerprint.safeguard_notes["fingerprint"]
    assert any("unavailable" in note.lower() for note in guardrail_notes)
    assert fingerprint in fake_session.added
    assert fake_session.flush_calls >= 1


class _FakeEmbeddingService:
    async def embed_text(self, text: str) -> List[float]:
        return [0.5, 0.6]


@pytest.mark.asyncio
async def test_text_search_constrains_allowed_workspaces(monkeypatch):
    service = FingerprintSearchService()
    fake_session = object()
    service._session_factory = lambda: _FakeSessionContext(fake_session)  # type: ignore[attr-defined]

    fake_embedding = _FakeEmbeddingService()

    async def fake_ensure():
        return fake_embedding

    monkeypatch.setattr(service, "_ensure_embedding_service", fake_ensure)

    captured_kwargs = {}

    async def fake_query(session, embedding, **kwargs):
        captured_kwargs.update(kwargs)
        assert session is fake_session
        assert embedding == [0.5, 0.6]
        return [
            RelatedIncidentMatch(
                session_id=str(uuid.uuid4()),
                tenant_id=str(kwargs["source_tenant_id"]),
                relevance=0.7,
                summary="tenant match",
                detected_platform="unknown",
            )
        ]

    monkeypatch.setattr(service, "_execute_similarity_query", fake_query)

    workspace_id = str(uuid.uuid4())
    allowed = [workspace_id]
    request = RelatedIncidentSearchRequest(
        query="error summary",
        scope=VisibilityScope.TENANT_ONLY,
        workspace_id=workspace_id,
        min_relevance=0.2,
        limit=2,
    )

    result = await service.search_by_text(request, allowed_workspace_ids=allowed)

    assert len(result.results) == 1
    assert result.audit_token is None
    assert captured_kwargs["min_relevance"] == 0.2
    assert captured_kwargs["limit"] == 2
    assert captured_kwargs["source_tenant_id"] == uuid.UUID(workspace_id)
    assert captured_kwargs["allowed_tenant_ids"] == [uuid.UUID(workspace_id)]


def test_search_result_cross_workspace_pairs():
    source_workspace = str(uuid.uuid4())
    matches = [
        RelatedIncidentMatch(
            session_id="session-a",
            tenant_id=source_workspace,
            relevance=0.9,
            summary="same",
            detected_platform="unknown",
        ),
        RelatedIncidentMatch(
            session_id="session-b",
            tenant_id=str(uuid.uuid4()),
            relevance=0.8,
            summary="cross",
            detected_platform="unknown",
        ),
    ]

    result = RelatedIncidentSearchResult(
        results=matches,
        source_session_id="base",
        source_workspace_id=source_workspace,
    )

    pairs = result.cross_workspace_pairs()
    assert pairs == [(matches[1].tenant_id, matches[1].session_id)]


def test_generate_audit_token_only_for_cross_workspace():
    same_workspace = str(uuid.uuid4())
    matches = [
        RelatedIncidentMatch(
            session_id="s1",
            tenant_id=same_workspace,
            relevance=0.5,
            summary="same",
            detected_platform="unknown",
        ),
        RelatedIncidentMatch(
            session_id="s2",
            tenant_id=str(uuid.uuid4()),
            relevance=0.7,
            summary="cross",
            detected_platform="unknown",
        ),
    ]

    token = FingerprintSearchService._generate_audit_token(matches, same_workspace)
    assert token is not None

    token_none = FingerprintSearchService._generate_audit_token(matches, None)
    assert token_none is None


@pytest.mark.asyncio
async def test_audit_recorder_respects_feature_flag(monkeypatch):
    recorder = AnalystAuditRecorder()
    session = _FakeSession()

    recorder._session_factory = lambda: _FakeSessionContext(session)  # type: ignore[attr-defined]

    monkeypatch.setitem(
        settings.__dict__,
        "related_incidents",
        SimpleNamespace(AUDIT_TRAIL_ENABLED=False),
    )

    count = await recorder.record_related_incident_views(
        analyst_id=str(uuid.uuid4()),
        source_workspace_id=str(uuid.uuid4()),
        source_session_id=str(uuid.uuid4()),
        related_pairs=[(str(uuid.uuid4()), str(uuid.uuid4()))],
    )

    assert count == 0
    assert session.added == []


@pytest.mark.asyncio
async def test_audit_recorder_inserts_only_cross_workspace(monkeypatch):
    recorder = AnalystAuditRecorder()
    session = _FakeSession()

    recorder._session_factory = lambda: _FakeSessionContext(session)  # type: ignore[attr-defined]

    monkeypatch.setitem(
        settings.__dict__,
        "related_incidents",
        SimpleNamespace(AUDIT_TRAIL_ENABLED=True),
    )

    source_workspace = uuid.uuid4()
    count = await recorder.record_related_incident_views(
        analyst_id=str(uuid.uuid4()),
        source_workspace_id=str(source_workspace),
        source_session_id=str(uuid.uuid4()),
        related_pairs=[
            (str(source_workspace), str(uuid.uuid4())),  # should be ignored
            (str(uuid.uuid4()), str(uuid.uuid4())),      # captured
            ("not-a-uuid", "also-bad"),                # ignored
        ],
    )

    assert count == 1
    assert len(session.added) == 1
    entry = session.added[0]
    assert str(entry.source_workspace_id) == str(source_workspace)
    assert str(entry.related_workspace_id) != str(entry.source_workspace_id)


def test_prepare_entries_filters_invalid(monkeypatch):
    recorder = AnalystAuditRecorder()

    source_workspace = uuid.uuid4()
    source_session = uuid.uuid4()
    analyst_id = uuid.uuid4()

    entries = recorder._prepare_entries(  # type: ignore[attr-defined]
        analyst_id,
        source_workspace,
        source_session,
        [
            (str(source_workspace), str(uuid.uuid4())),
            (str(uuid.uuid4()), "bad-session"),
            (str(uuid.uuid4()), str(uuid.uuid4())),
        ],
    )

    assert len(entries) == 1
    assert str(entries[0].analyst_id) == str(analyst_id)
    assert str(entries[0].source_workspace_id) == str(source_workspace)