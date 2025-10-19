"""Related incident API endpoints."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from core.jobs.fingerprint_service import (
    FingerprintNotFoundError,
    FingerprintSearchService,
    FingerprintUnavailableError,
)
from core.jobs.models import (
    RelatedIncidentMatch,
    RelatedIncidentQuery,
    RelatedIncidentSearchRequest,
    RelatedIncidentSearchResult,
    VisibilityScope,
)
from core.metrics.collectors import observe_related_incident_response
from core.metrics.models import RelatedIncidentMetricEvent
from core.security import get_current_user
from core.security.audit import record_related_incident_views

logger = logging.getLogger(__name__)
router = APIRouter()
_search_service = FingerprintSearchService()


class SearchScope(str, Enum):
    CURRENT_WORKSPACE = "current_workspace"
    AUTHORIZED_WORKSPACES = "authorized_workspaces"


class RelatedIncidentItem(BaseModel):
    session_id: str
    tenant_id: str
    relevance: float = Field(ge=0.0, le=1.0)
    summary: str
    detected_platform: str
    occurred_at: Optional[str] = None
    fingerprint_status: str
    safeguards: List[str] = Field(default_factory=list)


class RelatedIncidentListResponse(BaseModel):
    results: List[RelatedIncidentItem] = Field(default_factory=list)
    audit_token: Optional[str] = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    scope: SearchScope = Field(default=SearchScope.AUTHORIZED_WORKSPACES)
    min_relevance: Optional[float] = Field(None, ge=0.0, le=1.0)
    limit: Optional[int] = Field(None, ge=1, le=50)
    platform: Optional[str] = None
    workspace_id: Optional[str] = Field(
        default=None,
        description="Identifier for the current workspace when scope=current_workspace",
    )

    @field_validator("workspace_id")
    @classmethod
    def _require_workspace(cls, value: Optional[str], values) -> Optional[str]:
        scope = values.get("scope")
        if scope == SearchScope.CURRENT_WORKSPACE and not value:
            raise ValueError("workspace_id is required when scope=current_workspace")
        return value


def _visibility_from_scope(scope: SearchScope) -> VisibilityScope:
    if scope == SearchScope.CURRENT_WORKSPACE:
        return VisibilityScope.TENANT_ONLY
    return VisibilityScope.MULTI_TENANT


def _serialise_match(match: RelatedIncidentMatch) -> RelatedIncidentItem:
    return RelatedIncidentItem(
        session_id=match.session_id,
        tenant_id=match.tenant_id,
        relevance=match.relevance,
        summary=match.summary,
        detected_platform=match.detected_platform,
        occurred_at=match.occurred_at,
        fingerprint_status=match.fingerprint_status.value,
        safeguards=match.safeguards,
    )


def _build_response(result: RelatedIncidentSearchResult) -> RelatedIncidentListResponse:
    items = [_serialise_match(match) for match in result.results]
    return RelatedIncidentListResponse(results=items, audit_token=result.audit_token)


async def _record_audit_if_needed(
    user,
    result: RelatedIncidentSearchResult,
) -> None:
    if not result.source_workspace_id or not result.source_session_id:
        return
    pairs = result.cross_workspace_pairs()
    if not pairs:
        return
    try:
        await record_related_incident_views(
            analyst_id=str(getattr(user, "id", "")),
            source_workspace_id=result.source_workspace_id,
            source_session_id=result.source_session_id or "",
            related_pairs=pairs,
        )
    except Exception:
        logger.exception("Failed to record analyst audit event")


@router.get(
    "/{session_id}/related",
    response_model=RelatedIncidentListResponse,
    status_code=status.HTTP_200_OK,
)
async def related_incidents(
    session_id: str,
    min_relevance: Optional[float] = Query(None, ge=0.0, le=1.0),
    limit: Optional[int] = Query(None, ge=1, le=50),
    platform: Optional[str] = Query(None, min_length=1),
    current_user=Depends(get_current_user),
) -> RelatedIncidentListResponse:
    """Retrieve related incidents for a completed RCA session."""

    query_args: Dict[str, Any] = {
        "session_id": session_id,
    }
    if min_relevance is not None:
        query_args["min_relevance"] = min_relevance
    if limit is not None:
        query_args["limit"] = limit
    if platform is not None:
        query_args["platform_filter"] = platform
    query = RelatedIncidentQuery(**query_args)

    try:
        result = await _search_service.related_for_session(query)
    except FingerprintNotFoundError as exc:
        logger.info("Related incidents requested for unknown session", extra={"session_id": session_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session fingerprint not found") from exc
    except FingerprintUnavailableError as exc:
        logger.info("Related incidents unavailable for session", extra={"session_id": session_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session fingerprint unavailable") from exc

    await _record_audit_if_needed(current_user, result)
    observe_related_incident_response(
        RelatedIncidentMetricEvent(
            source_workspace_id=result.source_workspace_id,
            scope=query.scope.value,
            channel="session",
            result_count=len(result.results),
            cross_workspace_count=len(result.cross_workspace_pairs()),
            platform_filter=query.platform_filter,
            audit_token_issued=bool(result.audit_token),
        )
    )
    return _build_response(result)


@router.post(
    "/search",
    response_model=RelatedIncidentListResponse,
    status_code=status.HTTP_200_OK,
)
async def search_related_incidents(
    payload: SearchRequest,
    current_user=Depends(get_current_user),
) -> RelatedIncidentListResponse:
    """Search historical incidents similar to the provided query."""

    visibility = _visibility_from_scope(payload.scope)
    request_args: Dict[str, Any] = {
        "query": payload.query,
        "scope": visibility,
        "workspace_id": payload.workspace_id,
    }
    if payload.min_relevance is not None:
        request_args["min_relevance"] = payload.min_relevance
    if payload.limit is not None:
        request_args["limit"] = payload.limit
    if payload.platform is not None:
        request_args["platform_filter"] = payload.platform
    internal_request = RelatedIncidentSearchRequest(**request_args)

    allowed_ids: Optional[Sequence[str]] = None
    if payload.scope == SearchScope.CURRENT_WORKSPACE and payload.workspace_id:
        allowed_ids = [payload.workspace_id]

    result = await _search_service.search_by_text(
        internal_request,
        allowed_workspace_ids=allowed_ids,
    )

    await _record_audit_if_needed(current_user, result)
    observe_related_incident_response(
        RelatedIncidentMetricEvent(
            source_workspace_id=result.source_workspace_id,
            scope=payload.scope.value,
            channel="text_search",
            result_count=len(result.results),
            cross_workspace_count=len(result.cross_workspace_pairs()),
            platform_filter=payload.platform,
            audit_token_issued=bool(result.audit_token),
        )
    )
    return _build_response(result)


__all__ = ["router"]
