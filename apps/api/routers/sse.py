"""
Server Sent Event helpers for streaming job updates.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator, Dict, Optional

from fastapi import APIRouter, HTTPException, status
from starlette.responses import EventSourceResponse

from core.jobs.service import JobService

router = APIRouter()
job_service = JobService()

TERMINAL_STATES = {"completed", "failed", "cancelled"}


async def _event_stream(job_id: str) -> AsyncGenerator[Dict[str, str], None]:
    """
    Internal generator yielding SSE-compatible payloads.

    Emits job events as they are persisted and falls back to periodic heartbeats
    so the connection stays alive while waiting for new data.
    """
    last_seen: Optional[datetime] = None

    while True:
        events = await job_service.get_job_events_since(job_id, last_seen)
        if events:
            for event in events:
                last_seen = event.created_at
                payload = event.to_dict()
                yield {
                    "event": event.event_type,
                    "data": json.dumps(payload),
                }

        else:
            job = await job_service.get_job(job_id)
            if job and job.status in TERMINAL_STATES:
                yield {
                    "event": "complete",
                    "data": json.dumps({"job_id": job_id, "status": job.status}),
                }
                break

            yield {
                "event": "heartbeat",
                "data": json.dumps({"job_id": job_id, "timestamp": datetime.utcnow().isoformat() + "Z"}),
            }

        await asyncio.sleep(1.0)


@router.get("/jobs/{job_id}")
async def stream_job(job_id: str) -> EventSourceResponse:
    """Stream lifecycle events for the specified job."""
    job = await job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return EventSourceResponse(_event_stream(job_id))


__all__ = ["router"]
