"""Jobs API router."""

import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator, Callable, Optional, cast

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import EventSourceResponse

from core.db.database import get_db_session
from core.db.models import Job, JobEvent

router = APIRouter()


async def _stream_job_events(
    job_id: str,
    session_factory: Callable[[], AsyncSession],
) -> AsyncGenerator[str, None]:
    """Stream job events for the given job ID."""
    last_event_at: Optional[datetime] = None
    heartbeat_interval = 15
    last_heartbeat = datetime.utcnow()
    terminal_states = {"succeeded", "failed", "cancelled", "completed"}

    async with session_factory() as session:
        session = cast(AsyncSession, session)

        while True:
            query = select(JobEvent).where(JobEvent.job_id == job_id)
            if last_event_at is not None:
                query = query.where(JobEvent.created_at > last_event_at)
            query = query.order_by(JobEvent.created_at.asc())

            result = await session.execute(query)
            events = result.scalars().all()

            if events:
                for event in events:
                    last_event_at = event.created_at
                    payload = json.dumps(event.to_dict())
                    yield f"event: {event.event_type}\ndata: {payload}\n\n"

                last_heartbeat = datetime.utcnow()
            else:
                now = datetime.utcnow()
                if (now - last_heartbeat).total_seconds() >= heartbeat_interval:
                    heartbeat_payload = json.dumps({"timestamp": now.isoformat()})
                    yield f"event: heartbeat\ndata: {heartbeat_payload}\n\n"
                    last_heartbeat = now

            status_result = await session.execute(select(Job.status).where(Job.id == job_id))
            job_status = status_result.scalar_one_or_none()
            if job_status in terminal_states:
                break

            if events:
                await asyncio.sleep(0.1)
            else:
                await asyncio.sleep(1)


@router.get("/{job_id}/stream")
async def stream_job(job_id: str) -> EventSourceResponse:
    """Stream job events via Server-Sent Events."""
    session_factory = get_db_session()

    async with session_factory() as session:
        session = cast(AsyncSession, session)
        job_exists = await session.execute(select(Job.id).where(Job.id == job_id))
        if job_exists.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        async for chunk in _stream_job_events(job_id, session_factory):
            yield chunk

    return EventSourceResponse(event_generator())
