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
from sse_starlette.sse import EventSourceResponse

from core.watchers import (
    WatcherService,
    watcher_event_bus,
    watcher_processor_registry,
)

router = APIRouter()
watcher_service = WatcherService(processor_registry=watcher_processor_registry)

WATCHER_PRESETS: List[Dict[str, Any]] = [
    {
        "id": "standard-logs",
        "name": "Standard Logs",
        "description": "Common log formats with temporary files excluded.",
        "config": {
            "include_globs": ["**/*.log", "**/*.txt", "**/*.json"],
            "exclude_globs": ["**/archive/**", "**/*.tmp", "**/~*"],
            "max_file_size_mb": 250,
            "batch_window_seconds": 10,
            "allowed_mime_types": ["text/plain", "application/json"],
        },
    },
    {
        "id": "support-drops",
        "name": "Support Drops",
        "description": "Tailored for helpdesk uploads and CSV attachments.",
        "config": {
            "include_globs": ["**/*.csv", "**/*.xlsx", "**/*.json"],
            "exclude_globs": ["**/Processed/**", "**/*.bak"],
            "max_file_size_mb": 150,
            "batch_window_seconds": 5,
            "allowed_mime_types": [
                "text/csv",
                "application/json",
                "application/vnd.ms-excel",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ],
        },
    },
    {
        "id": "raw-dumps",
        "name": "Raw Dumps",
        "description": "Large forensic dumps with minimal exclusions.",
        "config": {
            "include_globs": ["**/*.log", "**/*.json", "**/*.zip"],
            "exclude_globs": ["**/*.tmp"],
            "max_file_size_mb": 1024,
            "batch_window_seconds": 30,
            "allowed_mime_types": [
                "text/plain",
                "application/json",
                "application/zip",
            ],
        },
    },
]



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


class WatcherPresetModel(BaseModel):
    """Pre-defined configuration preset."""

    id: str
    name: str
    description: str
    config: WatcherConfigUpdate


class PatternTestRequest(BaseModel):
    """Payload for pattern tester."""

    path: str = Field(..., description="Sample file path to evaluate")
    include_globs: Optional[List[str]] = Field(default=None, description="Include patterns to test")
    exclude_globs: Optional[List[str]] = Field(default=None, description="Exclude patterns to test")


class PatternTestResult(BaseModel):
    """Result of pattern tester evaluation."""

    path: str
    status: str
    reason: str
    matched_includes: List[str]
    matched_excludes: List[str]
    include_globs: List[str]
    exclude_globs: List[str]


class WatcherStatsTimelinePoint(BaseModel):
    bucket: str
    count: int


class WatcherStatsEntry(BaseModel):
    event_type: str
    total: int
    timeline: List[WatcherStatsTimelinePoint] = Field(default_factory=list)


class WatcherStatsResponse(BaseModel):
    lookback_hours: int
    total_events: int
    event_types: List[WatcherStatsEntry] = Field(default_factory=list)


class WatcherProcessorOption(BaseModel):
    id: str
    name: str
    description: str
    default_options: Dict[str, Any] = Field(default_factory=dict)


class WatcherConfigResponse(WatcherConfigModel):
    available_processors: List[WatcherProcessorOption] = Field(default_factory=list)


def _to_config_response(
    config, available_processors: List[Dict[str, Any]]
) -> WatcherConfigResponse:
    return WatcherConfigResponse(
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
        available_processors=[
            WatcherProcessorOption(**processor) for processor in available_processors
        ],
    )


@router.get("/config", response_model=WatcherConfigResponse)
async def get_config() -> WatcherConfigResponse:
    """Return the watcher configuration."""
    payload = await watcher_service.get_config()
    return _to_config_response(payload["config"], payload["available_processors"])


@router.put("/config", response_model=WatcherConfigResponse)
async def update_config(payload: WatcherConfigUpdate) -> WatcherConfigResponse:
    """Update watcher configuration."""
    if payload is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No payload supplied")
    config = await watcher_service.update_config(payload.model_dump(exclude_none=True))
    return _to_config_response(config, watcher_service.available_processors())


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
                envelope = {"event_type": payload.get("event_type", "history"), **payload}
                yield {
                    "event": "watcher-event",
                    "data": json.dumps(envelope),
                }

        while True:
            kind, payload = await queue.get()
            if kind == "event":
                event_type = payload.get("event_type", "message")
                envelope = {"event_type": event_type, **payload}
                yield {
                    "event": "watcher-event",
                    "data": json.dumps(envelope),
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


@router.get("/presets", response_model=List[WatcherPresetModel])
async def list_presets() -> List[WatcherPresetModel]:
    """Return available watcher configuration presets."""
    models: List[WatcherPresetModel] = []
    for preset in WATCHER_PRESETS:
        models.append(
            WatcherPresetModel(
                id=preset["id"],
                name=preset["name"],
                description=preset["description"],
                config=WatcherConfigUpdate(**preset["config"]),
            )
        )
    return models


@router.post("/pattern/test", response_model=PatternTestResult)
async def pattern_test(payload: PatternTestRequest) -> PatternTestResult:
    """Evaluate include/exclude patterns against a sample path."""

    result = await watcher_service.test_patterns(
        sample_path=payload.path,
        include_globs=payload.include_globs,
        exclude_globs=payload.exclude_globs,
    )
    return PatternTestResult(**result)


@router.get("/stats", response_model=WatcherStatsResponse)
async def watcher_stats(
    lookback_hours: int = Query(24, ge=1, le=168, description="Hours to include in the aggregation"),
) -> WatcherStatsResponse:
    """Return aggregated watcher activity statistics."""

    stats = await watcher_service.get_statistics(lookback_hours=lookback_hours)
    return WatcherStatsResponse(**stats)


__all__ = ["router"]
