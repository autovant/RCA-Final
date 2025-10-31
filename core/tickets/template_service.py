"""
Template service for ITSM ticket creation.

Provides reusable, parameterized templates for consistent ticket formatting
across ServiceNow and Jira platforms.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TicketTemplate:
    """Represents a ticket template with metadata."""

    name: str
    platform: str
    fields: Dict[str, Any]
    description: Optional[str] = None
    required_variables: Optional[List[str]] = None


class TemplateRenderError(Exception):
    """Raised when template rendering fails."""


class TicketTemplateService:
    """Service for loading and rendering ITSM ticket templates."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        """
        Initialize template service with ITSM configuration.

        Args:
            config_path: Path to itsm_config.json. Defaults to config/itsm_config.json.
        """
        if config_path is None:
            config_path = str(Path(__file__).parent.parent.parent / "config" / "itsm_config.json")

        self._config_path = config_path
        self._config = self._load_config()
        self._templates = self._load_templates()

    def _load_config(self) -> Dict[str, Any]:
        """Load and parse ITSM configuration file."""
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"ITSM config not found at {self._config_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in ITSM config: {e}")
            return {}

    def _load_templates(self) -> Dict[str, Dict[str, TicketTemplate]]:
        """
        Load templates from configuration.

        Returns:
            Nested dict: {platform: {template_name: TicketTemplate}}
        """
        templates_config = self._config.get("templates", {})
        templates: Dict[str, Dict[str, TicketTemplate]] = {}

        for platform, platform_templates in templates_config.items():
            if platform not in templates:
                templates[platform] = {}

            for template_name, template_fields in platform_templates.items():
                # Extract variables from template strings
                required_vars = self._extract_variables(template_fields)

                templates[platform][template_name] = TicketTemplate(
                    name=template_name,
                    platform=platform,
                    fields=template_fields,
                    description=template_fields.get("_description"),
                    required_variables=required_vars
                )

        logger.info(f"Loaded {sum(len(t) for t in templates.values())} templates across {len(templates)} platforms")
        return templates

    def _extract_variables(self, template_fields: Dict[str, Any]) -> List[str]:
        """
        Extract variable names from template field values.

        Args:
            template_fields: Dictionary of template fields

        Returns:
            List of unique variable names found in templates
        """
        variables = set()
        pattern = re.compile(r'\{(\w+)\}')

        def extract_from_value(value: Any) -> None:
            if isinstance(value, str):
                variables.update(pattern.findall(value))
            elif isinstance(value, dict):
                for v in value.values():
                    extract_from_value(v)
            elif isinstance(value, list):
                for item in value:
                    extract_from_value(item)

        for key, value in template_fields.items():
            if not key.startswith("_"):  # Skip metadata fields
                extract_from_value(value)

        return sorted(list(variables))

    def list_templates(self, platform: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available templates.

        Args:
            platform: Filter by platform ('servicenow' or 'jira'). If None, return all.

        Returns:
            List of template metadata dictionaries
        """
        result = []

        for plat, plat_templates in self._templates.items():
            if platform and plat.lower() != platform.lower():
                continue

            for template_name, template in plat_templates.items():
                result.append({
                    "name": template_name,
                    "platform": plat,
                    "description": template.description,
                    "required_variables": template.required_variables or [],
                    "field_count": len([k for k in template.fields.keys() if not k.startswith("_")])
                })

        return result

    def get_template(self, platform: str, template_name: str) -> Optional[TicketTemplate]:
        """
        Retrieve a specific template.

        Args:
            platform: Target platform ('servicenow' or 'jira')
            template_name: Name of the template

        Returns:
            TicketTemplate or None if not found
        """
        platform_lower = platform.lower()
        if platform_lower not in self._templates:
            logger.warning(f"Platform {platform} not found in templates")
            return None

        template = self._templates[platform_lower].get(template_name)
        if not template:
            logger.warning(f"Template {template_name} not found for platform {platform}")

        return template

    def render_template(
        self,
        platform: str,
        template_name: str,
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Render a template with provided variables.

        Args:
            platform: Target platform ('servicenow' or 'jira')
            template_name: Name of the template to render
            variables: Dictionary of variable name -> value mappings

        Returns:
            Rendered template as a dictionary ready for ticket creation

        Raises:
            TemplateRenderError: If template not found or required variables missing
        """
        template = self.get_template(platform, template_name)
        if not template:
            raise TemplateRenderError(
                f"Template '{template_name}' not found for platform '{platform}'"
            )

        # Check for missing required variables
        missing_vars = []
        for var in (template.required_variables or []):
            if var not in variables:
                missing_vars.append(var)

        if missing_vars:
            raise TemplateRenderError(
                f"Missing required variables for template '{template_name}': {', '.join(missing_vars)}"
            )

        # Render template by substituting variables
        try:
            rendered = self._substitute_variables(template.fields, variables)
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            raise TemplateRenderError(f"Template rendering failed: {str(e)}") from e

        # Remove metadata fields
        rendered = {k: v for k, v in rendered.items() if not k.startswith("_")}

        logger.info(f"Successfully rendered template {template_name} for platform {platform}")
        return rendered

    def _substitute_variables(self, obj: Any, variables: Dict[str, Any]) -> Any:
        """
        Recursively substitute variables in template object.

        Args:
            obj: Template object (can be dict, list, str, or primitive)
            variables: Variable mappings

        Returns:
            Object with variables substituted
        """
        if isinstance(obj, str):
            # Replace {variable} placeholders
            def replacer(match: re.Match) -> str:
                var_name = match.group(1)
                value = variables.get(var_name)
                if value is None:
                    # Keep placeholder if variable not provided (allows partial rendering)
                    return match.group(0)
                return str(value)

            return re.sub(r'\{(\w+)\}', replacer, obj)

        elif isinstance(obj, dict):
            return {k: self._substitute_variables(v, variables) for k, v in obj.items()}

        elif isinstance(obj, list):
            return [self._substitute_variables(item, variables) for item in obj]

        else:
            # Return primitive values as-is
            return obj


def render_template(
    platform: str,
    template_name: str,
    variables: Dict[str, Any],
    config_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to render a ticket template.

    Args:
        platform: Target ITSM platform ('servicenow' or 'jira')
        template_name: Name of the template to render
        variables: Variable mappings for substitution
        config_path: Optional custom path to itsm_config.json

    Returns:
        Rendered template ready for ticket creation

    Raises:
        TemplateRenderError: If rendering fails
    """
    service = TicketTemplateService(config_path=config_path)
    return service.render_template(platform, template_name, variables)
