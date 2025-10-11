"""
Conversation history endpoints for RCA jobs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from core.jobs.service import JobService

router = APIRouter()
job_service = JobService()


class ConversationTurnModel(BaseModel):
    """Single conversation turn."""

    id: str
    role: str
    sequence: int
    content: str
    token_count: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None


class ConversationResponse(BaseModel):
    """Conversation response payload."""

    job_id: str
    turns: List[ConversationTurnModel]


@router.get("/{job_id}", response_model=ConversationResponse)
async def get_conversation(job_id: str) -> ConversationResponse:
    """Return the persisted LLM conversation for a job."""
    job = await job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    turns = await job_service.get_conversation(job_id)
    payload: List[ConversationTurnModel] = []
    for turn in turns:
        turn_dict = turn.to_dict()
        turn_dict["metadata"] = turn_dict.get("metadata") or {}
        payload.append(ConversationTurnModel(**turn_dict))
    return ConversationResponse(job_id=job_id, turns=payload)


__all__ = ["router"]
