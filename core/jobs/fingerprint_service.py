"""Similarity search helpers for incident fingerprints."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import AsyncContextManager, Callable, Dict, Iterable, List, Optional, Sequence, cast

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.db.database import get_db_session
from core.db.models import IncidentFingerprint, Job, PlatformDetectionResult
from core.jobs.models import (
    FingerprintStatus,
    RelatedIncidentMatch,
    RelatedIncidentQuery,
    RelatedIncidentSearchRequest,
    RelatedIncidentSearchResult,
    VisibilityScope,
)
from core.llm.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class FingerprintNotFoundError(Exception):
    """Raised when the base session fingerprint cannot be located."""


class FingerprintUnavailableError(Exception):
    """Raised when a session fingerprint lacks an embedding for similarity search."""


class FingerprintSearchService:
    """Service providing similarity search against ``IncidentFingerprint`` records."""

    def __init__(self) -> None:
        self._session_factory = cast(
            Callable[[], AsyncContextManager[AsyncSession]],
            get_db_session(),
        )
        self._embedding_service: Optional[EmbeddingService] = None
        self._embedding_lock = asyncio.Lock()

    async def related_for_session(self, query: RelatedIncidentQuery) -> RelatedIncidentSearchResult:
        """Return related incidents for the provided session identifier."""

        session_uuid = self._coerce_uuid(query.session_id, "session_id")
        min_relevance = self._normalise_relevance(query.min_relevance)
        limit = self._normalise_limit(query.limit)

        should_raise_unavailable = False
        embedding_values: Optional[List[float]] = None
        source_tenant_uuid: Optional[uuid.UUID] = None

        async with self._session_factory() as session:
            async with session.begin():
                fingerprint = await self._load_fingerprint(session, session_uuid)
                if fingerprint is None:
                    raise FingerprintNotFoundError(
                        f"No fingerprint for session {query.session_id}"
                    )

                current_status = FingerprintSearchService._coerce_status(
                    getattr(fingerprint, "fingerprint_status", FingerprintStatus.AVAILABLE.value)
                )
                if current_status != FingerprintStatus.AVAILABLE:
                    await self._ensure_guardrail_note(
                        session,
                        fingerprint,
                        current_status,
                    )

                embedding_vector = getattr(fingerprint, "embedding_vector", None)
                if not embedding_vector:
                    await self._ensure_guardrail_note(
                        session,
                        fingerprint,
                        FingerprintStatus.MISSING,
                        force_status=True,
                    )
                    should_raise_unavailable = True
                else:
                    embedding_values = list(embedding_vector)

                source_tenant_uuid = self._coerce_uuid(
                    str(fingerprint.tenant_id), "tenant_id"
                )

            if should_raise_unavailable:
                raise FingerprintUnavailableError(
                    f"Fingerprint for session {query.session_id} has no embedding"
                )

            matches = await self._execute_similarity_query(
                session,
                embedding_values or [],
                scope=query.scope,
                min_relevance=min_relevance,
                limit=limit,
                source_tenant_id=source_tenant_uuid,
                exclude_session_id=session_uuid,
                platform_filter=query.platform_filter,
            )

        source_workspace_id = str(source_tenant_uuid)
        audit_token = self._generate_audit_token(matches, source_workspace_id)
        return RelatedIncidentSearchResult(
            results=matches,
            audit_token=audit_token,
            source_session_id=str(session_uuid),
            source_workspace_id=source_workspace_id,
        )

    async def search_by_text(
        self,
        request: RelatedIncidentSearchRequest,
        *,
        allowed_workspace_ids: Optional[Sequence[str]] = None,
    ) -> RelatedIncidentSearchResult:
        """Run a free-text search using embedded query semantics."""

        embedding_service = await self._ensure_embedding_service()
        embedding = await embedding_service.embed_text(request.query)

        min_relevance = self._normalise_relevance(request.min_relevance)
        limit = self._normalise_limit(request.limit)

        source_workspace_id: Optional[str] = None
        source_tenant_uuid: Optional[uuid.UUID] = None
        if request.workspace_id:
            source_workspace_id = request.workspace_id
            source_tenant_uuid = self._coerce_uuid(request.workspace_id, "workspace_id")

        allowed_tenants: Optional[List[uuid.UUID]] = None
        if allowed_workspace_ids:
            allowed_tenants = [self._coerce_uuid(w, "allowed_workspace_id") for w in allowed_workspace_ids]

        matches: List[RelatedIncidentMatch]
        async with self._session_factory() as session:
            matches = await self._execute_similarity_query(
                session,
                embedding,
                scope=request.scope,
                min_relevance=min_relevance,
                limit=limit,
                source_tenant_id=source_tenant_uuid,
                allowed_tenant_ids=allowed_tenants,
                platform_filter=request.platform_filter,
            )

        audit_token = self._generate_audit_token(matches, source_workspace_id)
        return RelatedIncidentSearchResult(
            results=matches,
            audit_token=audit_token,
            source_session_id=None,
            source_workspace_id=source_workspace_id,
        )

    async def _load_fingerprint(
        self, session: AsyncSession, session_uuid: uuid.UUID
    ) -> Optional[IncidentFingerprint]:
        stmt = (
            select(IncidentFingerprint)
            .where(IncidentFingerprint.session_id == session_uuid)
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _execute_similarity_query(
        self,
        session: AsyncSession,
        embedding: Sequence[float],
        *,
        scope: VisibilityScope,
        min_relevance: float,
        limit: int,
        source_tenant_id: Optional[uuid.UUID],
        exclude_session_id: Optional[uuid.UUID] = None,
        allowed_tenant_ids: Optional[Sequence[uuid.UUID]] = None,
        platform_filter: Optional[str] = None,
    ) -> List[RelatedIncidentMatch]:
        filters = [
            IncidentFingerprint.embedding_vector.isnot(None),
            IncidentFingerprint.fingerprint_status != FingerprintStatus.MISSING.value,
        ]

        if exclude_session_id:
            filters.append(IncidentFingerprint.session_id != exclude_session_id)

        if allowed_tenant_ids:
            filters.append(IncidentFingerprint.tenant_id.in_(list(allowed_tenant_ids)))
        elif scope == VisibilityScope.TENANT_ONLY:
            if source_tenant_id is None:
                raise ValueError("source_tenant_id required when scope is tenant_only")
            filters.append(IncidentFingerprint.tenant_id == source_tenant_id)
        else:
            if source_tenant_id is not None:
                filters.append(
                    or_(
                        IncidentFingerprint.tenant_id == source_tenant_id,
                        IncidentFingerprint.visibility_scope == VisibilityScope.MULTI_TENANT.value,
                    )
                )
            else:
                filters.append(
                    IncidentFingerprint.visibility_scope == VisibilityScope.MULTI_TENANT.value
                )

        similarity_expr = 1.0 - func.coalesce(
            IncidentFingerprint.embedding_vector.cosine_distance(embedding),
            1.0,
        )
        filters.append(similarity_expr >= min_relevance)

        stmt = (
            select(
                IncidentFingerprint.session_id.label("session_id"),
                IncidentFingerprint.tenant_id.label("tenant_id"),
                similarity_expr.label("relevance"),
                IncidentFingerprint.summary_text,
                IncidentFingerprint.fingerprint_status,
                IncidentFingerprint.safeguard_notes,
                Job.completed_at,
                Job.created_at,
                PlatformDetectionResult.detected_platform,
            )
            .join(Job, Job.id == IncidentFingerprint.session_id)
            .outerjoin(
                PlatformDetectionResult,
                PlatformDetectionResult.job_id == Job.id,
            )
            .where(and_(*filters))
            .order_by(similarity_expr.desc(), Job.completed_at.desc().nullslast())
            .limit(limit)
        )

        if platform_filter:
            normalised = platform_filter.strip().lower()
            if normalised == "unknown":
                stmt = stmt.where(
                    or_(
                        PlatformDetectionResult.detected_platform == normalised,
                        PlatformDetectionResult.detected_platform.is_(None),
                    )
                )
            else:
                stmt = stmt.where(PlatformDetectionResult.detected_platform == normalised)

        result = await session.execute(stmt)
        rows = result.fetchall()
        return [self._row_to_match(row) for row in rows]

    async def _ensure_embedding_service(self) -> EmbeddingService:
        if self._embedding_service is not None:
            return self._embedding_service

        async with self._embedding_lock:
            if self._embedding_service is None:
                service = EmbeddingService()
                await service.initialize()
                self._embedding_service = service
        return self._embedding_service  # type: ignore[return-value]

    @staticmethod
    def _row_to_match(row) -> RelatedIncidentMatch:
        relevance = FingerprintSearchService._clamp(float(row.relevance or 0.0))
        fingerprint_status = FingerprintSearchService._coerce_status(row.fingerprint_status)
        safeguards = FingerprintSearchService._extract_safeguards(row.safeguard_notes)
        detected_platform = (row.detected_platform or "unknown").lower()

        occurred_at = FingerprintSearchService._serialize_datetime(
            row.completed_at or row.created_at
        )

        return RelatedIncidentMatch(
            session_id=str(row.session_id),
            tenant_id=str(row.tenant_id),
            relevance=relevance,
            summary=row.summary_text or "",
            detected_platform=detected_platform,
            fingerprint_status=fingerprint_status,
            safeguards=safeguards,
            occurred_at=occurred_at,
        )

    @staticmethod
    def _serialize_datetime(value: Optional[datetime]) -> Optional[str]:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc).isoformat()
        return value.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _extract_safeguards(value: object) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if item is not None]
        if isinstance(value, dict):
            items: List[str] = []
            for v in value.values():
                if isinstance(v, list):
                    items.extend(str(item) for item in v if item is not None)
                elif v:
                    items.append(str(v))
            return items
        return []

    @staticmethod
    def _coerce_status(value: object) -> FingerprintStatus:
        try:
            return FingerprintStatus(str(value))
        except Exception:
            return FingerprintStatus.DEGRADED

    async def _ensure_guardrail_note(
        self,
        session: AsyncSession,
        fingerprint: IncidentFingerprint,
        status: FingerprintStatus,
        *,
        force_status: bool = False,
        note: Optional[str] = None,
    ) -> None:
        message = note or self._default_guardrail_message(status)
        notes = self._normalise_guardrail_notes(getattr(fingerprint, "safeguard_notes", None))
        bucket = notes.setdefault("fingerprint", [])
        if message not in bucket:
            bucket.append(message)

        fingerprint.safeguard_notes = notes
        if force_status or getattr(fingerprint, "fingerprint_status", None) != status.value:
            fingerprint.fingerprint_status = status.value
        fingerprint.updated_at = datetime.now(timezone.utc)

        session.add(fingerprint)
        await session.flush()

    @staticmethod
    def _normalise_guardrail_notes(raw: object) -> Dict[str, List[str]]:
        if not isinstance(raw, dict):
            return {}

        normalised: Dict[str, List[str]] = {}
        for key, value in raw.items():
            if isinstance(value, list):
                items = [str(item) for item in value if item is not None]
            elif value is None:
                items = []
            else:
                items = [str(value)]

            if items:
                normalised[str(key)] = items

        return normalised

    @staticmethod
    def _default_guardrail_message(status: FingerprintStatus) -> str:
        if status == FingerprintStatus.DEGRADED:
            return (
                "Fingerprint degraded: embedding generation failed. Similarity results may be incomplete."
            )
        if status == FingerprintStatus.MISSING:
            return "Fingerprint unavailable: embedding was not generated for this session."
        return "Fingerprint guardrail triggered."

    @staticmethod
    def _coerce_uuid(value: str, field: str) -> uuid.UUID:
        try:
            return uuid.UUID(str(value))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid {field}: {value}") from exc

    @staticmethod
    def _normalise_relevance(value: Optional[float]) -> float:
        related = getattr(settings, "related_incidents", None)
        default = getattr(related, "MIN_RELEVANCE", 0.6)
        if value is None:
            return FingerprintSearchService._clamp(default)
        return FingerprintSearchService._clamp(value)

    @staticmethod
    def _normalise_limit(value: Optional[int]) -> int:
        related = getattr(settings, "related_incidents", None)
        max_limit = getattr(related, "MAX_RESULTS", 20)
        if value is None:
            return max_limit
        value = max(1, value)
        return min(max_limit, value)

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _generate_audit_token(
        matches: Iterable[RelatedIncidentMatch],
        source_workspace_id: Optional[str],
    ) -> Optional[str]:
        if not source_workspace_id:
            return None

        for match in matches:
            if match.is_cross_workspace(source_workspace_id):
                return str(uuid.uuid4())
        return None


__all__ = [
    "FingerprintNotFoundError",
    "FingerprintUnavailableError",
    "FingerprintSearchService",
]
