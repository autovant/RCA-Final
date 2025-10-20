"""
Prompt template management API endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from core.prompts import get_prompt_manager

router = APIRouter()


class PromptTemplateInfo(BaseModel):
    """Basic prompt template information."""
    
    name: str
    description: str
    editable: bool
    variables: List[str]


class PromptTemplateDetail(BaseModel):
    """Detailed prompt template with content."""
    
    name: str
    description: str
    system_prompt: str
    user_prompt_template: str
    variables: List[str]
    editable: bool
    custom: bool = False


class UpdatePromptRequest(BaseModel):
    """Request to update a prompt template."""
    
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    description: Optional[str] = None


class CreatePromptRequest(BaseModel):
    """Request to create a new prompt template."""
    
    template_name: str = Field(..., description="Unique identifier for the template")
    name: str = Field(..., description="Display name")
    description: str
    system_prompt: str
    user_prompt_template: str
    variables: List[str] = Field(default_factory=list)


class ListPromptsResponse(BaseModel):
    """Response with list of available prompts."""
    
    templates: Dict[str, PromptTemplateInfo]


@router.get("", response_model=ListPromptsResponse)
async def list_prompts() -> ListPromptsResponse:
    """List all available prompt templates."""
    manager = get_prompt_manager()
    templates_dict = manager.list_templates()
    
    templates = {
        key: PromptTemplateInfo(**value)
        for key, value in templates_dict.items()
    }
    
    return ListPromptsResponse(templates=templates)


@router.get("/{template_name}", response_model=PromptTemplateDetail)
async def get_prompt(template_name: str) -> PromptTemplateDetail:
    """Get a specific prompt template with full details."""
    manager = get_prompt_manager()
    template = manager.get_template(template_name)
    
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt template '{template_name}' not found"
        )
    
    return PromptTemplateDetail(**template)


@router.put("/{template_name}")
async def update_prompt(
    template_name: str,
    request: UpdatePromptRequest
) -> Dict[str, Any]:
    """Update an existing prompt template."""
    manager = get_prompt_manager()
    
    success = manager.update_template(
        template_name,
        system_prompt=request.system_prompt,
        user_prompt_template=request.user_prompt_template,
        description=request.description
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to update template '{template_name}'. It may not exist or is not editable."
        )
    
    return {
        "success": True,
        "message": f"Template '{template_name}' updated successfully"
    }


@router.post("")
async def create_prompt(request: CreatePromptRequest) -> Dict[str, Any]:
    """Create a new custom prompt template."""
    manager = get_prompt_manager()
    
    success = manager.create_template(
        request.template_name,
        name=request.name,
        description=request.description,
        system_prompt=request.system_prompt,
        user_prompt_template=request.user_prompt_template,
        variables=request.variables
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Template '{request.template_name}' already exists"
        )
    
    return {
        "success": True,
        "message": f"Template '{request.template_name}' created successfully",
        "template_name": request.template_name
    }


@router.delete("/{template_name}")
async def delete_prompt(template_name: str) -> Dict[str, Any]:
    """Delete a custom prompt template."""
    manager = get_prompt_manager()
    
    success = manager.delete_template(template_name)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to delete template '{template_name}'. It may not exist or is not a custom template."
        )
    
    return {
        "success": True,
        "message": f"Template '{template_name}' deleted successfully"
    }


@router.post("/reset")
async def reset_prompts() -> Dict[str, Any]:
    """Reset all prompt templates to defaults."""
    manager = get_prompt_manager()
    manager.reset_to_defaults()
    
    return {
        "success": True,
        "message": "All prompt templates reset to defaults"
    }


__all__ = ["router"]
