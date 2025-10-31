"""
Server Sent Event helpers for streaming job updates.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, Dict, Optional, Set

from fastapi import APIRouter, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from core.jobs.service import JobService

logger = logging.getLogger(__name__)

router = APIRouter()
job_service = JobService()


TERMINAL_STATES = {"completed", "failed", "cancelled"}
JOB_EVENT_STREAM_NAME = "job-event"
SSE_RETRY_MS = 2_000
POLL_INTERVAL_SECONDS = 1.0
HEARTBEAT_INTERVAL_SECONDS = 15
STREAM_RESET_INTERVAL_SECONDS = 10 * 60
MAX_EVENT_HISTORY = 250


def _normalize_timestamp(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _send_event(payload_event: str, payload: Dict[str, object], *, retry: Optional[int] = None) -> Dict[str, str]:
    message: Dict[str, str] = {
        "event": payload_event,
        "data": json.dumps(payload),
    }
    if retry is not None:
        message["retry"] = str(retry)
    return message


async def _event_stream(job_id: str) -> AsyncGenerator[Dict[str, str], None]:
    """Yield SSE payloads by polling for job events."""
    start_time = datetime.now(timezone.utc)
    last_heartbeat_at = start_time
    last_seen_at: Optional[datetime] = None
    seen_event_ids: Set[str] = set()
    idle_polls = 0
    backoff_seconds = POLL_INTERVAL_SECONDS

    try:
        job_status = await job_service.get_job_status(job_id)
        if job_status is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

        yield _send_event(
            "connection-info",
            {
                "job_id": job_id,
                "status": job_status,
                "reset_after_seconds": STREAM_RESET_INTERVAL_SECONDS,
            },
            retry=SSE_RETRY_MS,
        )

        historical = await job_service.get_job_events(job_id, limit=MAX_EVENT_HISTORY)
        for event in reversed(historical):
            payload = event.to_dict()
            payload.setdefault("job_id", job_id)
            created_at = _normalize_timestamp(getattr(event, "created_at", None))
            event_id = payload.get("id")
            if event_id:
                event_id = str(event_id)
                if event_id in seen_event_ids:
                    continue
                seen_event_ids.add(event_id)
            if created_at is not None and (last_seen_at is None or created_at > last_seen_at):
                last_seen_at = created_at
            yield _send_event(JOB_EVENT_STREAM_NAME, payload)

        while True:
            await asyncio.sleep(backoff_seconds)

            if (datetime.now(timezone.utc) - start_time) >= timedelta(seconds=STREAM_RESET_INTERVAL_SECONDS):
                yield _send_event(
                    "connection-reset",
                    {
                        "job_id": job_id,
                        "reason": "stream-duration",
                    },
                    retry=SSE_RETRY_MS,
                )
                break

            try:
                job_status = await job_service.get_job_status(job_id)
                if job_status is None:
                    yield _send_event(
                        "error",
                        {"job_id": job_id, "error": "Job not found"},
                        retry=SSE_RETRY_MS,
                    )
                    break

                events = await job_service.get_job_events(job_id, limit=MAX_EVENT_HISTORY)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Error fetching SSE data for job %s: %s", job_id, exc, exc_info=True)
                yield _send_event(
                    "error",
                    {"job_id": job_id, "error": "temporary-unavailable"},
                    retry=SSE_RETRY_MS,
                )
                backoff_seconds = min(backoff_seconds * 2, 5.0)
                continue

            backoff_seconds = POLL_INTERVAL_SECONDS

            new_events = []
            for event in events:
                payload = event.to_dict()
                payload.setdefault("job_id", job_id)
                created_at = _normalize_timestamp(getattr(event, "created_at", None))
                event_id = payload.get("id")
                if event_id:
                    event_id = str(event_id)
                    if event_id in seen_event_ids:
                        continue
                is_new = False
                if last_seen_at is None:
                    is_new = True
                elif created_at is not None and created_at > last_seen_at:
                    is_new = True
                elif created_at is not None and created_at == last_seen_at and event_id and event_id not in seen_event_ids:
                    is_new = True

                if is_new:
                    new_events.append((event_id, created_at, payload))

            if new_events:
                idle_polls = 0
                for event_id, created_at, payload in sorted(new_events, key=lambda item: item[1] or datetime.min.replace(tzinfo=timezone.utc)):
                    if event_id:
                        seen_event_ids.add(event_id)
                    if created_at is not None and (last_seen_at is None or created_at > last_seen_at):
                        last_seen_at = created_at
                    yield _send_event(JOB_EVENT_STREAM_NAME, payload)
            else:
                idle_polls += 1

            now = datetime.now(timezone.utc)
            if (now - last_heartbeat_at) >= timedelta(seconds=HEARTBEAT_INTERVAL_SECONDS):
                yield _send_event(
                    "heartbeat",
                    {
                        "job_id": job_id,
                        "timestamp": now.isoformat(),
                        "status": job_status,
                    },
                )
                last_heartbeat_at = now

            if job_status in TERMINAL_STATES:
                yield _send_event(
                    JOB_EVENT_STREAM_NAME,
                    {
                        "event_type": "complete",
                        "job_id": job_id,
                        "status": job_status,
                    },
                )
                break

            if idle_polls * backoff_seconds >= STREAM_RESET_INTERVAL_SECONDS:
                yield _send_event(
                    "connection-reset",
                    {
                        "job_id": job_id,
                        "reason": "idle-timeout",
                    },
                    retry=SSE_RETRY_MS,
                )
                break

    except asyncio.CancelledError:
        logger.debug("SSE stream cancelled for job %s", job_id)
        raise
    except Exception as exc:
        logger.error("Error in SSE stream for job %s: %s", job_id, exc, exc_info=True)
        yield {
            "event": "error",
            "data": json.dumps({"job_id": job_id, "error": str(exc)}),
            "retry": str(SSE_RETRY_MS),
        }


@router.get("/jobs/{job_id}")
async def stream_job(job_id: str) -> EventSourceResponse:
    """Stream lifecycle events for the specified job."""
    job = await job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return EventSourceResponse(
        _event_stream(job_id),
        ping=HEARTBEAT_INTERVAL_SECONDS,
        headers={"Cache-Control": "no-store"},
    )


__all__ = ["router"]
