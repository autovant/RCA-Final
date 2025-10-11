"""
Watcher event bus used to fan-out filesystem watcher activity.

The implementation mirrors the job event bus, supporting an optional Redis
backend while providing an in-process fallback for development and tests.
"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator, Dict, List, Optional

try:
    import redis.asyncio as redis  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - Redis optional
    redis = None  # type: ignore[assignment]

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


class WatcherEventBus:
    """Lightweight publish/subscribe helper for watcher events."""

    _CHANNEL = "watcher-events"

    def __init__(self) -> None:
        self._redis_client: Optional["redis.Redis"] = None
        self._redis_enabled = (
            settings.redis.REDIS_ENABLED
            and bool(settings.redis.REDIS_URL)
            and redis is not None
        )
        self._local_subscribers: List[asyncio.Queue[str]] = []
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
            logger.warning("Redis unavailable for watcher event bus: %s", exc)
            self._redis_enabled = False
            self._redis_client = None
            return None

    async def publish(self, payload: Dict[str, object]) -> None:
        """Publish a watcher event payload."""
        serialised = json.dumps(payload, default=str)

        redis_client = await self._ensure_redis()
        if redis_client is not None:
            try:
                await redis_client.publish(self._CHANNEL, serialised)
            except Exception as exc:  # pragma: no cover - network failure
                logger.warning("Failed to publish watcher event to Redis: %s", exc)

        async with self._lock:
            subscribers = list(self._local_subscribers)

        for queue in subscribers:
            try:
                queue.put_nowait(serialised)
            except asyncio.QueueFull:  # pragma: no cover - defensive
                logger.debug("Local watcher event queue full, dropping payload")

    async def subscribe(self) -> AsyncIterator[Dict]:
        """Subscribe to watcher events."""
        redis_client = await self._ensure_redis()
        if redis_client is not None:
            pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
            await pubsub.subscribe(self._CHANNEL)
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
                    await pubsub.unsubscribe(self._CHANNEL)
                finally:
                    await pubsub.close()
            return

        queue: asyncio.Queue[str] = asyncio.Queue()
        async with self._lock:
            self._local_subscribers.append(queue)

        try:
            while True:
                data = await queue.get()
                yield json.loads(data)
        finally:
            async with self._lock:
                if queue in self._local_subscribers:
                    self._local_subscribers.remove(queue)

    async def close(self) -> None:
        """Dispose of any Redis connections."""
        if self._redis_client is not None and not self._redis_client.closed:
            await self._redis_client.close()
        self._redis_client = None


watcher_event_bus = WatcherEventBus()

__all__ = ["WatcherEventBus", "watcher_event_bus"]
