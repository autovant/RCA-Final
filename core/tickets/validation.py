"""
Validation layer for ITSM ticket payloads.

Validates ticket creation payloads against field mappings and rules
defined in itsm_config.json before transmission to ITSM platforms.
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
class ValidationError:
    """Represents a single field validation error."""

    field: str
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """Result of payload validation."""

    valid: bool
    errors: List[ValidationError]

    def error_dict(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return errors grouped by field for API responses."""
        error_map: Dict[str, List[Dict[str, Any]]] = {}
        for err in self.errors:
            if err.field not in error_map:
                error_map[err.field] = []
            error_map[err.field].append({
                "error_code": err.error_code,
                "message": err.message,
                "details": err.details or {}
            })
        return error_map


class TicketPayloadValidator:
    """Validates ITSM ticket payloads against configuration schemas."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        """
        Initialize validator with ITSM configuration.

        Args:
            config_path: Path to itsm_config.json. Defaults to config/itsm_config.json.
        """
        if config_path is None:
            config_path = str(Path(__file__).parent.parent.parent / "config" / "itsm_config.json")

        self._config_path = config_path
        self._config = self._load_config()

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

    def validate_payload(self, platform: str, payload: Dict[str, Any]) -> ValidationResult:
        """
        Validate a ticket payload against platform-specific rules.

        Args:
            platform: Target platform ('servicenow' or 'jira')
            payload: Ticket creation payload to validate

        Returns:
            ValidationResult with validity status and error details
        """
        platform_lower = platform.lower()
        if platform_lower not in ["servicenow", "jira"]:
            return ValidationResult(
                valid=False,
                errors=[ValidationError(
                    field="_platform",
                    error_code="invalid_platform",
                    message=f"Unsupported platform: {platform}. Must be 'servicenow' or 'jira'."
                )]
            )

        platform_config = self._config.get(platform_lower, {})
        field_mapping = platform_config.get("field_mapping", {})
        validation_rules = self._config.get("validation", {}).get("rules", {}).get(platform_lower, {})

        errors: List[ValidationError] = []

        # Validate each field in the payload
        for field_name, field_value in payload.items():
            field_spec = field_mapping.get(field_name, {})
            if not field_spec:
                # Field not in mapping - log warning but don't fail
                logger.warning(f"Field {field_name} not in {platform} field mapping")
                continue

            # Check required fields
            if field_spec.get("required", False) and not field_value:
                errors.append(ValidationError(
                    field=field_name,
                    error_code="required_field_missing",
                    message=f"Field '{field_name}' is required but was not provided or is empty.",
                    details={"description": field_spec.get("description")}
                ))
                continue

            # Skip further validation if field is empty and not required
            if not field_value:
                continue

            # Validate max length for string fields
            max_length = field_spec.get("max_length")
            if max_length and isinstance(field_value, str):
                if len(field_value) > max_length:
                    errors.append(ValidationError(
                        field=field_name,
                        error_code="max_length_exceeded",
                        message=f"Field '{field_name}' exceeds maximum length of {max_length} characters (current: {len(field_value)}).",
                        details={"max_length": max_length, "current_length": len(field_value)}
                    ))

            # Validate enumerated values
            allowed_values = field_spec.get("values")
            if allowed_values:
                if isinstance(allowed_values, list):
                    # List of allowed values
                    if field_value not in allowed_values:
                        errors.append(ValidationError(
                            field=field_name,
                            error_code="invalid_enum_value",
                            message=f"Field '{field_name}' has invalid value '{field_value}'. Allowed values: {', '.join(str(v) for v in allowed_values)}.",
                            details={"allowed_values": allowed_values, "provided_value": field_value}
                        ))
                elif isinstance(allowed_values, dict):
                    # Dictionary mapping (e.g., priority codes to labels)
                    if str(field_value) not in allowed_values:
                        errors.append(ValidationError(
                            field=field_name,
                            error_code="invalid_enum_value",
                            message=f"Field '{field_name}' has invalid value '{field_value}'. Allowed values: {', '.join(allowed_values.keys())}.",
                            details={"allowed_values": list(allowed_values.keys()), "provided_value": field_value}
                        ))

            # Validate regex pattern
            validation_pattern = field_spec.get("validation")
            if validation_pattern and isinstance(field_value, str):
                try:
                    if not re.match(validation_pattern, field_value):
                        errors.append(ValidationError(
                            field=field_name,
                            error_code="pattern_mismatch",
                            message=f"Field '{field_name}' does not match required pattern: {validation_pattern}.",
                            details={"pattern": validation_pattern, "provided_value": field_value}
                        ))
                except re.error as e:
                    logger.error(f"Invalid regex pattern for field {field_name}: {e}")

            # Validate field type
            field_type = field_spec.get("type")
            if field_type == "array" and not isinstance(field_value, list):
                errors.append(ValidationError(
                    field=field_name,
                    error_code="invalid_type",
                    message=f"Field '{field_name}' must be an array but got {type(field_value).__name__}.",
                    details={"expected_type": "array", "provided_type": type(field_value).__name__}
                ))

        # Check for missing required fields that aren't in the payload
        for field_name, field_spec in field_mapping.items():
            if field_spec.get("required", False) and field_name not in payload:
                errors.append(ValidationError(
                    field=field_name,
                    error_code="required_field_missing",
                    message=f"Required field '{field_name}' is missing from payload.",
                    details={"description": field_spec.get("description")}
                ))

        is_valid = len(errors) == 0
        if not is_valid:
            logger.warning(f"Validation failed for {platform} payload with {len(errors)} errors")

        return ValidationResult(valid=is_valid, errors=errors)


def validate_ticket_payload(platform: str, payload: Dict[str, Any], config_path: Optional[str] = None) -> ValidationResult:
    """
    Convenience function to validate a ticket payload.

    Args:
        platform: Target ITSM platform ('servicenow' or 'jira')
        payload: Ticket creation payload
        config_path: Optional custom path to itsm_config.json

    Returns:
        ValidationResult with validity status and errors
    """
    validator = TicketPayloadValidator(config_path=config_path)
    return validator.validate_payload(platform, payload)
