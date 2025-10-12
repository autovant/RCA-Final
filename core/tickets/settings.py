"""
Database-backed feature flag management for ITSM integrations.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.db.database import get_db_session
from core.db.models import TicketIntegrationSettings


@dataclass(slots=True)
class TicketToggleState:
    """Serializable view of current ticket integration toggles."""

    servicenow_enabled: bool
    jira_enabled: bool
    dual_mode: bool

    @property
    def active_platforms(self) -> tuple[str, ...]:
        """Return the enabled platforms respecting dual-mode settings."""
        platforms: list[str] = []
        if self.servicenow_enabled:
            platforms.append("servicenow")
        if self.jira_enabled:
            platforms.append("jira")
        return tuple(platforms)

    @property
    def dual_tracking(self) -> bool:
        """True when both integrations are enabled and dual mode is requested."""
        return self.dual_mode and self.servicenow_enabled and self.jira_enabled


class TicketSettingsService:
    """Persistence helper for ITSM feature toggles."""

    def __init__(self) -> None:
        self._session_factory = get_db_session()
        # Lightweight in-memory cache guarded by an asyncio lock to avoid
        # redundant round-trips on high traffic dashboards.
        self._cached_state: Optional[TicketToggleState] = None
        self._cache_lock = asyncio.Lock()

    async def _ensure_defaults(self, session: AsyncSession) -> TicketIntegrationSettings:
        result = await session.execute(select(TicketIntegrationSettings))
        record = result.scalar_one_or_none()
        if record:
            return record

        defaults = settings.ticketing
        record = TicketIntegrationSettings(
            servicenow_enabled=defaults.SERVICENOW_ENABLED,
            jira_enabled=defaults.JIRA_ENABLED,
            dual_mode=defaults.ITSM_DUAL_MODE_DEFAULT,
        )
        session.add(record)
        await session.flush()
        await session.refresh(record)
        return record

    async def get_settings(self, *, force_refresh: bool = False) -> TicketToggleState:
        """Return the current toggle state, optionally bypassing the cache."""
        async with self._cache_lock:
            if self._cached_state and not force_refresh:
                return self._cached_state

            async with self._session_factory() as session:
                async with session.begin():
                    record = await self._ensure_defaults(session)

            state = TicketToggleState(
                servicenow_enabled=record.servicenow_enabled,
                jira_enabled=record.jira_enabled,
                dual_mode=record.dual_mode,
            )
            self._cached_state = state
            return state

    async def update_settings(
        self,
        *,
        servicenow_enabled: Optional[bool] = None,
        jira_enabled: Optional[bool] = None,
        dual_mode: Optional[bool] = None,
    ) -> TicketToggleState:
        """Persist toggle changes and update the in-memory cache."""
        async with self._session_factory() as session:
            async with session.begin():
                record = await self._ensure_defaults(session)

                if servicenow_enabled is not None:
                    record.servicenow_enabled = servicenow_enabled
                if jira_enabled is not None:
                    record.jira_enabled = jira_enabled
                if dual_mode is not None:
                    record.dual_mode = dual_mode

                await session.flush()
                await session.refresh(record)

        async with self._cache_lock:
            state = TicketToggleState(
                servicenow_enabled=record.servicenow_enabled,
                jira_enabled=record.jira_enabled,
                dual_mode=record.dual_mode,
            )
            self._cached_state = state
            return state


__all__ = ["TicketSettingsService", "TicketToggleState"]
