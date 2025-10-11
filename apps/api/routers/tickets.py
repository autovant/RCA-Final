"""
Ticket management endpoints for RCA jobs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, UUID4

from core.jobs.service import JobService
from core.tickets import TicketService

router = APIRouter()
job_service = JobService()
ticket_service = TicketService()


class TicketResponse(BaseModel):
    """Serialised ticket payload."""

    id: str
    job_id: str
    platform: str
    ticket_id: str
    url: Optional[str] = None
    status: str
    profile_name: Optional[str] = None
    dry_run: bool
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TicketListResponse(BaseModel):
    """Collection of tickets for a job."""

    job_id: str
    tickets: List[TicketResponse]


class TicketCreateRequest(BaseModel):
    """Payload for ticket creation or dry-run preview."""

    job_id: UUID4
    platform: Literal["jira", "servicenow"]
    payload: Dict[str, Any] = Field(default_factory=dict)
    profile_name: Optional[str] = None
    dry_run: bool = True
    ticket_id: Optional[str] = None
    url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


def _serialise_ticket(ticket) -> TicketResponse:
    ticket_dict = ticket.to_dict()
    ticket_dict["payload"] = ticket_dict.get("payload") or {}
    ticket_dict["metadata"] = ticket_dict.get("metadata") or {}
    return TicketResponse(**ticket_dict)


@router.get("/{job_id}", response_model=TicketListResponse)
async def list_tickets(job_id: str) -> TicketListResponse:
    """Return tickets linked to a job."""
    job = await job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    tickets = await ticket_service.list_job_tickets(job_id)
    return TicketListResponse(
        job_id=job_id,
        tickets=[_serialise_ticket(ticket) for ticket in tickets],
    )


@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(payload: TicketCreateRequest) -> TicketResponse:
    """Create or record a ticket preview for a job."""
    job_id = str(payload.job_id)
    job = await job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    ticket = await ticket_service.create_ticket(
        job_id=job_id,
        platform=payload.platform,
        payload=payload.payload,
        profile_name=payload.profile_name,
        dry_run=payload.dry_run,
        ticket_id=payload.ticket_id,
        url=payload.url,
        metadata=payload.metadata,
    )
    return _serialise_ticket(ticket)


__all__ = ["router"]
