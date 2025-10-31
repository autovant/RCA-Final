"""Unit tests for embedding cache eviction coordination."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import cast

import pytest

from apps.worker.tasks import cache_eviction
from core.metrics.pipeline_metrics import PipelineMetricsCollector
from sqlalchemy.ext.asyncio import AsyncSession


class _FlagSet:
    def __init__(self, enabled_keys):
        self._enabled = set(enabled_keys)

    def is_enabled(self, key: str) -> bool:  # pragma: no cover - simple shim
        return key in self._enabled


class _ImmediateContext:
    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _StubSession:
    def __init__(self):
        self.begin_called = 0

    def begin(self):  # pragma: no cover - simple context factory
        session = self

        class _Txn:
            async def __aenter__(self):
                session.begin_called += 1
                return session

            async def __aexit__(self, exc_type, exc, tb):
                return False

        return _Txn()


@pytest.mark.asyncio
async def test_coordinator_schedules_once_when_threshold_met(monkeypatch):
    tenant_id = uuid.uuid4()
    scheduled = asyncio.Event()

    session_factory = cast(
        cache_eviction.SessionFactory,
        lambda: _ImmediateContext(SimpleNamespace()),
    )
    coordinator = cache_eviction.EmbeddingCacheEvictionCoordinator(
        session_factory=session_factory,
        metrics=PipelineMetricsCollector(),
        task_factory=asyncio.create_task,
        hit_rate_threshold=0.3,
        min_interval_seconds=0,
    )

    monkeypatch.setattr(
        cache_eviction,
        "settings",
        SimpleNamespace(
            feature_flags=_FlagSet(
                {"embedding_cache_enabled", "embedding_cache_eviction_enabled"}
            )
        ),
    )

    async def _fake_eviction(session_factory, metrics_obj, tid, **_kwargs):
        assert tid == tenant_id
        scheduled.set()

    monkeypatch.setattr(cache_eviction, "run_embedding_cache_eviction", _fake_eviction)
    await coordinator.maybe_schedule(tenant_id, hit_rate=0.5, job_id="job-1")
    await asyncio.wait_for(scheduled.wait(), timeout=1)
    await asyncio.sleep(0)

    # second call should be skipped because min interval is zero but task already inflight
    await coordinator.maybe_schedule(tenant_id, hit_rate=0.9, job_id="job-2")
    await asyncio.sleep(0)
    assert tenant_id not in coordinator._inflight


@pytest.mark.asyncio
async def test_coordinator_skips_below_threshold(monkeypatch):
    tenant_id = uuid.uuid4()
    session_factory = cast(
        cache_eviction.SessionFactory,
        lambda: _ImmediateContext(SimpleNamespace()),
    )
    coordinator = cache_eviction.EmbeddingCacheEvictionCoordinator(
        session_factory=session_factory,
        metrics=PipelineMetricsCollector(),
        task_factory=asyncio.create_task,
        hit_rate_threshold=0.8,
        min_interval_seconds=0,
    )

    monkeypatch.setattr(coordinator, "_run", pytest.fail)
    monkeypatch.setattr(
        cache_eviction,
        "settings",
        SimpleNamespace(
            feature_flags=_FlagSet(
                {"embedding_cache_enabled", "embedding_cache_eviction_enabled"}
            )
        ),
    )

    await coordinator.maybe_schedule(tenant_id, hit_rate=0.4)
    await asyncio.sleep(0)
    assert tenant_id not in coordinator._inflight


@pytest.mark.asyncio
async def test_perform_eviction_records_metrics(monkeypatch):
    tenant_id = uuid.uuid4()
    session = _StubSession()
    released = False

    async def _acquire(_session, _tenant):  # pragma: no cover - simple stub
        return True

    async def _release(_session, _tenant):  # pragma: no cover - simple stub
        nonlocal released
        released = True

    class _FakeService:
        def __init__(self, session_obj, *, metrics=None):
            self._session = session_obj
            self._invocations = 0

        async def select_stale_entries(self, tenant, *, older_than, limit):
            assert tenant == tenant_id
            self._invocations += 1
            if self._invocations == 1:
                return [(uuid.uuid4(), "model-one"), (uuid.uuid4(), "model-two")]
            return []

        async def delete_entries(self, entry_ids):
            assert len(entry_ids) == 2
            return ["model-one", "model-two"]

    metrics = PipelineMetricsCollector()
    calls = []

    def _capture(**kwargs):
        calls.append(
            (kwargs["tenant_id"], kwargs["model"], kwargs["count"], kwargs["policy"])
        )

    monkeypatch.setattr(metrics, "record_cache_eviction", _capture)  # type: ignore[attr-defined]

    monkeypatch.setattr(cache_eviction, "_acquire_tenant_lock", _acquire)
    monkeypatch.setattr(cache_eviction, "_release_tenant_lock", _release)
    monkeypatch.setattr(cache_eviction, "EmbeddingCacheService", _FakeService)

    result = await cache_eviction._perform_eviction(
        cast(AsyncSession, session),
        metrics,
        tenant_id,
        older_than=datetime.now(timezone.utc),
        batch_limit=10,
        policy_label="stale_zero_hit",
    )

    assert result["lock_acquired"] is True
    assert result["evicted"] == 2
    assert released is True
    assert calls == [
        (str(tenant_id), "model-one", 1, "stale_zero_hit"),
        (str(tenant_id), "model-two", 1, "stale_zero_hit"),
    ]


@pytest.mark.asyncio
async def test_perform_eviction_skips_when_lock_unavailable(monkeypatch):
    tenant_id = uuid.uuid4()
    session = _StubSession()

    async def _deny(_session, _tenant):
        return False

    async def _release(_session, _tenant):  # pragma: no cover - not expected
        pytest.fail("release should not be called when lock not acquired")

    monkeypatch.setattr(cache_eviction, "_acquire_tenant_lock", _deny)
    monkeypatch.setattr(cache_eviction, "_release_tenant_lock", _release)
    monkeypatch.setattr(cache_eviction, "EmbeddingCacheService", lambda *_args, **_kwargs: None)

    result = await cache_eviction._perform_eviction(
        cast(AsyncSession, session),
        PipelineMetricsCollector(),
        tenant_id,
        older_than=datetime.now(timezone.utc),
        batch_limit=5,
        policy_label="stale_zero_hit",
    )

    assert result == {"lock_acquired": False, "evicted": 0, "per_model": {}}
