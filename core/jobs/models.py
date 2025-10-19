"""Domain models supporting job fingerprinting and platform detection."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, PositiveInt, model_validator

__all__ = [
    "VisibilityScope",
    "FingerprintStatus",
    "IncidentFingerprintDTO",
    "RelatedIncidentMatch",
    "RelatedIncidentQuery",
    "RelatedIncidentSearchRequest",
    "RelatedIncidentSearchResult",
    "PlatformDetectionOutcome",
]


class VisibilityScope(str, Enum):
    """Scope applied to related incident visibility."""

    TENANT_ONLY = "tenant_only"
    MULTI_TENANT = "multi_tenant"


class FingerprintStatus(str, Enum):
    """Operational state of an incident fingerprint."""

    AVAILABLE = "available"
    DEGRADED = "degraded"
    MISSING = "missing"


class IncidentFingerprintDTO(BaseModel):
    """Serialized representation returned by fingerprint services."""

    session_id: str
    tenant_id: str
    summary_text: str = Field(max_length=4096)
    relevance_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    visibility_scope: VisibilityScope = VisibilityScope.TENANT_ONLY
    fingerprint_status: FingerprintStatus = FingerprintStatus.MISSING
    safeguard_notes: Dict[str, Any] = Field(default_factory=dict)
    embedding_present: bool = False


class RelatedIncidentQuery(BaseModel):
    """Query parameters used when retrieving related incidents by session."""

    session_id: str
    scope: VisibilityScope = VisibilityScope.MULTI_TENANT
    min_relevance: float = Field(default=0.6, ge=0.0, le=1.0)
    limit: int = Field(default=10, gt=0, le=50)
    platform_filter: Optional[str] = None


class RelatedIncidentMatch(BaseModel):
    """Related incident returned to the analyst UI/API."""

    session_id: str
    tenant_id: str
    relevance: float = Field(ge=0.0, le=1.0)
    summary: str = Field(max_length=4096)
    detected_platform: str = "unknown"
    fingerprint_status: FingerprintStatus = FingerprintStatus.AVAILABLE
    safeguards: List[str] = Field(default_factory=list)
    occurred_at: Optional[str] = None

    def is_cross_workspace(self, source_workspace_id: Optional[str]) -> bool:
        """Return True when the match belongs to a different workspace."""

        if not source_workspace_id:
            return False
        return self.tenant_id != source_workspace_id


class RelatedIncidentSearchRequest(BaseModel):
    """Query payload for free-text related incident search."""

    query: str = Field(..., min_length=1, max_length=2000)
    scope: VisibilityScope = VisibilityScope.MULTI_TENANT
    min_relevance: float = Field(default=0.6, ge=0.0, le=1.0)
    limit: int = Field(default=10, gt=0, le=50)
    platform_filter: Optional[str] = None
    workspace_id: Optional[str] = Field(
        default=None,
        description="Anchor workspace identifier when limiting to current tenant.",
    )

    @model_validator(mode="after")
    def _validate_workspace_scope(cls, values):
        if values.scope == VisibilityScope.TENANT_ONLY and not values.workspace_id:
            raise ValueError("workspace_id is required when scope=tenant_only")
        return values


class RelatedIncidentSearchResult(BaseModel):
    """Container for similarity search results and audit context."""

    results: List[RelatedIncidentMatch] = Field(default_factory=list)
    audit_token: Optional[str] = None
    source_session_id: Optional[str] = None
    source_workspace_id: Optional[str] = None

    def cross_workspace_pairs(self) -> List[Tuple[str, str]]:
        """Return workspace/session pairs for cross-workspace matches."""

        if not self.source_workspace_id:
            return []

        pairs: List[tuple[str, str]] = []
        for match in self.results:
            if match.is_cross_workspace(self.source_workspace_id):
                pairs.append((match.tenant_id, match.session_id))
        return pairs


class PlatformDetectionOutcome(BaseModel):
    """Captured metadata from platform detection and parser execution."""

    job_id: str
    detected_platform: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    detection_method: str
    parser_executed: bool = False
    parser_version: Optional[str] = None
    extracted_entities: List[Dict[str, Any]] = Field(default_factory=list)
    feature_flag_snapshot: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: Optional[PositiveInt] = None

    @property
    def should_run_parser(self) -> bool:
        """Return True when parser execution is expected."""

        return self.parser_executed or self.confidence_score >= 0.5
