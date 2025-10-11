"""
Job service for managing RCA analysis jobs.
Business logic for job processing, state management, and event tracking.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.db.models import Job, JobEvent, File, Document
from core.db.database import get_db_session
from core.jobs.event_bus import job_event_bus
from core.config import settings

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
    
    async def create_job(
        self, 
        user_id: str,
        job_type: str,
        input_manifest: Dict[str, Any],
        provider: str = "ollama",
        model: str = "llama2",
        priority: int = 0
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
                status="pending"
            )
            
            session.add(job)
            await session.flush()
            
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
        """Get job by ID."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(Job)
                .options(
                    selectinload(Job.files),
                    selectinload(Job.documents),
                )
                .where(Job.id == job_id)
            )
            return result.scalar_one_or_none()
    
    async def get_user_jobs(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Job]:
        """Get jobs for a specific user or all jobs when user_id is omitted."""
        async with self._session_factory() as session:
            query = select(Job)

            if user_id:
                query = query.where(Job.user_id == user_id)

            if status:
                query = query.where(Job.status == status)

            query = query.order_by(Job.created_at.desc())
            query = query.limit(limit).offset(offset)

            result = await session.execute(query)
            return result.scalars().all()
    
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
                    job.started_at = datetime.utcnow()
                    job.updated_at = datetime.utcnow()

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

                job.status = status
                job.updated_at = datetime.utcnow()

                if status == "running" and not job.started_at:
                    job.started_at = datetime.utcnow()
                elif status in ["completed", "failed", "cancelled"] and not job.completed_at:
                    job.completed_at = datetime.utcnow()

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
                job.completed_at = datetime.utcnow()
                job.updated_at = datetime.utcnow()

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
                job.completed_at = datetime.utcnow()
                job.updated_at = datetime.utcnow()
                job.retry_count += 1

                await self.create_job_event(
                    job_id,
                    "failed",
                    {"error": error_message},
                    session=session
                )

            await self._publish_session_events(session)
            logger.error("Failed job: %s, error: %s", job_id, error_message)

    async def cancel_job(self, job_id: str, reason: str = "User cancelled"):
        """Cancel a job."""
        async with self._session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    select(Job).where(Job.id == job_id)
                )
                job = result.scalar_one_or_none()

                if not job or job.status in ["completed", "failed", "cancelled"]:
                    return

                job.status = "cancelled"
                job.error_message = reason
                job.completed_at = datetime.utcnow()
                job.updated_at = datetime.utcnow()

                await self.create_job_event(
                    job_id,
                    "cancelled",
                    {"reason": reason},
                    session=session
                )

            await self._publish_session_events(session)
            logger.info("Cancelled job: %s, reason: %s", job_id, reason)
    
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
            return result.scalars().all()
    
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
            return result.scalars().all()
    
    async def get_job_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get job statistics."""
        async with self._session_factory() as session:
            query = select(Job)
            
            if user_id:
                query = query.where(Job.user_id == user_id)
            
            result = await session.execute(query)
            jobs = result.scalars().all()
            
            stats = {
                "total": len(jobs),
                "by_status": {},
                "by_type": {},
                "avg_duration": 0,
                "success_rate": 0
            }
            
            completed_jobs = [j for j in jobs if j.status == "completed"]
            failed_jobs = [j for j in jobs if j.status == "failed"]
            
            # Status breakdown
            for job in jobs:
                stats["by_status"][job.status] = stats["by_status"].get(job.status, 0) + 1
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
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        async with self._session_factory() as session:
            # Delete old completed jobs
            result = await session.execute(
                select(Job).where(
                    Job.status.in_(["completed", "failed", "cancelled"]),
                    Job.completed_at < cutoff_date
                )
            )
            
            old_jobs = result.scalars().all()
            deleted_count = len(old_jobs)
            
            for job in old_jobs:
                await session.delete(job)
            
            await session.commit()
            
            logger.info(f"Cleaned up {deleted_count} old jobs older than {days} days")
            return deleted_count
