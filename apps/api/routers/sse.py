"""
Server Sent Event helpers for streaming job updates.
"""

from __future__ import annotations

import contextlib
import asyncio
import json
import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Optional, Tuple

from fastapi import APIRouter, HTTPException, status
from starlette.responses import EventSourceResponse

from core.jobs.service import JobService
from core.jobs.event_bus import job_event_bus

logger = logging.getLogger(__name__)

router = APIRouter()
job_service = JobService()

TERMINAL_STATES = {"completed", "failed", "cancelled"}


async def _event_stream(job_id: str) -> AsyncGenerator[Dict[str, str], None]:
    """Yield SSE payloads backed by the in-process/Redis event bus."""

    queue: asyncio.Queue[Tuple[str, Dict[str, Any]]] = asyncio.Queue()
    stop_event = asyncio.Event()

    async def _forward_events() -> None:
        try:
            async for payload in job_event_bus.subscribe(job_id):
                await queue.put(("event", payload))
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - transport issues
            logger.warning("SSE subscription lost for job %s: %s", job_id, exc)
        finally:
            await queue.put(("closed", {}))
            stop_event.set()

    async def _emit_heartbeats() -> None:
        while not stop_event.is_set():
            await asyncio.sleep(15)
            job = await job_service.get_job(job_id)
            data = {
                "job_id": job_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "status": getattr(job, "status", None),
            }
            await queue.put(("heartbeat", data))

            if job and job.status in TERMINAL_STATES:
                await queue.put(
                    (
                        "event",
                        {
                            "event_type": "complete",
                            "job_id": job_id,
                            "status": job.status,
                        },
                    )
                )
                stop_event.set()
                await queue.put(("closed", {}))
                break

    consumer_task = asyncio.create_task(_forward_events())
    heartbeat_task = asyncio.create_task(_emit_heartbeats())

    try:
        historical = await job_service.get_job_events(job_id, limit=50)
        for event in reversed(historical):
            payload = event.to_dict()
            yield {
                "event": payload.get("event_type", "message"),
                "data": json.dumps(payload),
            }

        while True:
            kind, payload = await queue.get()

            if kind == "event":
                event_type = payload.get("event_type", "message")
                yield {
                    "event": event_type,
                    "data": json.dumps(payload),
                }

                if event_type in TERMINAL_STATES or payload.get("status") in TERMINAL_STATES:
                    stop_event.set()

            elif kind == "heartbeat":
                yield {
                    "event": "heartbeat",
                    "data": json.dumps(payload),
                }

            elif kind == "closed":
                break
    finally:
        stop_event.set()
        consumer_task.cancel()
        heartbeat_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await consumer_task
        with contextlib.suppress(asyncio.CancelledError):
            await heartbeat_task


@router.get("/jobs/{job_id}")
async def stream_job(job_id: str) -> EventSourceResponse:
    """Stream lifecycle events for the specified job."""
    job = await job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return EventSourceResponse(_event_stream(job_id))


__all__ = ["router"]
