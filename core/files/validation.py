"""Extraction policy checks and error mapping for compressed uploads."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from core.files import extraction, validators

__all__ = [
    "ExtractionViolation",
    "ExtractionPolicy",
    "validate_extraction_result",
    "validate_archive_before_extraction",
    "map_extraction_error",
]


@dataclass
class ExtractionViolation:
    """Represents a policy violation encountered during extraction."""

    code: str
    message: str
    detail: Optional[str] = None


@dataclass
class ExtractionPolicy:
    """Policy thresholds for archive extraction checks."""

    max_total_bytes: int = extraction.DEFAULT_SIZE_LIMIT_BYTES
    max_duration_seconds: int = extraction.DEFAULT_TIMEOUT_SECONDS


def validate_extraction_result(
    result: extraction.ExtractionResult,
    *,
    policy: Optional[ExtractionPolicy] = None,
) -> List[ExtractionViolation]:
    """Evaluate an `ExtractionResult` against configured policy limits."""

    policy = policy or ExtractionPolicy()
    violations: List[ExtractionViolation] = []

    if result.total_size_bytes > policy.max_total_bytes:
        violations.append(
            ExtractionViolation(
                code="size_limit_exceeded",
                message="Extracted contents exceed allowed size",
                detail=f"total={result.total_size_bytes} limit={policy.max_total_bytes}",
            )
        )

    if result.duration_seconds > policy.max_duration_seconds:
        violations.append(
            ExtractionViolation(
                code="duration_exceeded",
                message="Extraction exceeded time limit",
                detail=f"duration={result.duration_seconds:.2f}s limit={policy.max_duration_seconds}s",
            )
        )

    return violations


def validate_archive_before_extraction(
    archive_path: Path,
    *,
    safeguard_config: Optional[validators.SafeguardConfig] = None,
) -> List[ExtractionViolation]:
    """Validate archive against safeguards before attempting extraction.
    
    This pre-extraction check identifies potential decompression bombs,
    excessive member counts, and path traversal attempts.
    
    Args:
        archive_path: Path to archive file
        safeguard_config: Safeguard configuration (uses defaults if None)
    
    Returns:
        List of violations (empty if archive passes all safeguards)
    """
    safeguard_violations = validators.evaluate_archive_safeguards(
        archive_path,
        config=safeguard_config,
    )

    # Convert safeguard violations to extraction violations
    violations: List[ExtractionViolation] = []
    for sv in safeguard_violations:
        violations.append(
            ExtractionViolation(
                code=sv.code,
                message=sv.message,
                detail=sv.detail,
            )
        )

    return violations


def map_extraction_error(error: Exception) -> ExtractionViolation:
    """Translate extraction exceptions to policy violations for user messaging."""

    if isinstance(error, extraction.ExtractionTimeoutExceeded):
        return ExtractionViolation(
            code="duration_exceeded",
            message="Archive extraction exceeded the time limit",
        )
    if isinstance(error, extraction.ExtractionSizeLimitExceeded):
        return ExtractionViolation(
            code="size_limit_exceeded",
            message="Archive extraction exceeded the size limit",
        )
    if isinstance(error, extraction.UnsupportedArchiveTypeError):
        return ExtractionViolation(
            code="unsupported_archive",
            message="Archive format is not supported",
        )
    if isinstance(error, extraction.ArchiveExtractionError):
        return ExtractionViolation(
            code="extraction_failed",
            message=str(error) or "Archive extraction failed",
        )
    return ExtractionViolation(
        code="extraction_failed",
        message="Archive extraction failed",
        detail=str(error) or None,
    )
