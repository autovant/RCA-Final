"""
Jobs API endpoints.

Provides a minimal-yet-functional layer over ``JobService`` so that the API can
create, list, and inspect background jobs while the richer workflow evolves.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from apps.api.routers.sse import _event_stream as job_event_stream
from core.db.models import Job, JobEvent
from core.jobs.service import JobService

router = APIRouter()
job_service = JobService()
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}
DEFAULT_CANCEL_REASON = "User requested cancellation"
DEFAULT_PAUSE_REASON = "User paused live analysis"
DEFAULT_RESUME_NOTE = "User resumed live analysis"


def _is_platform_detection_enabled() -> bool:
    """Check if platform detection feature is enabled."""
    env_value = os.getenv("PLATFORM_DETECTION_ENABLED", "").lower()
    return env_value in ("true", "1", "yes", "on")


class JobCreateRequest(BaseModel):
    """Payload required to create a new job."""

    user_id: str = Field(default="anonymous", description="Identifier for the job owner")
    job_type: str = Field(..., description="Type of job, e.g. rca_analysis")
    input_manifest: Dict[str, Any] = Field(default_factory=dict, description="Job specific payload")
    provider: str = Field(default="ollama")
    model: str = Field(default="llama2")
    priority: int = Field(default=0, ge=0, le=10)
    llm_config: Optional[Dict[str, Any]] = Field(
        default=None, description="Provider/model tuning overrides"
    )
    ticketing: Optional[Dict[str, Any]] = Field(
        default=None, description="Per-job ITSM configuration"
    )
    source: Optional[Dict[str, Any]] = Field(
        default=None, description="Origin metadata (e.g. watcher path)"
    )
    file_ids: Optional[List[str]] = Field(
        default=None, description="List of file IDs to attach to this job"
    )


class JobResponse(BaseModel):
    """Projection of a job for API responses."""

    id: str
    job_type: str
    status: str
    user_id: str
    provider: str
    model: str
    llm_config: Optional[Dict[str, Any]] = None
    input_manifest: Optional[Dict[str, Any]] = None
    priority: int
    retry_count: int
    max_retries: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    result_data: Optional[Dict[str, Any]] = None
    outputs: Optional[Dict[str, Any]] = None
    ticketing: Optional[Dict[str, Any]] = None
    source: Optional[Dict[str, Any]] = None
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


class JobFingerprintResponse(BaseModel):
    """Surface-level details about a job fingerprint for debugging."""

    job_id: str = Field(..., description="Job/session identifier associated with the fingerprint")
    tenant_id: str = Field(..., description="Tenant that owns the fingerprint record")
    fingerprint_status: str = Field(..., description="Operational status of the fingerprint")
    visibility_scope: str = Field(..., description="Visibility scope controlling search eligibility")
    summary_text: str = Field(..., description="Summary text captured for this fingerprint")
    relevance_threshold: float = Field(..., description="Threshold used for similarity comparisons")
    safeguard_notes: Dict[str, Any] = Field(default_factory=dict, description="Guardrail notes explaining degraded or missing states")
    embedding_present: bool = Field(..., description="True when the fingerprint has a stored embedding vector")
    created_at: Optional[str] = Field(default=None, description="Creation timestamp in ISO8601 format")
    updated_at: Optional[str] = Field(default=None, description="Last updated timestamp in ISO8601 format")


class PlatformDetectionResponse(BaseModel):
    """Platform detection results and extracted entities for a job."""
    
    job_id: str = Field(..., description="Job identifier")
    platform: str = Field(..., description="Detected platform (blue_prism, uipath, appian, etc.)")
    confidence: float = Field(..., description="Detection confidence score (0.0 to 1.0)")
    detection_method: str = Field(..., description="Method used for detection (content, filename, combined)")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted platform-specific entities")
    detected_at: Optional[str] = Field(default=None, description="Detection timestamp in ISO8601 format")


class JobCancelRequest(BaseModel):
    """Optional payload accompanying a cancel request."""

    reason: Optional[str] = Field(
        default=None,
        description="Optional explanation recorded against the cancellation event",
    )


class JobPauseRequest(BaseModel):
    """Optional payload for pause requests."""

    reason: Optional[str] = Field(
        default=None,
        description="Optional note recorded when the job is paused",
    )


class JobResumeRequest(BaseModel):
    """Optional payload for resume requests."""

    note: Optional[str] = Field(
        default=None,
        description="Optional note recorded when the job resumes",
    )


class JobActionResponse(BaseModel):
    """Acknowledgement returned for state transition operations."""

    job_id: str = Field(..., description="Job identifier the action applied to")
    status: str = Field(..., description="Resulting job status after the action")
    message: str = Field(..., description="Human readable confirmation message")


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
        model_config=payload.llm_config,
        ticketing=payload.ticketing,
        source=payload.source,
        file_ids=payload.file_ids,
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


@router.post(
    "/{job_id}/cancel",
    response_model=JobActionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def cancel_job(job_id: str, payload: Optional[JobCancelRequest] = None) -> JobActionResponse:
    """Request cancellation of a running job."""

    job = await job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job already {job.status}",
        )

    reason = payload.reason if payload and payload.reason else DEFAULT_CANCEL_REASON
    applied = await job_service.cancel_job(job_id, reason=reason)
    if not applied:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job could not be cancelled",
        )

    return JobActionResponse(
        job_id=job_id,
        status="cancelled",
        message="Job cancellation requested",
    )


@router.post(
    "/{job_id}/pause",
    response_model=JobActionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def pause_job(job_id: str, payload: Optional[JobPauseRequest] = None) -> JobActionResponse:
    """Pause a running job so analysis can be resumed later."""

    job = await job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    job_status = getattr(job, "status", None)
    if job_status != "running":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is {job_status}; pause is only supported while running",
        )

    reason = payload.reason if payload and payload.reason else DEFAULT_PAUSE_REASON
    applied = await job_service.pause_job(job_id, reason=reason)
    if not applied:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job could not be paused",
        )

    return JobActionResponse(
        job_id=job_id,
        status="paused",
        message="Job paused",
    )


@router.post(
    "/{job_id}/resume",
    response_model=JobActionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def resume_job(job_id: str, payload: Optional[JobResumeRequest] = None) -> JobActionResponse:
    """Resume a previously paused job."""

    job = await job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    job_status = getattr(job, "status", None)
    if job_status != "paused":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is {job_status}; resume is only supported for paused jobs",
        )

    note = payload.note if payload and payload.note else DEFAULT_RESUME_NOTE
    applied = await job_service.resume_job(job_id, note=note)
    if not applied:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job could not be resumed",
        )

    return JobActionResponse(
        job_id=job_id,
        status="running",
        message="Job resumed",
    )


@router.post(
    "/{job_id}/retry",
    response_model=JobActionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_job(job_id: str) -> JobActionResponse:
    """Reset a completed job so it can be processed again."""

    job = await job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.status not in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is {job.status}; retry is only supported for completed, failed, or cancelled jobs",
        )

    restarted = await job_service.restart_job(job_id)
    if restarted is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return JobActionResponse(
        job_id=job_id,
        status=str(getattr(restarted, "status", "pending")),
        message="Job queued for retry",
    )


@router.get("/{job_id}/fingerprint", response_model=JobFingerprintResponse)
async def get_job_fingerprint(job_id: str) -> JobFingerprintResponse:
    """Return the stored fingerprint metadata for a completed job."""

    fingerprint = await job_service.get_job_fingerprint(job_id)
    if fingerprint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fingerprint not found")

    payload = fingerprint.to_dict()
    return JobFingerprintResponse(
        job_id=payload.get("session_id", job_id),
        tenant_id=payload["tenant_id"],
        fingerprint_status=payload["fingerprint_status"],
        visibility_scope=payload["visibility_scope"],
        summary_text=payload["summary_text"],
        relevance_threshold=float(payload.get("relevance_threshold", 0)),
        safeguard_notes=payload.get("safeguard_notes") or {},
        embedding_present=fingerprint.embedding_vector is not None,
        created_at=payload.get("created_at"),
        updated_at=payload.get("updated_at"),
    )


@router.get("/{job_id}/platform-detection", response_model=PlatformDetectionResponse)
async def get_platform_detection(job_id: str) -> Dict[str, Any]:
    """Return platform detection results and extracted entities for a job."""
    
    # Feature flag guard
    if not _is_platform_detection_enabled():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Platform detection feature is not enabled"
        )
    
    detection_result = await job_service.get_platform_detection(job_id)
    if detection_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Platform detection result not found"
        )
    
    return {
        "job_id": job_id,
        "detected_platform": detection_result.detected_platform,
        "confidence_score": float(detection_result.confidence_score),
        "detection_method": detection_result.detection_method,
        "parser_executed": detection_result.parser_executed,
        "parser_version": detection_result.parser_version,
        "extracted_entities": detection_result.extracted_entities or [],
        "feature_flag_snapshot": detection_result.feature_flag_snapshot or {},
        "created_at": detection_result.created_at.isoformat() if detection_result.created_at else None,
    }


@router.get("/{job_id}/stream")
async def stream_job_events(job_id: str) -> EventSourceResponse:
    """Stream job events via server-sent events (alias for PRD compatibility)."""
    job = await job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return EventSourceResponse(job_event_stream(job_id))


__all__ = ["router"]
