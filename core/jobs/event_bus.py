"""
Job event bus abstraction used to fan-out job lifecycle updates.

The bus publishes events to Redis when configured, falling back to an
in-process queue for development and tests. Consumers can subscribe to a job's
channel and receive events without polling the database.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import AsyncIterator, DefaultDict, Dict, List, Optional

try:
    import redis.asyncio as redis  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - redis is optional at runtime
    redis = None  # type: ignore[assignment]

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


class JobEventBus:
    """Publish/subscribe helper for job lifecycle events."""

    def __init__(self) -> None:
        self._redis_client: Optional["redis.Redis"] = None
        self._redis_enabled = (
            settings.redis.REDIS_ENABLED
            and bool(settings.redis.REDIS_URL)
            and redis is not None
        )
        self._local_subscriptions: DefaultDict[str, List[asyncio.Queue[str]]] = (
            defaultdict(list)
        )
        self._lock = asyncio.Lock()

    async def _ensure_redis(self) -> Optional["redis.Redis"]:
        if not self._redis_enabled:
            return None

        if self._redis_client and not self._redis_client.closed:
            return self._redis_client

        try:
            self._redis_client = redis.from_url(  # type: ignore[call-arg]
                settings.redis.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._redis_client.ping()
            return self._redis_client
        except Exception as exc:  # pragma: no cover - network failure
            logger.warning("Redis unavailable for job event bus: %s", exc)
            self._redis_client = None
            self._redis_enabled = False
            return None

    @staticmethod
    def _channel(job_id: str) -> str:
        return f"job-events:{job_id}"

    async def publish(self, job_id: str, payload: Dict) -> None:
        """Publish an event for a job."""
        serialised = json.dumps(payload, default=str)

        redis_client = await self._ensure_redis()
        if redis_client is not None:
            try:
                await redis_client.publish(self._channel(job_id), serialised)
            except Exception as exc:  # pragma: no cover - network failure
                logger.warning("Failed to publish job event to Redis: %s", exc)

        await self._publish_local(job_id, serialised)

    async def subscribe(self, job_id: str) -> AsyncIterator[Dict]:
        """Subscribe to events for a specific job."""
        redis_client = await self._ensure_redis()
        if redis_client is not None:
            pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
            await pubsub.subscribe(self._channel(job_id))
            try:
                async for message in pubsub.listen():
                    if message.get("type") != "message":
                        continue
                    data = message.get("data")
                    if not data:
                        continue
                    yield json.loads(data)
            finally:
                try:
                    await pubsub.unsubscribe(self._channel(job_id))
                finally:
                    await pubsub.close()
            return

        queue: asyncio.Queue[str] = asyncio.Queue()
        await self._register_local(job_id, queue)
        try:
            while True:
                data = await queue.get()
                yield json.loads(data)
        finally:
            await self._unregister_local(job_id, queue)

    async def close(self) -> None:
        """Close the underlying Redis connection."""
        if self._redis_client is not None and not self._redis_client.closed:
            await self._redis_client.close()
        self._redis_client = None

    async def _publish_local(self, job_id: str, payload: str) -> None:
        async with self._lock:
            queues = list(self._local_subscriptions.get(job_id, []))

        if not queues:
            return

        for queue in queues:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:  # pragma: no cover - defensive
                logger.debug("Local job event queue full for job %s", job_id)

    async def _register_local(
        self, job_id: str, queue: asyncio.Queue[str]
    ) -> None:
        async with self._lock:
            self._local_subscriptions[job_id].append(queue)

    async def _unregister_local(
        self, job_id: str, queue: asyncio.Queue[str]
    ) -> None:
        async with self._lock:
            subscribers = self._local_subscriptions.get(job_id)
            if not subscribers:
                return

            if queue in subscribers:
                subscribers.remove(queue)

            if not subscribers:
                self._local_subscriptions.pop(job_id, None)


# Global event bus instance
job_event_bus = JobEventBus()

__all__ = ["JobEventBus", "job_event_bus"]
