"""
Watcher configuration and event streaming endpoints.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from starlette.responses import EventSourceResponse

from core.watchers import WatcherService, watcher_event_bus

router = APIRouter()
watcher_service = WatcherService()



class WatcherConfigModel(BaseModel):
    """Serialised watcher configuration."""

    id: str
    enabled: bool
    roots: List[str] = Field(default_factory=list)
    include_globs: List[str] = Field(default_factory=list)
    exclude_globs: List[str] = Field(default_factory=list)
    max_file_size_mb: Optional[int] = None
    allowed_mime_types: List[str] = Field(default_factory=list)
    batch_window_seconds: Optional[int] = None
    auto_create_jobs: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class WatcherConfigUpdate(BaseModel):
    """Partial update model for watcher configuration."""

    enabled: Optional[bool] = None
    roots: Optional[List[str]] = None
    include_globs: Optional[List[str]] = None
    exclude_globs: Optional[List[str]] = None
    max_file_size_mb: Optional[int] = Field(default=None, ge=1)
    allowed_mime_types: Optional[List[str]] = None
    batch_window_seconds: Optional[int] = Field(default=None, ge=1)
    auto_create_jobs: Optional[bool] = None


def _to_config_model(config) -> WatcherConfigModel:
    return WatcherConfigModel(
        id=str(config.id),
        enabled=config.enabled,
        roots=list(config.roots or []),
        include_globs=list(config.include_globs or []),
        exclude_globs=list(config.exclude_globs or []),
        max_file_size_mb=config.max_file_size_mb,
        allowed_mime_types=list(config.allowed_mime_types or []),
        batch_window_seconds=config.batch_window_seconds,
        auto_create_jobs=config.auto_create_jobs,
        created_at=config.created_at.isoformat() if config.created_at else None,
        updated_at=config.updated_at.isoformat() if config.updated_at else None,
    )


@router.get("/config", response_model=WatcherConfigModel)
async def get_config() -> WatcherConfigModel:
    """Return the watcher configuration."""
    config = await watcher_service.get_config()
    return _to_config_model(config)


@router.put("/config", response_model=WatcherConfigModel)
async def update_config(payload: WatcherConfigUpdate) -> WatcherConfigModel:
    """Update watcher configuration."""
    if payload is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No payload supplied")
    config = await watcher_service.update_config(payload.model_dump(exclude_none=True))
    return _to_config_model(config)


@router.get("/status")
async def watcher_status() -> Dict[str, Any]:
    """Return watcher subsystem status metrics."""
    return await watcher_service.get_status()


async def _watcher_event_stream(history: int):
    queue: asyncio.Queue[tuple[str, Dict[str, Any]]] = asyncio.Queue()
    stop_event = asyncio.Event()

    async def _forward_events() -> None:
        try:
            async for payload in watcher_event_bus.subscribe():
                await queue.put(("event", payload))
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            await queue.put(
                (
                    "event",
                    {
                        "event_type": "error",
                        "error": str(exc),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
            )
        finally:
            await queue.put(("closed", {}))
            stop_event.set()

    async def _emit_heartbeats() -> None:
        while not stop_event.is_set():
            await asyncio.sleep(15)
            heartbeat = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await queue.put(("heartbeat", heartbeat))


    forward_task = asyncio.create_task(_forward_events())
    heartbeat_task = asyncio.create_task(_emit_heartbeats())

    try:
        if history:
            events = await watcher_service.list_recent_events(history)
            for event in events:
                payload = event.to_dict()
                yield {
                    "event": payload.get("event_type", "history"),
                    "data": json.dumps(payload),
                }

        while True:
            kind, payload = await queue.get()
            if kind == "event":
                yield {
                    "event": payload.get("event_type", "message"),
                    "data": json.dumps(payload),
                }
            elif kind == "heartbeat":
                yield {
                    "event": "heartbeat",
                    "data": json.dumps(payload),
                }
            elif kind == "closed":
                break
    finally:
        stop_event.set()
        forward_task.cancel()
        heartbeat_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await forward_task
        with contextlib.suppress(asyncio.CancelledError):
            await heartbeat_task


@router.get("/events")
async def stream_events(
    history: int = Query(0, ge=0, le=200, description="Number of historical events to replay"),
) -> EventSourceResponse:
    """Stream watcher events via server-sent events."""
    return EventSourceResponse(_watcher_event_stream(history))


__all__ = ["router"]
