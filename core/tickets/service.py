"""
Service helpers for ITSM ticket orchestration and persistence.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.db.database import get_db_session
from core.db.models import Ticket
from core.jobs.service import JobService
from core.logging import get_logger
from core.tickets.clients import (
    JiraClient,
    JiraClientConfig,
    ServiceNowClient,
    ServiceNowClientConfig,
    TicketClientError,
    TicketCreationResult,
)
from core.tickets.settings import TicketSettingsService, TicketToggleState

logger = get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _clean_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Remove keys that have ``None`` values for cleaner persistence."""
    return {key: value for key, value in payload.items() if value is not None}


class TicketService:
    """Persist and orchestrate ITSM ticket metadata associated with RCA jobs."""

    def __init__(self) -> None:
        self._session_factory = get_db_session()
        self._job_service = JobService()
        self._settings_service = TicketSettingsService()

        ticketing = settings.ticketing
        self._servicenow_client: Optional[ServiceNowClient] = None
        if ticketing.SERVICENOW_INSTANCE_URL:
            self._servicenow_client = ServiceNowClient(
                ServiceNowClientConfig(**ticketing.as_servicenow_config())
            )

        self._jira_client: Optional[JiraClient] = None
        if ticketing.JIRA_BASE_URL:
            self._jira_client = JiraClient(
                JiraClientConfig(**ticketing.as_jira_config())
            )

        self._status_refresh_seconds = ticketing.ITSM_STATUS_REFRESH_SECONDS

    async def _get_toggle_state(self) -> TicketToggleState:
        return await self._settings_service.get_settings()

    @staticmethod
    def _merge_payload(
        defaults: Dict[str, Any], overrides: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        merged = dict(defaults)
        if overrides:
            for key, value in overrides.items():
                if isinstance(value, dict) and isinstance(merged.get(key), dict):
                    merged[key] = TicketService._merge_payload(merged[key], value)
                elif value is not None:
                    merged[key] = value
        return _clean_payload(merged)

    def _severity(self, job_dict: Dict[str, Any]) -> str:
        severity = job_dict.get("severity")
        if not severity:
            metrics = job_dict.get("metrics") or {}
            if metrics.get("critical"):
                severity = "critical"
            elif metrics.get("errors"):
                severity = "high"
            elif metrics.get("warnings"):
                severity = "moderate"
        return severity or "low"

    def _servicenow_defaults(self, job_dict: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        severity = self._severity(job_dict)
        priority_map = {"critical": "1", "high": "2", "moderate": "3", "low": "4"}
        priority = priority_map.get(severity, settings.ticketing.SERVICENOW_DEFAULT_PRIORITY or "3")
        summary = job_dict.get("summary") or f"RCA outcome for job {job_id}"
        actions = job_dict.get("recommended_actions") or []
        actions_block = "\n".join(f"- {item}" for item in actions) if actions else "No immediate actions recorded."
        metrics = job_dict.get("metrics") or {}

        description_lines = [
            f"Job ID: {job_id}",
            f"Severity: {severity}",
            "",
            f"Summary: {summary}",
            "",
            "Key Metrics:",
        ]
        for key, value in metrics.items():
            description_lines.append(f"- {key}: {value}")
        description_lines.extend(
            [
                "",
                "Recommended Actions:",
                actions_block,
            ]
        )

        category = None
        categories_field = job_dict.get("categories")
        if isinstance(categories_field, list) and categories_field:
            category = categories_field[0]
        elif isinstance(categories_field, str) and categories_field:
            category = categories_field
        else:
            category = job_dict.get("category")

        if not category:
            category = settings.ticketing.SERVICENOW_DEFAULT_CATEGORY

        return _clean_payload(
            {
                "short_description": summary[:160],
                "description": "\n".join(description_lines),
                "category": category,
                "subcategory": settings.ticketing.SERVICENOW_DEFAULT_SUBCATEGORY,
                "priority": priority,
                "state": settings.ticketing.SERVICENOW_DEFAULT_STATE or "1",
                # Ensure optional routing fields remain present even when unset.
                "assignment_group": settings.ticketing.SERVICENOW_DEFAULT_ASSIGNMENT_GROUP or "",
                "configuration_item": settings.ticketing.SERVICENOW_DEFAULT_CONFIGURATION_ITEM or "",
                "assigned_to": settings.ticketing.SERVICENOW_DEFAULT_ASSIGNED_TO or "",
            }
        )

    def _jira_defaults(self, job_dict: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        severity = self._severity(job_dict)
        summary = job_dict.get("summary") or f"RCA outcome for job {job_id}"
        actions = job_dict.get("recommended_actions") or []
        tags = job_dict.get("tags") or []
        metrics = job_dict.get("metrics") or {}

        description_lines = [
            f"h2. Root Cause Analysis Summary for Job {job_id}",
            "",
            f"*Severity:* {severity}",
            "",
            "*Summary:*",
            summary,
            "",
            "*Key Metrics:*",
        ]
        for key, value in metrics.items():
            description_lines.append(f"- {key}: {value}")
        if actions:
            description_lines.extend(
                ["", "*Recommended Actions:*"] + [f"- {item}" for item in actions]
            )

        priority_map = {
            "critical": "Highest",
            "high": "High",
            "moderate": "Medium",
            "low": "Low",
        }

        return _clean_payload(
            {
                "project_key": settings.ticketing.JIRA_DEFAULT_PROJECT_KEY,
                "issue_type": settings.ticketing.JIRA_DEFAULT_ISSUE_TYPE,
                "summary": summary[:255],
                "description": "\n".join(description_lines),
                "labels": list({*(tags if isinstance(tags, list) else []), *settings.ticketing.JIRA_DEFAULT_LABELS}),
                "priority": priority_map.get(severity, settings.ticketing.JIRA_DEFAULT_PRIORITY),
                "assignee": settings.ticketing.JIRA_DEFAULT_ASSIGNEE,
            }
        )

    async def _load_job_context(self, job_id: str) -> Dict[str, Any]:
        job = await self._job_service.get_job(job_id)
        if job is None:
            raise ValueError(f"Job {job_id} not found")

        structured: Dict[str, Any] = {}
        if job.outputs and isinstance(job.outputs, dict):
            structured = job.outputs.get("json") or job.outputs
        if not structured and isinstance(job.result_data, dict):
            outputs = job.result_data.get("outputs")
            if isinstance(outputs, dict):
                structured = outputs.get("json") or outputs
        structured = structured or {}
        structured.setdefault("job", {"id": job_id, "user_id": job.user_id})
        return structured

    async def _prepare_payload(
        self, job_id: str, platform: str, overrides: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        job_dict = await self._load_job_context(job_id)
        if platform == "servicenow":
            defaults = self._servicenow_defaults(job_dict, job_id)
        elif platform == "jira":
            defaults = self._jira_defaults(job_dict, job_id)
        else:
            raise ValueError(f"Unsupported platform: {platform}")
        return self._merge_payload(defaults, overrides)

    async def _dispatch_remote_create(
        self, platform: str, payload: Dict[str, Any]
    ) -> TicketCreationResult:
        if platform == "servicenow" and self._servicenow_client:
            return await self._servicenow_client.create_incident(payload)
        if platform == "jira" and self._jira_client:
            return await self._jira_client.create_issue(payload)
        raise TicketClientError(
            f"{platform} integration is not configured. Provide credentials to enable creation."
        )

    async def _fetch_remote_status(self, platform: str, ticket_identifier: str) -> Optional[Dict[str, Any]]:
        if platform == "servicenow" and self._servicenow_client:
            return await self._servicenow_client.fetch_incident(ticket_identifier)
        if platform == "jira" and self._jira_client:
            return await self._jira_client.fetch_issue(ticket_identifier)
        return None

    async def _persist_ticket(
        self,
        session: AsyncSession,
        *,
        job_id: str,
        platform: str,
        ticket_id: str,
        url: Optional[str],
        status: str,
        dry_run: bool,
        profile_name: Optional[str],
        payload: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> Ticket:
        record = Ticket(
            job_id=job_id,
            platform=platform,
            ticket_id=ticket_id,
            url=url,
            status=status,
            profile_name=profile_name,
            dry_run=dry_run,
            payload=payload,
            metadata=metadata,
        )
        session.add(record)
        await session.flush()
        await session.refresh(record)

        await self._job_service.create_job_event(
            job_id,
            "ticket-created",
            {
                "ticket_id": ticket_id,
                "platform": platform,
                "status": status,
                "dry_run": dry_run,
            },
            session=session,
        )
        return record

    async def create_ticket(
        self,
        job_id: str,
        platform: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        profile_name: Optional[str] = None,
        dry_run: bool = True,
        ticket_id: Optional[str] = None,
        url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Ticket:
        """Create or persist a ticket record for the supplied platform."""
        overrides = payload or {}
        metadata = metadata or {}

        toggles = await self._get_toggle_state()
        platform_enabled = platform in toggles.active_platforms

        prepared_payload = await self._prepare_payload(job_id, platform, overrides)
        final_ticket_id = ticket_id or f"{platform}-{uuid.uuid4().hex[:8]}"
        final_url = url
        status = "dry-run"
        actual_dry_run = dry_run or not platform_enabled

        if not actual_dry_run:
            try:
                result = await self._dispatch_remote_create(platform, prepared_payload)
            except TicketClientError as exc:
                logger.error(
                    "Failed to create %s ticket for job %s: %s",
                    platform,
                    job_id,
                    exc,
                    exc_info=True,
                )
                metadata["error"] = str(exc)
                actual_dry_run = True
                result = None
            else:
                final_ticket_id = result.ticket_id
                final_url = result.url or final_url
                status = result.status or "created"
                metadata.update(result.metadata)
                metadata["persisted_at"] = _utcnow().isoformat()
                actual_dry_run = False
        else:
            metadata["dry_run_reason"] = (
                "feature-toggle-disabled" if not platform_enabled and not dry_run else "preview"
            )

        if actual_dry_run:
            status = "dry-run"

        async with self._session_factory() as session:
            async with session.begin():
                record = await self._persist_ticket(
                    session,
                    job_id=job_id,
                    platform=platform,
                    ticket_id=final_ticket_id,
                    url=final_url,
                    status=status,
                    dry_run=actual_dry_run,
                    profile_name=profile_name,
                    payload=prepared_payload,
                    metadata=metadata,
                )
            await self._job_service.publish_session_events(session)
            logger.info(
                "Ticket %s recorded for job %s on platform %s (dry_run=%s)",
                final_ticket_id,
                job_id,
                platform,
                actual_dry_run,
            )
            return record

    async def create_enabled_tickets(
        self,
        job_id: str,
        *,
        payloads: Optional[Dict[str, Dict[str, Any]]] = None,
        profile_name: Optional[str] = None,
        dry_run: bool = False,
    ) -> List[Ticket]:
        """
        Create tickets for all enabled platforms honouring dual-tracking mode.
        """
        payloads = payloads or {}
        toggles = await self._get_toggle_state()
        created: List[Ticket] = []
        servicenow_ticket: Optional[Ticket] = None

        if toggles.servicenow_enabled:
            sn_payload = payloads.get("servicenow")
            servicenow_ticket = await self.create_ticket(
                job_id,
                "servicenow",
                sn_payload,
                profile_name=profile_name,
                dry_run=dry_run,
            )
            created.append(servicenow_ticket)

        if toggles.jira_enabled:
            jira_overrides = dict(payloads.get("jira") or {})
            jira_metadata: Dict[str, Any] = {}
            if (
                toggles.dual_tracking
                and servicenow_ticket
                and not servicenow_ticket.dry_run
            ):
                link_text = f"Linked ServiceNow Incident: {servicenow_ticket.ticket_id}"
                existing_description = jira_overrides.get("description")
                if existing_description:
                    jira_overrides["description"] = f"{existing_description}\n\n{link_text}"
                else:
                    jira_overrides["description"] = link_text
                jira_metadata["linked_servicenow"] = {
                    "ticket_id": servicenow_ticket.ticket_id,
                    "url": servicenow_ticket.url,
                }

            jira_ticket = await self.create_ticket(
                job_id,
                "jira",
                jira_overrides,
                profile_name=profile_name,
                dry_run=dry_run,
                metadata=jira_metadata or None,
            )
            created.append(jira_ticket)

        return created

    async def list_job_tickets(
        self,
        job_id: str,
        *,
        refresh: bool = False,
    ) -> List[Ticket]:
        """Return tickets associated with a given job."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(Ticket)
                .where(Ticket.job_id == job_id)
                .order_by(Ticket.created_at.asc())
            )
            tickets = result.scalars().all()

        if refresh and tickets:
            await self._refresh_ticket_batch(tickets)
            async with self._session_factory() as session:
                result = await session.execute(
                    select(Ticket)
                    .where(Ticket.job_id == job_id)
                    .order_by(Ticket.created_at.asc())
                )
                tickets = result.scalars().all()

        return tickets

    async def _refresh_ticket_batch(self, tickets: Iterable[Ticket]) -> None:
        updates: List[Tuple[str, Dict[str, Any], Dict[str, Any]]] = []

        for ticket in tickets:
            if ticket.dry_run:
                continue
            latest = await self._fetch_remote_status(ticket.platform, ticket.ticket_id)
            if not latest:
                continue

            status = None
            if ticket.platform == "servicenow":
                state = str(latest.get("state") or latest.get("incident_state") or "")
                state_map = {
                    "1": "New",
                    "2": "In Progress",
                    "3": "On Hold",
                    "4": "Resolved",
                    "6": "Cancelled",
                    "7": "Closed",
                }
                status = state_map.get(state, latest.get("state"))
            elif ticket.platform == "jira":
                fields = latest.get("fields") or {}
                status = fields.get("status", {}).get("name")

            metadata = ticket.metadata or {}
            metadata["sync"] = {
                "raw": latest,
                "refreshed_at": _utcnow().isoformat(),
            }
            updates.append((ticket.id, {"status": status or ticket.status}, metadata))

        if not updates:
            return

        async with self._session_factory() as session:
            async with session.begin():
                for ticket_id, status_payload, metadata in updates:
                    await session.execute(
                        Ticket.__table__.update()
                        .where(Ticket.id == ticket_id)
                        .values(
                            status=status_payload.get("status"),
                            metadata=metadata,
                            updated_at=_utcnow(),
                        )
                    )

    async def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        """Fetch ticket by primary key."""
        async with self._session_factory() as session:
            return await session.get(Ticket, ticket_id)
