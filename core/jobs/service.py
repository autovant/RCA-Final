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
from core.config import settings

logger = logging.getLogger(__name__)


class JobService:
    """Service for managing RCA analysis jobs."""
    
    def __init__(self):
        self.db = get_db_session()
    
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
        async with self.db() as session:
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
                session, job.id, "created", 
                {"input_manifest": input_manifest}
            )
            
            await session.commit()
            
            logger.info(f"Created job: {job.id} for user: {user_id}")
            return job
    
    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        async with self.db() as session:
            result = await session.execute(
                select(Job).where(Job.id == job_id)
            )
            return result.scalar_one_or_none()
    
    async def get_user_jobs(
        self, 
        user_id: str, 
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Job]:
        """Get jobs for a specific user."""
        async with self.db() as session:
            query = select(Job).where(Job.user_id == user_id)
            
            if status:
                query = query.where(Job.status == status)
            
            query = query.order_by(Job.created_at.desc())
            query = query.limit(limit).offset(offset)
            
            result = await session.execute(query)
            return result.scalars().all()
    
    async def get_next_pending_job(self) -> Optional[Job]:
        """Get next pending job for processing (with proper locking)."""
        async with self.db() as session:
            # Use explicit transaction for locking
            async with session.begin():
                result = await session.execute(
                    select(Job)
                    .where(
                        Job.status == "pending",
                        Job.retry_count < Job.max_retries
                    )
                    .order_by(Job.priority.desc(), Job.created_at.asc())
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                
                job = result.scalar_one_or_none()
                
                if job:
                    # Update status within transaction
                    job.status = "running"
                    job.started_at = datetime.utcnow()
                    job.updated_at = datetime.utcnow()
                    
                    # Create started event
                    await self.create_job_event(
                        session, job.id, "started", 
                        {"worker_id": "worker_instance"}
                    )
                    
                    await session.commit()
                    
                    logger.info(f"Acquired job for processing: {job.id}")
                    return job
                
                return None
    
    async def update_job_status(self, job_id: str, status: str, data: Optional[Dict] = None):
        """Update job status."""
        async with self.db() as session:
            result = await session.execute(
                select(Job).where(Job.id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if job:
                job.status = status
                job.updated_at = datetime.utcnow()
                
                if status == "running" and not job.started_at:
                    job.started_at = datetime.utcnow()
                elif status in ["completed", "failed", "cancelled"] and not job.completed_at:
                    job.completed_at = datetime.utcnow()
                
                await session.commit()
                
                # Create status event
                event_data = {"status": status}
                if data:
                    event_data.update(data)
                
                await self.create_job_event(session, job_id, status, event_data)
                
                logger.info(f"Updated job {job_id} status to {status}")
    
    async def complete_job(self, job_id: str, result_data: Dict[str, Any]):
        """Mark job as completed."""
        async with self.db() as session:
            result = await session.execute(
                select(Job).where(Job.id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if job:
                job.status = "completed"
                job.result_data = result_data
                job.completed_at = datetime.utcnow()
                job.updated_at = datetime.utcnow()
                
                await session.commit()
                
                # Create completion event
                await self.create_job_event(
                    session, job_id, "completed", 
                    {"result": result_data}
                )
                
                logger.info(f"Completed job: {job_id}")
    
    async def fail_job(self, job_id: str, error_message: str):
        """Mark job as failed."""
        async with self.db() as session:
            result = await session.execute(
                select(Job).where(Job.id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if job:
                job.status = "failed"
                job.error_message = error_message
                job.completed_at = datetime.utcnow()
                job.updated_at = datetime.utcnow()
                job.retry_count += 1
                
                await session.commit()
                
                # Create failure event
                await self.create_job_event(
                    session, job_id, "failed", 
                    {"error": error_message}
                )
                
                logger.error(f"Failed job: {job_id}, error: {error_message}")
    
    async def cancel_job(self, job_id: str, reason: str = "User cancelled"):
        """Cancel a job."""
        async with self.db() as session:
            result = await session.execute(
                select(Job).where(Job.id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if job and job.status not in ["completed", "failed", "cancelled"]:
                job.status = "cancelled"
                job.error_message = reason
                job.completed_at = datetime.utcnow()
                job.updated_at = datetime.utcnow()
                
                await session.commit()
                
                # Create cancellation event
                await self.create_job_event(
                    session, job_id, "cancelled", 
                    {"reason": reason}
                )
                
                logger.info(f"Cancelled job: {job_id}, reason: {reason}")
    
    async def create_job_event(
        self, 
        session: AsyncSession, 
        job_id: str, 
        event_type: str, 
        data: Optional[Dict] = None
    ):
        """Create a job event."""
        event = JobEvent(
            job_id=job_id,
            event_type=event_type,
            data=data or {}
        )
        
        session.add(event)
        
        logger.debug(f"Created event {event_type} for job {job_id}")
    
    async def get_job_events(
        self, 
        job_id: str, 
        limit: int = 100,
        event_type: Optional[str] = None
    ) -> List[JobEvent]:
        """Get events for a job."""
        async with self.db() as session:
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
        async with self.db() as session:
            query = select(JobEvent).where(JobEvent.job_id == job_id)
            
            if since:
                query = query.where(JobEvent.created_at > since)
            
            query = query.order_by(JobEvent.created_at.asc())
            
            result = await session.execute(query)
            return result.scalars().all()
    
    async def get_job_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get job statistics."""
        async with self.db() as session:
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
        
        async with self.db() as session:
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