"""Audit helpers for recording analyst related-incident views."""

from __future__ import annotations

import logging
import uuid
from typing import Iterable, List, Optional, Sequence, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.db.database import get_db_session
from core.db.models import AnalystAuditEvent

logger = logging.getLogger(__name__)


class AnalystAuditRecorder:
    """Persist analyst audit events for cross-workspace access."""

    def __init__(self) -> None:
        self._session_factory = get_db_session()

    async def record_related_incident_views(
        self,
        *,
        analyst_id: str,
        source_workspace_id: str,
        source_session_id: str,
        related_pairs: Iterable[Tuple[str, str]],
        session: Optional[AsyncSession] = None,
    ) -> int:
        """Insert ``AnalystAuditEvent`` rows for cross-workspace related incident views."""

        if not getattr(settings, "related_incidents", None) or not getattr(
            settings.related_incidents, "AUDIT_TRAIL_ENABLED", True
        ):
            return 0

        try:
            analyst_uuid = uuid.UUID(str(analyst_id))
            source_workspace_uuid = uuid.UUID(str(source_workspace_id))
            source_session_uuid = uuid.UUID(str(source_session_id))
        except (ValueError, TypeError) as exc:
            logger.warning("Skipping audit insert due to invalid identifiers", exc_info=exc)
            return 0

        entries = self._prepare_entries(
            analyst_uuid,
            source_workspace_uuid,
            source_session_uuid,
            related_pairs,
        )
        if not entries:
            return 0

        if session is not None:
            session.add_all(entries)
            await session.flush()
            return len(entries)

        async with self._session_factory() as scoped_session:
            scoped_session.add_all(entries)
            await scoped_session.flush()
            return len(entries)

    @staticmethod
    def _prepare_entries(
        analyst_uuid: uuid.UUID,
        source_workspace_uuid: uuid.UUID,
        source_session_uuid: uuid.UUID,
        related_pairs: Iterable[Tuple[str, str]],
    ) -> List[AnalystAuditEvent]:
        entries: List[AnalystAuditEvent] = []
        for workspace_id, session_id in related_pairs:
            try:
                related_workspace_uuid = uuid.UUID(str(workspace_id))
                related_session_uuid = uuid.UUID(str(session_id))
            except (ValueError, TypeError):
                logger.debug("Skipping audit pair with invalid identifiers", extra={
                    "workspace_id": workspace_id,
                    "session_id": session_id,
                })
                continue

            if related_workspace_uuid == source_workspace_uuid:
                continue

            entries.append(
                AnalystAuditEvent(
                    analyst_id=analyst_uuid,
                    source_workspace_id=source_workspace_uuid,
                    related_workspace_id=related_workspace_uuid,
                    session_id=source_session_uuid,
                    related_session_id=related_session_uuid,
                    action="viewed_related_incident",
                )
            )
        return entries


_recorder = AnalystAuditRecorder()


async def record_related_incident_views(
    *,
    analyst_id: str,
    source_workspace_id: str,
    source_session_id: str,
    related_pairs: Sequence[Tuple[str, str]],
    session: Optional[AsyncSession] = None,
) -> int:
    """Public helper delegating to the shared :class:`AnalystAuditRecorder`."""

    return await _recorder.record_related_incident_views(
        analyst_id=analyst_id,
        source_workspace_id=source_workspace_id,
        source_session_id=source_session_id,
        related_pairs=related_pairs,
        session=session,
    )


__all__ = [
    "AnalystAuditRecorder",
    "record_related_incident_views",
]
