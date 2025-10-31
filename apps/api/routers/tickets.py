"""
Ticket management endpoints for RCA jobs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, UUID4

from core.jobs.service import JobService
from core.tickets import TicketService, TicketSettingsService
from core.tickets.settings import TicketToggleState

router = APIRouter()
job_service = JobService()
ticket_service = TicketService()
settings_service = TicketSettingsService()


class TicketResponse(BaseModel):
    """Serialised ticket payload."""

    id: str
    job_id: str
    platform: str
    ticket_id: str
    url: Optional[str] = None
    status: str
    profile_name: Optional[str] = None
    dry_run: bool
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TicketListResponse(BaseModel):
    """Collection of tickets for a job."""

    job_id: str
    tickets: List[TicketResponse]


class TicketCreateRequest(BaseModel):
    """Payload for ticket creation or dry-run preview."""

    job_id: UUID4
    platform: Literal["jira", "servicenow"]
    payload: Dict[str, Any] = Field(default_factory=dict)
    profile_name: Optional[str] = None
    dry_run: bool = True
    ticket_id: Optional[str] = None
    url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TicketDispatchRequest(BaseModel):
    """Batch creation request honouring feature toggles."""

    job_id: UUID4
    payloads: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    profile_name: Optional[str] = None
    dry_run: bool = False


class TicketToggleResponse(BaseModel):
    """Current ITSM feature toggle state."""

    servicenow_enabled: bool
    jira_enabled: bool
    dual_mode: bool


class TicketToggleUpdateRequest(BaseModel):
    """Update payload for ITSM toggle state."""

    servicenow_enabled: Optional[bool] = None
    jira_enabled: Optional[bool] = None
    dual_mode: Optional[bool] = None


class TemplateMetadataResponse(BaseModel):
    """Metadata for a single ticket template."""

    name: str
    platform: str
    description: Optional[str] = None
    required_variables: List[str]
    field_count: int


class TemplateListResponse(BaseModel):
    """Collection of available ticket templates."""

    templates: List[TemplateMetadataResponse]
    count: int


class CreateFromTemplateRequest(BaseModel):
    """Request payload for creating a ticket from a template."""

    job_id: UUID4
    platform: Literal["jira", "servicenow"]
    template_name: str
    variables: Optional[Dict[str, Any]] = Field(default_factory=dict)
    profile_name: Optional[str] = None
    dry_run: bool = True


class CreateFromTemplateResponse(BaseModel):
    """Response payload for ticket created from template."""

    id: str
    job_id: str
    platform: str
    ticket_id: str
    url: Optional[str] = None
    status: str
    profile_name: Optional[str] = None
    dry_run: bool
    template_name: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


def _serialise_ticket(ticket) -> TicketResponse:
    ticket_dict = ticket.to_dict()
    ticket_dict["payload"] = ticket_dict.get("payload") or {}
    ticket_dict["metadata"] = ticket_dict.get("metadata") or {}
    return TicketResponse(**ticket_dict)


def _serialise_toggle_state(state: TicketToggleState) -> TicketToggleResponse:
    return TicketToggleResponse(
        servicenow_enabled=state.servicenow_enabled,
        jira_enabled=state.jira_enabled,
        dual_mode=state.dual_mode,
    )


@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(payload: TicketCreateRequest) -> TicketResponse:
    """Create or record a ticket preview for a job."""
    job_id = str(payload.job_id)
    job = await job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    ticket = await ticket_service.create_ticket(
        job_id=job_id,
        platform=payload.platform,
        payload=payload.payload,
        profile_name=payload.profile_name,
        dry_run=payload.dry_run,
        ticket_id=payload.ticket_id,
        url=payload.url,
        metadata=payload.metadata,
    )
    return _serialise_ticket(ticket)


@router.post("/dispatch", response_model=TicketListResponse, status_code=status.HTTP_201_CREATED)
async def dispatch_tickets(payload: TicketDispatchRequest) -> TicketListResponse:
    """Create tickets for all enabled platforms in a single call."""
    job_id = str(payload.job_id)
    job = await job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    tickets = await ticket_service.create_enabled_tickets(
        job_id=job_id,
        payloads=payload.payloads,
        profile_name=payload.profile_name,
        dry_run=payload.dry_run,
    )
    return TicketListResponse(
        job_id=job_id,
        tickets=[_serialise_ticket(ticket) for ticket in tickets],
    )


@router.get("/settings/state", response_model=TicketToggleResponse)
async def get_toggle_state() -> TicketToggleResponse:
    """Return the persisted ITSM feature toggle configuration."""
    state = await settings_service.get_settings()
    return _serialise_toggle_state(state)


@router.put("/settings/state", response_model=TicketToggleResponse)
async def update_toggle_state(payload: TicketToggleUpdateRequest) -> TicketToggleResponse:
    """Update the ITSM feature toggle configuration."""
    state = await settings_service.update_settings(
        servicenow_enabled=payload.servicenow_enabled,
        jira_enabled=payload.jira_enabled,
        dual_mode=payload.dual_mode,
    )
    return _serialise_toggle_state(state)


@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(
    platform: Optional[Literal["jira", "servicenow"]] = Query(None, description="Filter templates by platform")
) -> TemplateListResponse:
    """List available ticket templates, optionally filtered by platform."""
    try:
        templates = ticket_service.list_templates(platform=platform)
        
        # Convert templates to response format
        template_responses = [
            TemplateMetadataResponse(
                name=template["name"],
                platform=template["platform"],
                description=template.get("description"),
                required_variables=template["required_variables"],
                field_count=template["field_count"],
            )
            for template in templates
        ]
        
        return TemplateListResponse(
            templates=template_responses,
            count=len(template_responses),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid platform: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list templates: {str(e)}",
        )


@router.post("/from-template", response_model=CreateFromTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_from_template(payload: CreateFromTemplateRequest) -> CreateFromTemplateResponse:
    """Create a ticket from a template with variable substitution."""
    job_id = str(payload.job_id)
    
    # Verify job exists
    job = await job_service.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    try:
        ticket = await ticket_service.create_from_template(
            job_id=job_id,
            platform=payload.platform,
            template_name=payload.template_name,
            variables=payload.variables,
            profile_name=payload.profile_name,
            dry_run=payload.dry_run,
        )
        
        # Serialize ticket to response format
        ticket_dict = ticket.to_dict()
        return CreateFromTemplateResponse(
            id=ticket_dict["id"],
            job_id=ticket_dict["job_id"],
            platform=ticket_dict["platform"],
            ticket_id=ticket_dict["ticket_id"],
            url=ticket_dict.get("url"),
            status=ticket_dict["status"],
            profile_name=ticket_dict.get("profile_name"),
            dry_run=ticket_dict["dry_run"],
            template_name=ticket_dict.get("metadata", {}).get("template_name"),
            payload=ticket_dict.get("payload") or {},
            metadata=ticket_dict.get("metadata") or {},
            created_at=ticket_dict.get("created_at"),
            updated_at=ticket_dict.get("updated_at"),
        )
        
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            )
        elif "validation" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create ticket from template: {str(e)}",
        )


@router.get("/{job_id}", response_model=TicketListResponse)
async def list_tickets(job_id: str, refresh: bool = Query(False)) -> TicketListResponse:
    """Return tickets linked to a job."""
    # Handle demo/placeholder job_id gracefully
    if job_id == "demo-job":
        return TicketListResponse(
            job_id=job_id,
            tickets=[],
        )
    
    # Validate UUID format
    try:
        from uuid import UUID
        UUID(job_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid job ID format. Expected UUID, got: {job_id}"
        )
    
    job = await job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    tickets = await ticket_service.list_job_tickets(job_id, refresh=refresh)
    return TicketListResponse(
        job_id=job_id,
        tickets=[_serialise_ticket(ticket) for ticket in tickets],
    )


__all__ = ["router"]
