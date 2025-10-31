"""Tests for the job processor orchestration logic."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, List, cast
import uuid

import pytest

pytest.importorskip("aiofiles")

from core.files import DetectionInput
from core.files.telemetry import PipelineStage
from core.jobs.models import (
    FingerprintStatus,
    IncidentFingerprintDTO,
    VisibilityScope,
)
from core.jobs.processor import FileDescriptor, FileSummary, JobProcessor
from core.jobs.service import JobService


class StubJobService:
    def __init__(self):
        self.events = []

    async def create_job_event(self, job_id: str, event_type: str, data=None, session=None):
        self.events.append((job_id, event_type, data or {}))

    async def publish_session_events(self, session):  # pragma: no cover - simple stub
        return None


class StubProcessor(JobProcessor):
    def __init__(self, descriptors, summaries, job_service):
        super().__init__(job_service)
        self._descriptors = descriptors
        self._summaries = summaries
        self.fingerprint_calls = 0
        self.detection_calls = 0

    async def _list_job_files(self, job_id: str):
        return self._descriptors

    async def _process_single_file(
        self,
        job,
        descriptor: FileDescriptor,
        *,
        position: int,
        total_files: int,
        detection_collector=None,
    ):
        await self._job_service.create_job_event(
            str(job.id),
            "file-processing-started",
            {
                "file_id": descriptor.id,
                "file_number": position,
                "total_files": total_files,
            },
        )
        summary = self._summaries[descriptor.id]
        await self._job_service.create_job_event(
            str(job.id),
            "file-processing-completed",
            {
                "file_id": descriptor.id,
                "chunks": summary.chunk_count,
                "file_number": position,
                "total_files": total_files,
            },
        )
        return summary

    async def _handle_platform_detection(self, job, inputs):  # pragma: no cover - override in stub
        self.detection_calls += 1
        return None

    async def _generate_embeddings(self, texts):
        return [[1.0] * max(1, len(texts)) for _ in texts]

    async def _run_llm_analysis(self, job, summaries, mode):
        return {"summary": f"{mode}-analysis", "provider": "stub", "model": "stub"}

    async def _index_incident_fingerprint(self, job, summaries, llm_output):
        self.fingerprint_calls += 1
        return IncidentFingerprintDTO(
            session_id=str(job.id),
            tenant_id="tenant-1",
            summary_text="stub summary",
            relevance_threshold=0.6,
            visibility_scope=VisibilityScope.MULTI_TENANT,
            fingerprint_status=FingerprintStatus.AVAILABLE,
            safeguard_notes={},
            embedding_present=True,
        )


class _FakeSessionResult:
    def __init__(self, record):
        self._record = record

    def scalar_one_or_none(self):
        return self._record


class _FakeFingerprintSession:
    def __init__(self):
        self.record = None
        self.added = []
        self.flush_calls = 0
        self.info = {}

    def begin(self):
        class _Txn:
            def __init__(self, session):
                self._session = session

            async def __aenter__(self):  # pragma: no cover - trivial context manager
                return self._session

            async def __aexit__(self, exc_type, exc, tb):  # pragma: no cover - trivial context manager
                return False

        return _Txn(self)

    async def execute(self, stmt):  # pragma: no cover - simple stub behaviour
        return _FakeSessionResult(self.record)

    def add(self, record):
        self.added.append(record)
        if getattr(record, "session_id", None) is not None:
            self.record = record

    async def flush(self):
        self.flush_calls += 1


class _FakeSessionContext:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _StubCacheSession:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    async def commit(self):  # pragma: no cover - simple counter
        self.commits += 1

    async def rollback(self):  # pragma: no cover - simple counter
        self.rollbacks += 1


def _summary(file_id: str, filename: str, errors: int, warnings: int) -> FileSummary:
    return FileSummary(
        file_id=file_id,
        filename=filename,
        checksum="checksum",
        file_size=42,
        content_type="text/plain",
        line_count=10,
        error_count=errors,
        warning_count=warnings,
        critical_count=0,
        info_count=10 - errors - warnings,
        sample_head=["line1"],
        sample_tail=["line10"],
        top_keywords=["error", "info"],
        chunk_count=1,
    )


def _stub_ingestion_settings(**overrides: Any) -> SimpleNamespace:
    defaults = {
        "CHUNK_MAX_CHARACTERS": 1800,
        "CHUNK_MIN_CHARACTERS": 600,
        "CHUNK_OVERLAP_CHARACTERS": 200,
        "LINE_MAX_CHARACTERS": 1600,
        "EMBED_BATCH_SIZE": 32,
    }
    defaults.update(overrides)

    class _Flags:
        @staticmethod
        def is_enabled(_key: str) -> bool:
            return False

    ingestion = SimpleNamespace(**defaults)
    return SimpleNamespace(ingestion=ingestion, feature_flags=_Flags())


@pytest.mark.asyncio
async def test_process_rca_analysis_compiles_summary():
    descriptors = [
        FileDescriptor(
            id="file-1",
            path="/tmp/file-1.log",
            name="file-1.log",
            checksum="checksum",
            content_type="text/plain",
            metadata=None,
            size_bytes=42,
        )
    ]
    summaries = {"file-1": _summary("file-1", "file-1.log", errors=2, warnings=1)}
    job_service = StubJobService()
    processor = StubProcessor(descriptors, summaries, job_service)

    job: Any = SimpleNamespace(
        id="job-1",
        job_type="rca_analysis",
        provider="stub",
        model="stub",
        input_manifest={},
    )
    result = await processor.process_rca_analysis(job)  # type: ignore[arg-type]

    assert result["analysis_type"] == "rca_analysis"
    assert result["metrics"]["errors"] == 2
    assert result["llm"]["summary"] == "rca_analysis-analysis"
    assert processor.fingerprint_calls == 1
    assert processor.detection_calls == 1
    assert result["fingerprint"]["fingerprint_status"] == "available"
    assert result["fingerprint"]["visibility_scope"] == "multi_tenant"
    assert any(
        event_type == "analysis-progress" and data.get("step") == "report" and data.get("status") in {"completed", "success"}
        for _, event_type, data in job_service.events
    )


def test_chunk_lines_respects_line_limits(monkeypatch):
    settings_stub = _stub_ingestion_settings(
        CHUNK_MAX_CHARACTERS=30,
        CHUNK_MIN_CHARACTERS=10,
        CHUNK_OVERLAP_CHARACTERS=5,
        LINE_MAX_CHARACTERS=12,
    )
    monkeypatch.setattr("core.jobs.processor.settings", settings_stub)

    job_service = StubJobService()
    processor = JobProcessor(cast(JobService, job_service))

    lines = ["A" * 35, "B" * 12]
    chunks = processor._chunk_lines(lines)

    assert len(chunks) == 2
    assert all(len(chunk) <= 30 for chunk in chunks)
    assert max(len(part) for chunk in chunks for part in chunk.split("\n")) <= 12


def test_sanitise_pipeline_metadata_limits_complex_values():
    processor = JobProcessor(cast(JobService, StubJobService()))

    big_text = "x" * 600
    metadata = {
        "long_text": big_text,
        "numbers": list(range(15)),
        "mapping": {f"key-{idx}": idx for idx in range(12)},
        "custom": SimpleNamespace(name="example"),
        "none_value": None,
    }

    cleaned = processor._sanitise_pipeline_metadata(metadata)

    assert "none_value" not in cleaned
    assert len(cleaned["long_text"]) == 512
    assert cleaned["numbers"][-1] == "..."
    assert len(cleaned["numbers"]) == 11
    assert cleaned["mapping"]["__truncated__"] is True
    assert cleaned["custom"] == "namespace(name='example')"


@pytest.mark.asyncio
async def test_emit_progress_event_sanitises_details():
    job_service = StubJobService()
    processor = JobProcessor(cast(JobService, job_service))

    details = {
        "long_text": "y" * 600,
        "numbers": list(range(15)),
        "mapping": {f"key-{idx}": idx for idx in range(12)},
        "custom": SimpleNamespace(value="example"),
    }

    await processor._emit_progress_event(
        "job-1",
        "chunking",
        "completed",
        label="L" * 200,
        message="M" * 600,
        details=details,
    )

    assert job_service.events, "expected a progress event to be recorded"
    _, _, payload = job_service.events[-1]
    progress_details = payload.get("details")
    assert progress_details is not None
    assert len(progress_details["long_text"]) == 512
    assert progress_details["numbers"][-1] == "..."
    assert len(progress_details["numbers"]) == 11
    assert progress_details["mapping"]["__truncated__"] is True
    assert progress_details["custom"].startswith("namespace(")
    assert len(payload["label"]) == 128
    assert payload["label"].endswith("...")
    assert len(payload["message"]) == 512
    assert payload["message"].endswith("...")


def test_maybe_collect_detection_input_sanitises_metadata():
    job_service = StubJobService()
    processor = JobProcessor(cast(JobService, job_service))

    descriptor = FileDescriptor(
        id="file-1",
        path="/tmp/file-1.log",
        name="file-1.log",
        checksum="checksum",
        content_type="text/plain",
        metadata={"descriptor_only": "y" * 600},
        size_bytes=128,
    )

    file_record = SimpleNamespace(
        metadata={
            "long": "x" * 1024,
            "list": list(range(15)),
            "none_value": None,
        },
        original_filename="file-1.log",
        filename=None,
        content_type="text/plain",
    )

    collected: List[DetectionInput] = []

    processor._maybe_collect_detection_input(
        collected.append,
        descriptor,
        cast(Any, file_record),
        "content",
    )

    assert len(collected) == 1
    detection_input = collected[0]
    assert detection_input.name == "file-1.log"
    assert len(detection_input.content) <= 8000
    metadata = dict(detection_input.metadata)
    assert "none_value" not in metadata
    assert len(metadata["long"]) == 512
    assert metadata["list"][-1] == "..."
    assert len(metadata["list"]) == 11
    assert len(metadata["descriptor_only"]) == 512
    assert set(metadata["descriptor_only"]) == {"y"}


@pytest.mark.asyncio
async def test_index_incident_fingerprint_marks_degraded_when_embedding_fails(monkeypatch):
    monkeypatch.setattr(
        "core.jobs.processor.settings",
        SimpleNamespace(
            RELATED_INCIDENTS_ENABLED=True,
            RELATED_INCIDENTS_DEFAULT_SCOPE="multi_tenant",
            RELATED_INCIDENTS_MIN_RELEVANCE=0.6,
        ),
    )
    job_service = StubJobService()
    processor = JobProcessor(cast(JobService, job_service))
    fake_session = _FakeFingerprintSession()
    processor._session_factory = lambda: _FakeSessionContext(fake_session)  # type: ignore[assignment]

    class _FailingEmbeddingService:
        async def embed_text(self, text: str):  # pragma: no cover - simple stub
            raise RuntimeError("embedding failed")

    async def _provide_embedding_service():
        return _FailingEmbeddingService()

    monkeypatch.setattr(processor, "_ensure_embedding_service", _provide_embedding_service)

    tenant_id = uuid.uuid4()
    job: Any = SimpleNamespace(id=uuid.uuid4(), input_manifest={"tenant_id": str(tenant_id)}, source={})
    summaries = [
        FileSummary(
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
    ]

    dto = await processor._index_incident_fingerprint(  # type: ignore[arg-type]
        job,
        summaries,
        {"summary": "Integration summary"},
    )

    assert dto is not None
    assert dto.fingerprint_status is FingerprintStatus.DEGRADED
    assert dto.embedding_present is False
    assert fake_session.record is not None
    assert fake_session.record.fingerprint_status == FingerprintStatus.DEGRADED.value
    assert fake_session.record.embedding_vector is None


@pytest.mark.asyncio
async def test_index_incident_fingerprint_uses_placeholder_when_summary_missing(monkeypatch):
    monkeypatch.setattr(
        "core.jobs.processor.settings",
        SimpleNamespace(
            RELATED_INCIDENTS_ENABLED=True,
            RELATED_INCIDENTS_DEFAULT_SCOPE="multi_tenant",
            RELATED_INCIDENTS_MIN_RELEVANCE=0.6,
        ),
    )
    job_service = StubJobService()
    processor = JobProcessor(cast(JobService, job_service))
    fake_session = _FakeFingerprintSession()
    processor._session_factory = lambda: _FakeSessionContext(fake_session)  # type: ignore[assignment]

    called = {"value": False}

    async def _unexpected():  # pragma: no cover - should not run in this scenario
        called["value"] = True
        raise AssertionError("Embedding service should not be invoked when summary missing")

    monkeypatch.setattr(processor, "_ensure_embedding_service", _unexpected)

    tenant_id = uuid.uuid4()
    job: Any = SimpleNamespace(id=uuid.uuid4(), input_manifest={"tenant_id": str(tenant_id)}, source={})

    dto = await processor._index_incident_fingerprint(  # type: ignore[arg-type]
        job,
        [],
        {},
    )

    assert dto is not None
    assert dto.fingerprint_status is FingerprintStatus.MISSING
    assert dto.embedding_present is False
    assert dto.summary_text.startswith("Automated summary unavailable")
    assert fake_session.record is not None
    assert fake_session.record.fingerprint_status == FingerprintStatus.MISSING.value
    assert called["value"] is False


@pytest.mark.asyncio
async def test_generate_embeddings_batches_requests(monkeypatch):
    settings_stub = _stub_ingestion_settings(EMBED_BATCH_SIZE=2)
    monkeypatch.setattr("core.jobs.processor.settings", settings_stub)

    job_service = StubJobService()
    processor = JobProcessor(cast(JobService, job_service))

    class _EmbeddingService:
        def __init__(self):
            self.calls = []
            self.provider = SimpleNamespace(
                provider_name="stub-provider",
                model="stub-embedding",
            )

        async def embed_texts(self, batch):
            self.calls.append(list(batch))
            return [[float(len(item))] for item in batch]

    service = _EmbeddingService()

    async def _ensure_service():
        return service

    monkeypatch.setattr(processor, "_ensure_embedding_service", _ensure_service)

    vectors = await processor._generate_embeddings(["one", "two", "three"])

    assert service.calls == [["one", "two"], ["three"]]
    assert [value[0] for value in vectors] == [3.0, 3.0, 5.0]


@pytest.mark.asyncio
async def test_generate_embeddings_records_cache_stage(monkeypatch):
    settings_stub = _stub_ingestion_settings(EMBED_BATCH_SIZE=2)

    class _Flags:
        @staticmethod
        def is_enabled(key: str) -> bool:
            return key == "embedding_cache_enabled"

    settings_stub.feature_flags = _Flags()  # type: ignore[attr-defined]
    monkeypatch.setattr("core.jobs.processor.settings", settings_stub)

    job_service = StubJobService()
    processor = JobProcessor(cast(JobService, job_service))

    class _StubEmbeddingService:
        def __init__(self):
            self.calls = []
            self.provider = SimpleNamespace(provider_name="stub-provider", model="stub-model")

        async def embed_texts(self, batch):
            self.calls.append(list(batch))
            return [[float(len(item))] for item in batch]

    embedding_service = _StubEmbeddingService()

    async def _ensure_service():
        return embedding_service

    monkeypatch.setattr(processor, "_ensure_embedding_service", _ensure_service)

    class _StubEmbeddingCacheService:
        def __init__(self, session, metrics):
            self.session = session
            self.metrics = metrics
            self.lookup_hashes: List[str] = []
            self.store_payloads: List[str] = []

        async def lookup(self, tenant_id, content_hash, model):
            self.lookup_hashes.append(content_hash)
            if len(self.lookup_hashes) == 1:
                return SimpleNamespace(embedding=[42.0])
            return None

        async def store(
            self,
            tenant_id,
            content_hash,
            model,
            *,
            embedding_vector_id,
            scrub_metadata,
            embedding,
            expires_at=None,
        ):
            self.store_payloads.append(content_hash)
            return SimpleNamespace(id=uuid.uuid4())

    monkeypatch.setattr("core.jobs.processor.EmbeddingCacheService", _StubEmbeddingCacheService)

    cache_session = _StubCacheSession()
    processor._session_factory = lambda: _FakeSessionContext(cache_session)  # type: ignore[assignment]

    recorded_events: List[dict[str, Any]] = []

    async def _record_stage_event_stub(self, session_arg, job_id_arg, context_arg, **kwargs):
        recorded_events.append(
            {
                "session": session_arg,
                "job_id": job_id_arg,
                "context": context_arg,
                **kwargs,
            }
        )

    monkeypatch.setattr(JobProcessor, "_record_stage_event", _record_stage_event_stub)

    tenant_id = uuid.uuid4()
    context = cast(
        Any,
        SimpleNamespace(
            tenant_label=str(tenant_id),
            tenant_uuid=tenant_id,
            job_uuid=uuid.uuid4(),
            file_uuid=uuid.uuid4(),
            platform="worker",
            file_type="log",
            feature_flags=["embedding_cache_enabled"],
            telemetry_enabled=True,
            metrics_enabled=True,
            size_bytes=128,
        ),
    )

    session_stub = cast(Any, SimpleNamespace())

    vectors = await processor._generate_embeddings(
        ["cached-chunk", "fresh-chunk"],
        context=context,
        pii_scrubbed=True,
        session=session_stub,
        job_id="job-telemetry",
        cache_details={"file_id": "file-123"},
    )

    assert recorded_events, "expected cache stage telemetry to be recorded"
    event = recorded_events[0]
    assert event["job_id"] == "job-telemetry"
    assert event["stage"] is PipelineStage.CACHE
    metadata = event["metadata"]
    assert metadata["lookup_count"] == 2
    assert metadata["hit_count"] == 1
    assert metadata["miss_count"] == 1
    assert metadata["store_count"] == 1
    assert metadata["store_committed"] is True
    assert vectors[0] == [42.0]
    assert vectors[1] == [float(len("fresh-chunk"))]


@pytest.mark.asyncio
async def test_process_log_analysis_reports_suspected_error_logs():
    descriptors = [
        FileDescriptor(
            id="file-2",
            path="/tmp/file-2.log",
            name="errors.log",
            checksum="checksum",
            content_type="text/plain",
            metadata=None,
            size_bytes=21,
        )
    ]
    summaries = {"file-2": _summary("file-2", "errors.log", errors=1, warnings=0)}
    job_service = StubJobService()
    processor = StubProcessor(descriptors, summaries, job_service)

    job: Any = SimpleNamespace(
        id="job-2",
        job_type="log_analysis",
        provider="stub",
        model="stub",
        input_manifest={},
    )

    result = await processor.process_log_analysis(job)  # type: ignore[arg-type]

    assert result["analysis_type"] == "log_analysis"
    assert result["suspected_error_logs"] == ["errors.log"]
    assert processor.fingerprint_calls == 0
    assert processor.detection_calls == 1
    assert any(
        event_type == "analysis-progress" and data.get("step") == "report" and data.get("status") in {"completed", "success"}
        for _, event_type, data in job_service.events
    )
