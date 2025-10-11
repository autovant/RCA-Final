"""
Service layer for watcher configuration and event persistence.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.db.database import get_db_session
from core.db.models import WatcherConfig, WatcherEvent
from core.logging import get_logger
from core.watchers.event_bus import watcher_event_bus

logger = get_logger(__name__)


class WatcherService:
    """Manage watcher configuration and surface activity events."""

    def __init__(self) -> None:
        self._session_factory = get_db_session()
        self._event_bus = watcher_event_bus

    @staticmethod
    def _normalise_list(value: Optional[Any]) -> Optional[List[str]]:
        if value is None:
            return None
        if isinstance(value, (list, tuple, set)):
            return [str(item) for item in value]
        return [str(value)]

    async def _ensure_config(self, session: AsyncSession) -> WatcherConfig:
        result = await session.execute(select(WatcherConfig).limit(1))
        config = result.scalar_one_or_none()
        if config:
            return config

        default_roots = self._normalise_list(settings.files.WATCH_FOLDER)
        config = WatcherConfig(
            enabled=True,
            roots=default_roots,
            include_globs=["**/*.log", "**/*.txt", "**/*.json", "**/*.csv"],
            exclude_globs=["**/~*", "**/*.tmp"],
            max_file_size_mb=settings.files.MAX_FILE_SIZE_MB,
            allowed_mime_types=["text/plain", "application/json"],
            batch_window_seconds=5,
            auto_create_jobs=True,
        )
        session.add(config)
        await session.flush()
        await session.refresh(config)
        logger.info("Initial watcher configuration created")
        return config

    async def get_config(self) -> WatcherConfig:
        """Return the persisted watcher configuration (creating defaults if needed)."""
        async with self._session_factory() as session:
            async with session.begin():
                config = await self._ensure_config(session)
            await session.refresh(config)
            return config

    async def update_config(self, payload: Dict[str, Any]) -> WatcherConfig:
        """
        Update watcher configuration with supplied payload.

        Args:
            payload: Partial configuration fields to update.
        """
        async with self._session_factory() as session:
            async with session.begin():
                config = await self._ensure_config(session)

                for field in (
                    "enabled",
                    "max_file_size_mb",
                    "batch_window_seconds",
                    "auto_create_jobs",
                ):
                    if field in payload and payload[field] is not None:
                        setattr(config, field, payload[field])

                for field in ("roots", "include_globs", "exclude_globs", "allowed_mime_types"):
                    if field in payload and payload[field] is not None:
                        setattr(config, field, self._normalise_list(payload[field]))

                await session.flush()
                await session.refresh(config)

            await self._event_bus.publish(
                {"event_type": "config-updated", "config": config.to_dict()}
            )
            logger.info("Watcher configuration updated")
            return config

    async def record_event(
        self,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        job_id: Optional[str] = None,
        watcher_id: Optional[str] = None,
    ) -> WatcherEvent:
        """Persist a watcher event and broadcast it."""
        async with self._session_factory() as session:
            async with session.begin():
                config = await self._ensure_config(session)
                event = WatcherEvent(
                    watcher_id=watcher_id or (config.id if config else None),
                    job_id=job_id,
                    event_type=event_type,
                    payload=payload or {},
                )
                session.add(event)
                await session.flush()
                await session.refresh(event)

            await self._event_bus.publish(event.to_dict())
            return event

    async def list_recent_events(self, limit: int = 100) -> List[WatcherEvent]:
        """Return the most recent watcher events."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(WatcherEvent)
                .order_by(WatcherEvent.created_at.desc())
                .limit(limit)
            )
            events = list(result.scalars().all())
            return list(reversed(events))

    async def get_status(self) -> Dict[str, Any]:
        """Return watcher runtime status including recent activity."""
        async with self._session_factory() as session:
            async with session.begin():
                config = await self._ensure_config(session)
                count_result = await session.execute(select(func.count(WatcherEvent.id)))
                total_events = int(count_result.scalar_one())
                latest_result = await session.execute(
                    select(WatcherEvent)
                    .order_by(WatcherEvent.created_at.desc())
                    .limit(1)
                )
                latest = latest_result.scalars().first()

        status: Dict[str, Any] = {
            "enabled": config.enabled,
            "roots": list(config.roots or []),
            "auto_create_jobs": config.auto_create_jobs,
            "total_events": total_events,
        }
        if latest:
            status["last_event"] = latest.to_dict()
        return status
