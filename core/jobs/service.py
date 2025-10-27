"""
Job service for managing RCA analysis jobs.
Business logic for job processing, state management, and event tracking.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
import uuid
from typing import Any, Dict, List, Optional, cast

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, defer

from core.config import settings
from core.db.database import get_db_session
from core.db.models import (
    ConversationTurn,
    Document,
    File,
    IncidentFingerprint,
    Job,
    JobEvent,
    Ticket,
)
from core.jobs.event_bus import job_event_bus
from core.cache.response_cache import cached

logger = logging.getLogger(__name__)


class JobService:

    """Service for managing RCA analysis jobs."""
    
    def __init__(self):
        self._session_factory = get_db_session()
        self._event_bus = job_event_bus

    @staticmethod
    def _register_session_event(
        session: AsyncSession, job_id: str, event: JobEvent
    ) -> None:
        """Attach pending events to the session for post-commit publishing."""
        pending = session.info.setdefault("_job_pending_events", [])
        pending.append((job_id, event))

    async def _publish_session_events(self, session: AsyncSession) -> None:
        """Publish any events queued on the session."""
        pending = session.info.pop("_job_pending_events", [])
        for job_id, event in pending:
            await self._event_bus.publish(job_id, event.to_dict())

    async def publish_session_events(self, session: AsyncSession) -> None:
        """Public wrapper used by external callers to flush queued events."""
        await self._publish_session_events(session)

    async def _get_next_conversation_sequence(
        self, session: AsyncSession, job_id: str
    ) -> int:
        result = await session.execute(
            select(func.max(ConversationTurn.sequence)).where(
                ConversationTurn.job_id == job_id
            )
        )
        current = result.scalar_one_or_none()
        return int(current or 0)

    async def append_conversation_turns(
        self,
        job_id: str,
        turns: List[Dict[str, Any]],
        *,
        event_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Persist a batch of conversation turns for a job.

        Args:
            job_id: Target job identifier.
            turns: Sequence of dicts containing ``role`` and ``content`` keys,
                with optional ``metadata`` or ``token_count`` entries.
            event_metadata: Payload appended to the emitted job event.
        """
        if not turns:
            return

        async with self._session_factory() as session:
            async with session.begin():
                sequence = await self._get_next_conversation_sequence(session, job_id)
                for turn in turns:
                    sequence += 1
                    record = ConversationTurn(
                        job_id=job_id,
                        role=turn["role"],
                        content=turn["content"],
                        sequence=sequence,
                        token_count=turn.get("token_count"),
                        metadata=turn.get("metadata") or {},
                    )
                    session.add(record)

                await self.create_job_event(
                    job_id,
                    "conversation-turn",
                    {
                        "count": len(turns),
                        "latest_sequence": sequence,
                        "roles": [turn.get("role") for turn in turns],
                        **(event_metadata or {}),
                    },
                    session=session,
                )

            await self._publish_session_events(session)

    async def create_job(
        self,
        user_id: str,
        job_type: str,
        input_manifest: Dict[str, Any],
        provider: str = "ollama",
        model: str = "llama2",
        priority: int = 0,
        *,
        model_config: Optional[Dict[str, Any]] = None,
        ticketing: Optional[Dict[str, Any]] = None,
        source: Optional[Dict[str, Any]] = None,
        file_ids: Optional[List[str]] = None,
    ) -> Job:
        """Create a new analysis job."""
        async with self._session_factory() as session:
            job = Job(
                job_type=job_type,
                user_id=user_id,
                input_manifest=input_manifest,
                provider=provider,
                model=model,
                priority=priority,
                status="pending",
                model_config=model_config or {},
                ticketing=ticketing or {},
                source=source,
            )
            
            session.add(job)
            await session.flush()
            
            # Attach files if provided
            if file_ids:
                from core.db.models import File

                logger.info(
                    f"Attaching {len(file_ids)} files to job {job.id}: {file_ids}"
                )
                for file_id in file_ids:
                    file_obj = await session.get(File, file_id)
                    if not file_obj:
                        logger.warning(f"File {file_id} not found in database!")
                        continue

                    # Reset file processing state so the new job reprocesses recycled files.
                    file_record = cast(File, file_obj)
                    setattr(file_record, "job_id", job.id)
                    setattr(file_record, "processed", False)
                    setattr(file_record, "processed_at", None)
                    setattr(file_record, "processing_error", None)

                    logger.info(f"Attached file {file_id} to job {job.id}")
            else:
                logger.warning(f"No file_ids provided for job {job.id}")
            
            # Create initial event
            await self.create_job_event(
                job.id,
                "created",
                {"input_manifest": input_manifest},
                session=session
            )
            
            await session.commit()
            await self._publish_session_events(session)
            await session.refresh(job)
            
            logger.info(f"Created job: {job.id} for user: {user_id}")
            return job
    
    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID with full data (for detail views)."""
        async with self._session_factory() as session:
            stmt = (
                select(Job)
                .options(
                    # Load relationships
                    selectinload(Job.files),
                    selectinload(Job.documents).defer(Document.content),
                    selectinload(Job.conversation_turns),
                    selectinload(Job.tickets),
                    selectinload(Job.fingerprint),
                )
                .execution_options(populate_existing=True)
                .where(Job.id == job_id)
            )
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()
            
            # Access all fields to ensure they're loaded before session closes
            if job:
                # Trigger loading of all non-deferred fields
                _ = job.input_manifest
                _ = job.result_data
                _ = job.outputs
                _ = job.model_config
                _ = job.ticketing
                _ = job.source
                _ = job.error_message
            
            return job
    
    async def get_job_status(self, job_id: str) -> Optional[str]:
        """Return the current status for the job, or ``None`` when missing."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(Job.status).where(Job.id == job_id)
            )
            return result.scalar_one_or_none()

    async def get_user_jobs(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Job]:
        """Get jobs for a specific user or all jobs when user_id is omitted (optimized for list views)."""
        async with self._session_factory() as session:
            query = select(Job).options(
                # Load files for list views
                selectinload(Job.files)
            )
            query = query.execution_options(populate_existing=True)

            if user_id:
                query = query.where(Job.user_id == user_id)

            if status:
                query = query.where(Job.status == status)

            query = query.order_by(Job.created_at.desc())
            query = query.limit(limit).offset(offset)

            result = await session.execute(query)
            jobs = list(result.scalars().all())
            
            # Trigger loading of all fields before session closes
            for job in jobs:
                _ = job.input_manifest
                _ = job.result_data
                _ = job.outputs
                _ = job.model_config
                _ = job.ticketing
                _ = job.source
                _ = job.error_message
            
            return jobs
    
    async def get_next_pending_job(self) -> Optional[Job]:
        """Get next pending job for processing (with proper locking)."""
        async with self._session_factory() as session:
            job: Optional[Job] = None

            async with session.begin():
                result = await session.execute(
                    select(Job)
                    .options(
                        selectinload(Job.files),
                        selectinload(Job.documents),
                    )
                    .where(
                        Job.status == "pending",
                        Job.retry_count < Job.max_retries,
                    )
                    .order_by(Job.priority.desc(), Job.created_at.asc())
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                job = result.scalar_one_or_none()

                if job:
                    job.status = "running"
                    job.started_at = datetime.now(timezone.utc)
                    job.updated_at = datetime.now(timezone.utc)

                    await self.create_job_event(
                        job.id,
                        "started",
                        {"worker_id": "worker_instance"},
                        session=session,
                    )

            if job:
                await self._publish_session_events(session)
                await session.refresh(job)
                logger.info("Acquired job for processing: %s", job.id)

            return job

            return job

    async def get_job_fingerprint(self, job_id: str) -> Optional[IncidentFingerprint]:
        """Return the fingerprint associated with a job when present."""

        try:
            job_uuid = uuid.UUID(str(job_id))
        except (ValueError, TypeError):
            return None

        async with self._session_factory() as session:
            result = await session.execute(
                select(IncidentFingerprint)
                .where(IncidentFingerprint.session_id == job_uuid)
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def get_platform_detection(self, job_id: str) -> Optional["PlatformDetectionResult"]:
        """Return platform detection results for a job when present."""
        from core.db.models import PlatformDetectionResult

        try:
            job_uuid = uuid.UUID(str(job_id))
        except (ValueError, TypeError):
            return None

        async with self._session_factory() as session:
            result = await session.execute(
                select(PlatformDetectionResult)
                .where(PlatformDetectionResult.job_id == job_uuid)
                .limit(1)
            )
            return result.scalar_one_or_none()
    
    async def update_job_status(self, job_id: str, status: str, data: Optional[Dict] = None):
        """Update job status."""
        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    select(Job).where(Job.id == job_id)
                )
                job = result.scalar_one_or_none()
                if not job:
                    return

                now = datetime.now(timezone.utc)
                previous_status = getattr(job, "status", None)
                setattr(job, "status", status)
                setattr(job, "updated_at", now)

                if status == "running":
                    if previous_status in {"completed", "failed", "cancelled"}:
                        setattr(job, "started_at", now)
                    elif getattr(job, "started_at", None) is None:
                        setattr(job, "started_at", now)
                    setattr(job, "completed_at", None)
                    setattr(job, "error_message", None)
                    setattr(job, "result_data", None)
                    setattr(job, "outputs", {})
                elif status in ["pending", "draft"]:
                    setattr(job, "started_at", None)
                    setattr(job, "completed_at", None)
                    setattr(job, "error_message", None)
                    setattr(job, "result_data", None)
                    setattr(job, "outputs", {})
                elif status in ["completed", "failed", "cancelled"]:
                    setattr(job, "completed_at", now)
                    if status != "failed":
                        setattr(job, "error_message", None)

                event_data = {"status": status}
                if data:
                    event_data.update(data)

                await self.create_job_event(
                    job_id,
                    status,
                    event_data,
                    session=session
                )

            await self._publish_session_events(session)
            logger.info("Updated job %s status to %s", job_id, status)

            logger.info("Updated job %s status to %s", job_id, status)
    
    async def complete_job(self, job_id: str, result_data: Dict[str, Any]):
        """Mark job as completed."""
        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    select(Job).where(Job.id == job_id)
                )
                job = result.scalar_one_or_none()
                if not job:
                    return

                job.status = "completed"
                job.result_data = result_data
                job.outputs = result_data.get("outputs") or {}
                if "ticketing" in result_data and result_data["ticketing"]:
                    job.ticketing = result_data["ticketing"]
                job.completed_at = datetime.now(timezone.utc)
                job.updated_at = datetime.now(timezone.utc)

                await self.create_job_event(
                    job_id,
                    "completed",
                    {"result": result_data},
                    session=session
                )

            await self._publish_session_events(session)
            logger.info("Completed job: %s", job_id)
    
    async def fail_job(self, job_id: str, error_message: str):
        """Mark job as failed."""
        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    select(Job).where(Job.id == job_id)
                )
                job = result.scalar_one_or_none()

                if not job:
                    return

                job.status = "failed"
                job.error_message = error_message
                job.completed_at = datetime.now(timezone.utc)
                job.updated_at = datetime.now(timezone.utc)
                job.retry_count += 1

                await self.create_job_event(
                    job_id,
                    "failed",
                    {"error": error_message},
                    session=session
                )

            await self._publish_session_events(session)
            logger.error("Failed job: %s, error: %s", job_id, error_message)


    async def cancel_job(self, job_id: str, reason: str = "User cancelled") -> bool:
        """Cancel a job.

        Returns ``True`` when the state transition was applied, otherwise ``False``.
        """
        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    select(Job).where(Job.id == job_id)
                )
                job = result.scalar_one_or_none()

                if not job or job.status in ["completed", "failed", "cancelled"]:
                    return False

                setattr(job, "status", "cancelled")
                setattr(job, "error_message", reason)
                setattr(job, "completed_at", datetime.now(timezone.utc))
                setattr(job, "updated_at", datetime.now(timezone.utc))

                await self.create_job_event(
                    job_id,
                    "cancelled",
                    {"reason": reason},
                    session=session
                )

            await self._publish_session_events(session)
            logger.info("Cancelled job: %s, reason: %s", job_id, reason)
            return True

    async def pause_job(self, job_id: str, reason: str = "Paused from UI") -> bool:
        """Pause a running job."""
        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(select(Job).where(Job.id == job_id))
                job = result.scalar_one_or_none()

                if not job:
                    return False

                status = getattr(job, "status", None)
                if status != "running":
                    return False

                setattr(job, "status", "paused")
                setattr(job, "updated_at", datetime.now(timezone.utc))

                await self.create_job_event(
                    job_id,
                    "paused",
                    {"reason": reason},
                    session=session,
                )

            await self._publish_session_events(session)
            logger.info("Paused job: %s, reason: %s", job_id, reason)
            return True

    async def resume_job(self, job_id: str, note: str = "Resumed from UI") -> bool:
        """Resume a paused job."""
        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(select(Job).where(Job.id == job_id))
                job = result.scalar_one_or_none()

                if not job:
                    return False

                status = getattr(job, "status", None)
                if status != "paused":
                    return False

                now = datetime.now(timezone.utc)
                setattr(job, "status", "running")
                setattr(job, "updated_at", now)

                await self.create_job_event(
                    job_id,
                    "resumed",
                    {"status": "running", "message": note},
                    session=session,
                )

            await self._publish_session_events(session)
            logger.info("Resumed job: %s", job_id)
            return True

    async def restart_job(self, job_id: str) -> Optional[Job]:
        """Reset a completed job so it can be re-queued for processing."""

        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    select(Job)
                    .options(selectinload(Job.files))
                    .where(Job.id == job_id)
                )
                job = result.scalar_one_or_none()

                if not job:
                    return None

                previous_status = job.status
                now = datetime.now(timezone.utc)

                setattr(job, "status", "pending")
                setattr(job, "started_at", None)
                setattr(job, "completed_at", None)
                setattr(job, "error_message", None)
                setattr(job, "result_data", None)
                setattr(job, "outputs", {})
                setattr(job, "updated_at", now)
                # Ensure the worker can pick the job up again even if automatic retries were exhausted.
                setattr(
                    job,
                    "retry_count",
                    min(job.retry_count or 0, max(job.max_retries - 1, 0)),
                )

                for file_record in getattr(job, "files", []) or []:
                    setattr(file_record, "processed", False)
                    setattr(file_record, "processed_at", None)
                    setattr(file_record, "processing_error", None)

                await self.create_job_event(
                    job_id,
                    "restart-requested",
                    {
                        "previous_status": previous_status,
                    },
                    session=session,
                )

                await self.create_job_event(
                    job_id,
                    "pending",
                    {"status": "pending", "trigger": "restart"},
                    session=session,
                )

            await self._publish_session_events(session)
            logger.info("Restarted job %s (previous status: %s)", job_id, previous_status)
            return job

    
    async def create_job_event(
        self,
        job_id: str,
        event_type: str,
        data: Optional[Dict] = None,
        *,
        session: Optional[AsyncSession] = None,
    ) -> JobEvent:
        """
        Persist a job event, optionally reusing an existing session.
        
        When a session is supplied the event is queued for publication and
        emitted once the caller commits.
        """

        async def _persist(target_session: AsyncSession) -> JobEvent:
            event = JobEvent(
                job_id=job_id,
                event_type=event_type,
                data=data or {},
            )
            target_session.add(event)
            await target_session.flush()
            await target_session.refresh(event)
            logger.debug("Created event %s for job %s", event_type, job_id)
            return event

        if session is not None:
            event = await _persist(session)
            self._register_session_event(session, job_id, event)
            return event

        async with self._session_factory() as session_ctx:
            async with session_ctx.begin():
                event = await _persist(session_ctx)
            await self._event_bus.publish(job_id, event.to_dict())
            return event
    
    async def get_job_events(
        self, 
        job_id: str, 
        limit: int = 100,
        event_type: Optional[str] = None
    ) -> List[JobEvent]:
        """Get events for a job."""
        async with self._session_factory() as session:
            query = select(JobEvent).where(JobEvent.job_id == job_id)
            
            if event_type:
                query = query.where(JobEvent.event_type == event_type)
            
            query = query.order_by(JobEvent.created_at.desc())
            query = query.limit(limit)
            
            result = await session.execute(query)
            events = list(result.scalars().all())
            
            # Trigger loading of all fields before session closes
            for event in events:
                _ = event.data
            
            return events
    
    async def get_job_events_since(
        self, 
        job_id: str, 
        since: Optional[datetime]
    ) -> List[JobEvent]:
        """Get events since a specific timestamp."""
        async with self._session_factory() as session:
            query = select(JobEvent).where(JobEvent.job_id == job_id)
            
            if since:
                query = query.where(JobEvent.created_at > since)
            
            query = query.order_by(JobEvent.created_at.asc())
            
            result = await session.execute(query)
            events = list(result.scalars().all())
            
            # Trigger loading of all fields before session closes
            for event in events:
                _ = event.data
            
            return events

    async def get_conversation(
        self,
        job_id: str,
        limit: Optional[int] = None,
    ) -> List[ConversationTurn]:
        """Fetch persisted conversation turns for a job."""
        async with self._session_factory() as session:
            query = (
                select(ConversationTurn)
                .where(ConversationTurn.job_id == job_id)
                .order_by(ConversationTurn.sequence.asc())
            )
            if limit:
                query = query.limit(limit)
            result = await session.execute(query)
            return list(result.scalars().all())
    
    @cached(ttl=60, key_prefix="job_stats")  # Cache for 60 seconds
    async def get_job_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get job statistics (cached for 60 seconds)."""
        async with self._session_factory() as session:
            query = select(Job)
            
            if user_id:
                query = query.where(Job.user_id == user_id)
            
            result = await session.execute(query)
            jobs = list(result.scalars().all())
            
            stats = {
                "total": len(jobs),
                "by_status": {},
                "by_type": {},
                "avg_duration": 0,
                "success_rate": 0
            }
            
            completed_jobs = [j for j in jobs if getattr(j, "status", None) == "completed"]
            failed_jobs = [j for j in jobs if getattr(j, "status", None) == "failed"]
            
            # Status breakdown
            for job in jobs:
                job_status = getattr(job, "status", None)
                if job_status is not None:
                    stats["by_status"][job_status] = stats["by_status"].get(job_status, 0) + 1
                stats["by_type"][job.job_type] = stats["by_type"].get(job.job_type, 0) + 1
            
            # Success rate
            if completed_jobs or failed_jobs:
                stats["success_rate"] = len(completed_jobs) / (len(completed_jobs) + len(failed_jobs)) * 100
            
            # Average duration
            durations = [j.duration_seconds for j in completed_jobs if j.duration_seconds]
            if durations:
                stats["avg_duration"] = sum(durations) / len(durations)
            
            return stats
    
    async def cleanup_old_jobs(self, days: int = 30):
        """Clean up old completed jobs."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        async with self._session_factory() as session:
            # Delete old completed jobs
            result = await session.execute(
                select(Job).where(
                    Job.status.in_(["completed", "failed", "cancelled"]),
                    Job.completed_at < cutoff_date
                )
            )
            
            old_jobs = list(result.scalars().all())
            deleted_count = len(old_jobs)
            
            for job in old_jobs:
                await session.delete(job)
            
            await session.commit()
            
            logger.info(f"Cleaned up {deleted_count} old jobs older than {days} days")
            return deleted_count
