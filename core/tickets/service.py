"""
Service helpers for ITSM ticket persistence and lifecycle events.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from core.db.database import get_db_session
from core.db.models import Ticket
from core.jobs.service import JobService
from core.logging import get_logger

logger = get_logger(__name__)


class TicketService:
    """Persist and retrieve ticket metadata associated with RCA jobs."""

    def __init__(self) -> None:
        self._session_factory = get_db_session()
        self._job_service = JobService()

    async def create_ticket(
        self,
        job_id: str,
        platform: str,
        payload: Dict[str, Any],
        *,
        profile_name: Optional[str] = None,
        dry_run: bool = True,
        ticket_id: Optional[str] = None,
        url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Ticket:
        """
        Persist ticket metadata for a job.

        Args:
            job_id: Associated job identifier.
            platform: Target ITSM platform.
            payload: Request payload that would be submitted to the platform.
            profile_name: Optional profile/credential reference.
            dry_run: Whether this represents a preview only.
            ticket_id: External ticket identifier, if already created.
            url: Ticket URL, if available.
            metadata: Additional diagnostic metadata.
        """
        generated_ticket_id = ticket_id or f"{platform}-{uuid.uuid4().hex[:8]}"
        status = "dry-run" if dry_run else "created"

        async with self._session_factory() as session:
            async with session.begin():
                record = Ticket(
                    job_id=job_id,
                    platform=platform,
                    ticket_id=generated_ticket_id,
                    url=url,
                    status=status,
                    profile_name=profile_name,
                    dry_run=dry_run,
                    payload=payload,
                    metadata=metadata or {},
                )
                session.add(record)
                await session.flush()
                await session.refresh(record)

                await self._job_service.create_job_event(
                    job_id,
                    "ticket-created",
                    {
                        "ticket_id": generated_ticket_id,
                        "platform": platform,
                        "status": status,
                        "dry_run": dry_run,
                    },
                    session=session,
                )

            await self._job_service.publish_session_events(session)
            logger.info(
                "Ticket %s recorded for job %s on platform %s (dry_run=%s)",
                generated_ticket_id,
                job_id,
                platform,
                dry_run,
            )
            return record

    async def list_job_tickets(self, job_id: str) -> List[Ticket]:
        """Return tickets associated with a given job."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(Ticket)
                .where(Ticket.job_id == job_id)
                .order_by(Ticket.created_at.asc())
            )
            return result.scalars().all()

    async def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        """Fetch ticket by primary key."""
        async with self._session_factory() as session:
            return await session.get(Ticket, ticket_id)
