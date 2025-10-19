"""
Server Sent Event helpers for streaming job updates.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict

from fastapi import APIRouter, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from core.jobs.service import JobService

logger = logging.getLogger(__name__)

router = APIRouter()
job_service = JobService()


TERMINAL_STATES = {"completed", "failed", "cancelled"}
JOB_EVENT_STREAM_NAME = "job-event"


async def _event_stream(job_id: str) -> AsyncGenerator[Dict[str, str], None]:
    """Yield SSE payloads by polling the database for new events.
    
    This simple polling approach works reliably across processes without Redis.
    """
    try:
        # Track last seen timestamp to identify new events
        last_seen_at = None
        
        # Send historical events first
        historical = await job_service.get_job_events(job_id, limit=100)
        for event in reversed(historical):
            payload = event.to_dict()
            yield {
                "event": JOB_EVENT_STREAM_NAME,
                "data": json.dumps(payload),
            }
            # Track the latest timestamp we've sent
            created_at = getattr(event, 'created_at', None)
            if created_at is not None:
                if last_seen_at is None or created_at > last_seen_at:
                    last_seen_at = created_at

        # Poll for new events until job reaches terminal state
        poll_interval = 1.0  # Poll every 1 second for new events
        heartbeat_counter = 0
        
        while True:
            await asyncio.sleep(poll_interval)
            heartbeat_counter += 1
            
            # Check job status
            job = await job_service.get_job(job_id)
            
            # Send heartbeat every 15 seconds
            if heartbeat_counter >= 15:
                heartbeat_counter = 0
                data = {
                    "job_id": job_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": getattr(job, "status", None),
                }
                yield {
                    "event": "heartbeat",
                    "data": json.dumps(data),
                }
            
            # Fetch new events since last check
            all_events = await job_service.get_job_events(job_id, limit=100)
            logger.info(f"[SSE {job_id}] Fetched {len(all_events)} total events, last_seen_at={last_seen_at}")
            new_events = []
            for e in all_events:
                created_at = getattr(e, 'created_at', None)
                if created_at is not None:
                    is_new = last_seen_at is None or created_at > last_seen_at
                    logger.debug(f"[SSE {job_id}] Event {e.event_type} @ {created_at} - is_new={is_new}")
                    if is_new:
                        new_events.append(e)
            
            # Send new events (oldest first)
            if new_events:
                logger.info(f"[SSE {job_id}] Sending {len(new_events)} new events")
            for event in reversed(new_events):
                payload = event.to_dict()
                yield {
                    "event": JOB_EVENT_STREAM_NAME,
                    "data": json.dumps(payload),
                }
                created_at = getattr(event, 'created_at', None)
                if created_at is not None:
                    if last_seen_at is None or created_at > last_seen_at:
                        last_seen_at = created_at
            
            # Stop polling if job is in terminal state
            if job and job.status in TERMINAL_STATES:
                # Send final completion event
                yield {
                    "event": JOB_EVENT_STREAM_NAME,
                    "data": json.dumps({
                        "event_type": "complete",
                        "job_id": job_id,
                        "status": job.status,
                    }),
                }
                break
    except Exception as exc:
        logger.error(f"Error in SSE stream for job {job_id}: {exc}", exc_info=True)
        # Yield error event before closing
        yield {
            "event": "error",
            "data": json.dumps({"error": str(exc)}),
        }


@router.get("/jobs/{job_id}")
async def stream_job(job_id: str) -> EventSourceResponse:
    """Stream lifecycle events for the specified job."""
    job = await job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return EventSourceResponse(_event_stream(job_id))


__all__ = ["router"]
