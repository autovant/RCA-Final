"""Asynchronous embedding cache eviction task orchestration."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncContextManager, Callable, Coroutine, Dict, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.cache.embedding_cache_service import EmbeddingCacheService
from core.config import settings
from core.metrics.pipeline_metrics import PipelineMetricsCollector

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], AsyncContextManager[AsyncSession]]
TaskFactory = Callable[[Coroutine[Any, Any, Any]], asyncio.Task]


def _tenant_lock_key(tenant_id: uuid.UUID) -> int:
    """Derive a stable advisory lock key from the tenant identifier."""

    return tenant_id.int & 0x7FFF_FFFF_FFFF_FFFF


async def _acquire_tenant_lock(session: AsyncSession, tenant_id: uuid.UUID) -> bool:
    """Attempt to obtain a session-scoped advisory lock for the tenant."""

    lock_key = _tenant_lock_key(tenant_id)
    stmt = text("SELECT pg_try_advisory_lock(:lock_key)").execution_options(
        isolation_level="AUTOCOMMIT"
    )
    result = await session.execute(stmt, {"lock_key": lock_key})
    return bool(result.scalar())


async def _release_tenant_lock(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Release the advisory lock held for the tenant when present."""

    lock_key = _tenant_lock_key(tenant_id)
    stmt = text("SELECT pg_advisory_unlock(:lock_key)").execution_options(
        isolation_level="AUTOCOMMIT"
    )
    await session.execute(stmt, {"lock_key": lock_key})


async def _perform_eviction(
    session: AsyncSession,
    metrics: PipelineMetricsCollector,
    tenant_id: uuid.UUID,
    *,
    older_than: datetime,
    batch_limit: int,
    policy_label: str,
) -> Dict[str, Any]:
    """Execute eviction in a transaction, returning summary statistics."""

    if not await _acquire_tenant_lock(session, tenant_id):
        logger.info(
            "Embedding cache eviction already in progress for tenant %s", tenant_id
        )
        return {"lock_acquired": False, "evicted": 0, "per_model": {}}

    total_removed = 0
    per_model: Counter[str] = Counter()

    try:
        async with session.begin():
            service = EmbeddingCacheService(session, metrics=metrics)
            while True:
                entries = await service.select_stale_entries(
                    tenant_id,
                    older_than=older_than,
                    limit=batch_limit,
                )
                if not entries:
                    break

                entry_ids = [entry_id for entry_id, _model in entries]
                removed_models = await service.delete_entries(entry_ids)
                if not removed_models:
                    break

                total_removed += len(removed_models)
                per_model.update(removed_models)

                if len(entries) < batch_limit:
                    break

        if total_removed:
            for model, count in per_model.items():
                metrics.record_cache_eviction(
                    tenant_id=str(tenant_id),
                    model=model,
                    count=count,
                    policy=policy_label,
                )
            logger.info(
                "Embedding cache eviction removed %s entries for tenant %s", total_removed, tenant_id
            )
        else:
            logger.debug(
                "No embedding cache entries met eviction policy for tenant %s", tenant_id
            )

        return {
            "lock_acquired": True,
            "evicted": total_removed,
            "per_model": dict(per_model),
        }
    finally:
        await _release_tenant_lock(session, tenant_id)


async def run_embedding_cache_eviction(
    session_factory: SessionFactory,
    metrics: PipelineMetricsCollector,
    tenant_id: uuid.UUID,
    *,
    now: Optional[datetime] = None,
    cutoff_days: Optional[int] = None,
    batch_limit: Optional[int] = None,
    policy_label: str = "stale_zero_hit",
) -> Dict[str, Any]:
    """Public entry point used by worker tasks to prune stale cache entries."""

    effective_now = now or datetime.now(timezone.utc)
    days = cutoff_days or settings.EMBEDDING_CACHE_EVICTION_MAX_AGE_DAYS
    older_than = effective_now - timedelta(days=max(1, int(days)))
    batch = batch_limit or settings.EMBEDDING_CACHE_EVICTION_BATCH_SIZE
    batch = max(1, int(batch))

    async with session_factory() as session:
        return await _perform_eviction(
            session,
            metrics,
            tenant_id,
            older_than=older_than,
            batch_limit=batch,
            policy_label=policy_label,
        )


class EmbeddingCacheEvictionCoordinator:
    """Coordinates background eviction runs without blocking ingest work."""

    def __init__(
        self,
        session_factory: SessionFactory,
        metrics: PipelineMetricsCollector,
        *,
        task_factory: Optional[TaskFactory] = None,
        hit_rate_threshold: Optional[float] = None,
        min_interval_seconds: Optional[int] = None,
    ) -> None:
        self._session_factory = session_factory
        self._metrics = metrics
        self._task_factory = task_factory or asyncio.create_task
        self._hit_rate_threshold = (
            float(hit_rate_threshold)
            if hit_rate_threshold is not None
            else float(settings.EMBEDDING_CACHE_HIT_RATE_THRESHOLD)
        )
        interval_seconds = (
            min_interval_seconds
            if min_interval_seconds is not None
            else settings.EMBEDDING_CACHE_EVICTION_MIN_INTERVAL_SECONDS
        )
        self._min_interval = timedelta(seconds=max(1, int(interval_seconds)))
        self._lock = asyncio.Lock()
        self._next_allowed: Dict[uuid.UUID, datetime] = {}
        self._inflight: Dict[uuid.UUID, asyncio.Task] = {}

    async def maybe_schedule(
        self,
        tenant_id: Optional[uuid.UUID],
        *,
        hit_rate: float,
        job_id: Optional[str] = None,
    ) -> None:
        """Schedule eviction when thresholds and feature flags permit."""

        if tenant_id is None:
            return
        if hit_rate < self._hit_rate_threshold:
            logger.debug(
                "Skipping eviction scheduling for tenant %s; hit rate %.4f below %.2f",
                tenant_id,
                hit_rate,
                self._hit_rate_threshold,
            )
            return

        flags = settings.feature_flags
        if not (
            flags.is_enabled("embedding_cache_enabled")
            and flags.is_enabled("embedding_cache_eviction_enabled")
        ):
            return

        async with self._lock:
            now = datetime.now(timezone.utc)
            next_allowed = self._next_allowed.get(tenant_id)
            if next_allowed and now < next_allowed:
                return

            if tenant_id in self._inflight:
                return

            task = self._task_factory(self._run(tenant_id, job_id=job_id))
            self._inflight[tenant_id] = task
            self._next_allowed[tenant_id] = now + self._min_interval

    async def _run(self, tenant_id: uuid.UUID, job_id: Optional[str]) -> None:
        try:
            await run_embedding_cache_eviction(
                self._session_factory,
                self._metrics,
                tenant_id,
            )
        except Exception:
            logger.exception(
                "Embedding cache eviction task failed for tenant %s (job=%s)",
                tenant_id,
                job_id,
            )
        finally:
            async with self._lock:
                self._inflight.pop(tenant_id, None)
