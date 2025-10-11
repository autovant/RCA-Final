"""
Summary endpoints for retrieving structured RCA outputs.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from core.jobs.service import JobService

router = APIRouter()
job_service = JobService()


class OutputBundle(BaseModel):
    """Structured representations of RCA outputs."""

    markdown: str = ""
    html: str = ""
    json: Dict[str, Any] = Field(default_factory=dict)


class JobSummaryResponse(BaseModel):
    """Response payload for RCA summary retrieval."""

    job_id: str
    analysis_type: Optional[str] = None
    generated_at: Optional[str] = None
    outputs: OutputBundle
    metrics: Optional[Dict[str, Any]] = None
    ticketing: Optional[Dict[str, Any]] = None


@router.get("/{job_id}", response_model=JobSummaryResponse)
async def get_summary(job_id: str) -> JobSummaryResponse:
    """Return the latest RCA outputs for the requested job."""
    job = await job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    outputs = job.outputs or {}
    if not outputs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Summary outputs not available for this job",
        )

    result = job.result_data or {}

    bundle = OutputBundle(
        markdown=str(outputs.get("markdown", "")),
        html=str(outputs.get("html", "")),
        json=outputs.get("json") or {},
    )

    return JobSummaryResponse(
        job_id=job_id,
        analysis_type=result.get("analysis_type") or job.job_type,
        generated_at=result.get("generated_at"),
        outputs=bundle,
        metrics=result.get("metrics"),
        ticketing=job.ticketing or {},
    )


__all__ = ["router"]
