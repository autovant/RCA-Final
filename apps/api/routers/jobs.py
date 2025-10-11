"""
Jobs API endpoints.

Provides a minimal-yet-functional layer over ``JobService`` so that the API can
create, list, and inspect background jobs while the richer workflow evolves.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from core.jobs.service import JobService
from core.db.models import Job, JobEvent

router = APIRouter()
job_service = JobService()


class JobCreateRequest(BaseModel):
    """Payload required to create a new job."""

    user_id: str = Field(default="anonymous", description="Identifier for the job owner")
    job_type: str = Field(..., description="Type of job, e.g. rca_analysis")
    input_manifest: Dict[str, Any] = Field(default_factory=dict, description="Job specific payload")
    provider: str = Field(default="ollama")
    model: str = Field(default="llama2")
    priority: int = Field(default=0, ge=0, le=10)


class JobResponse(BaseModel):
    """Projection of a job for API responses."""

    id: str
    job_type: str
    status: str
    user_id: str
    provider: str
    model: str
    priority: int
    retry_count: int
    max_retries: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    @classmethod
    def from_orm(cls, job: Job) -> "JobResponse":
        return cls(**job.to_dict())


class JobEventResponse(BaseModel):
    """Serialised representation of a job event."""

    id: str
    job_id: str
    event_type: str
    data: Optional[Dict[str, Any]]
    created_at: Optional[str] = None

    @classmethod
    def from_orm(cls, event: JobEvent) -> "JobEventResponse":
        return cls(**event.to_dict())


def _parse_iso_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    cleaned = value.rstrip("Z")
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid ISO8601 timestamp: {value}",
        ) from exc


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=JobResponse)
async def create_job(payload: JobCreateRequest) -> JobResponse:
    """Queue a new job for processing."""
    job = await job_service.create_job(
        user_id=payload.user_id,
        job_type=payload.job_type,
        input_manifest=payload.input_manifest,
        provider=payload.provider,
        model=payload.model,
        priority=payload.priority,
    )
    return JobResponse.from_orm(job)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    """Fetch details of a specific job."""
    job = await job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobResponse.from_orm(job)


@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    user_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[JobResponse]:
    """List jobs optionally filtered by user and/or status."""
    jobs = await job_service.get_user_jobs(
        user_id=user_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return [JobResponse.from_orm(job) for job in jobs]


@router.get("/{job_id}/events", response_model=List[JobEventResponse])
async def job_events(
    job_id: str,
    since: Optional[str] = Query(None, description="ISO timestamp from which to stream events"),
    limit: int = Query(100, ge=1, le=500),
) -> List[JobEventResponse]:
    """Return recent events for the given job."""
    job = await job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    since_dt = _parse_iso_timestamp(since)
    events = await job_service.get_job_events_since(job_id, since_dt)
    if not events:
        return []

    # Enforce limit after filtering by timestamp to keep the implementation simple.
    trimmed = events[-limit:]
    return [JobEventResponse.from_orm(event) for event in trimmed]


__all__ = ["router"]
