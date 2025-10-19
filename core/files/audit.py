"""Archive extraction audit recording and retrieval."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models import ArchiveExtractionAudit
from core.files.extraction import ExtractionResult
from core.files.validators import SafeguardViolation

__all__ = [
    "record_extraction_audit",
    "get_extraction_audit",
    "create_audit_from_extraction",
]


def _determine_archive_type(archive_path: Path) -> str:
    """Determine archive type enum value from file extension."""
    suffix = archive_path.suffix.lower()
    stem = archive_path.stem.lower()

    if suffix == ".zip":
        return "zip"
    elif suffix == ".gz" and stem.endswith(".tar"):
        return "tar_gz"
    elif suffix == ".gz":
        return "gz"
    elif suffix == ".bz2" and stem.endswith(".tar"):
        return "tar_bz2"
    elif suffix == ".bz2":
        return "bz2"
    elif suffix == ".xz" and stem.endswith(".tar"):
        return "tar_xz"
    elif suffix == ".xz":
        return "xz"
    elif suffix == ".tgz":
        return "tar_gz"
    elif suffix == ".tbz2":
        return "tar_bz2"
    elif suffix == ".txz":
        return "tar_xz"
    else:
        # Default to gz for unknown
        return "gz"


def _determine_guardrail_status(violations: List[SafeguardViolation]) -> tuple[str, Optional[str]]:
    """Determine guardrail status and blocked reason from violations.
    
    Returns:
        Tuple of (status, blocked_reason)
    """
    if not violations:
        return ("passed", None)

    # Check for error-level violations
    errors = [v for v in violations if v.severity == "error"]
    if errors:
        # Prioritize specific error types
        if any(v.code == "excessive_decompression_ratio" for v in errors):
            reason = "; ".join(v.message for v in errors if v.code == "excessive_decompression_ratio")
            return ("blocked_ratio", reason)
        elif any(v.code == "excessive_member_count" for v in errors):
            reason = "; ".join(v.message for v in errors if v.code == "excessive_member_count")
            return ("blocked_members", reason)
        else:
            # Generic error
            reason = "; ".join(v.message for v in errors)
            return ("error", reason)

    # No errors, archive passed
    return ("passed", None)


async def record_extraction_audit(
    session: AsyncSession,
    *,
    job_id: uuid.UUID,
    archive_path: Path,
    extraction_result: Optional[ExtractionResult],
    safeguard_violations: List[SafeguardViolation],
    compressed_size: int,
    estimated_uncompressed: Optional[int] = None,
    member_count: int = 0,
) -> ArchiveExtractionAudit:
    """Record an archive extraction audit event.
    
    Args:
        session: Database session
        job_id: Associated job ID
        archive_path: Path to the archive file
        extraction_result: Result of extraction (None if blocked)
        safeguard_violations: List of safeguard violations detected
        compressed_size: Size of compressed archive in bytes
        estimated_uncompressed: Estimated uncompressed size (from pre-check)
        member_count: Number of members in archive
    
    Returns:
        Created ArchiveExtractionAudit record
    """
    archive_type = _determine_archive_type(archive_path)
    status, blocked_reason = _determine_guardrail_status(safeguard_violations)

    # Calculate decompression ratio if we have both sizes
    decompression_ratio = None
    actual_uncompressed = estimated_uncompressed
    if extraction_result:
        actual_uncompressed = extraction_result.total_size_bytes
        member_count = len(extraction_result.files)

    if actual_uncompressed and compressed_size > 0:
        decompression_ratio = actual_uncompressed / compressed_size

    # Create partial members list for audit trail
    partial_members = []
    if extraction_result:
        partial_members = [
            {
                "path": f.original_path,
                "size_bytes": f.size_bytes,
            }
            for f in extraction_result.files[:100]  # Limit to first 100 for storage
        ]

    audit = ArchiveExtractionAudit(
        id=uuid.uuid4(),
        job_id=job_id,
        source_filename=archive_path.name,
        archive_type=archive_type,
        member_count=member_count,
        compressed_size_bytes=compressed_size,
        estimated_uncompressed_bytes=actual_uncompressed,
        decompression_ratio=decompression_ratio,
        guardrail_status=status,
        blocked_reason=blocked_reason,
        partial_members=partial_members,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )

    session.add(audit)
    await session.commit()
    await session.refresh(audit)

    return audit


async def get_extraction_audit(
    session: AsyncSession,
    job_id: uuid.UUID,
) -> Optional[ArchiveExtractionAudit]:
    """Retrieve extraction audit record for a job.
    
    Args:
        session: Database session
        job_id: Job ID to look up
    
    Returns:
        ArchiveExtractionAudit record or None if not found
    """
    result = await session.execute(
        select(ArchiveExtractionAudit).where(ArchiveExtractionAudit.job_id == job_id)
    )
    return result.scalar_one_or_none()


def create_audit_from_extraction(
    job_id: uuid.UUID,
    archive_path: Path,
    extraction_result: ExtractionResult,
    safeguard_violations: Optional[List[SafeguardViolation]] = None,
) -> dict:
    """Create audit data dict from extraction result (for immediate use).
    
    This is a synchronous helper for creating audit data without DB access.
    Use record_extraction_audit() for persisting to database.
    
    Args:
        job_id: Associated job ID
        archive_path: Path to archive
        extraction_result: Extraction result
        safeguard_violations: Optional safeguard violations
    
    Returns:
        Dict containing audit information
    """
    violations = safeguard_violations or []
    archive_type = _determine_archive_type(archive_path)
    status, blocked_reason = _determine_guardrail_status(violations)

    compressed_size = archive_path.stat().st_size if archive_path.exists() else 0
    decompression_ratio = None
    if compressed_size > 0:
        decompression_ratio = extraction_result.total_size_bytes / compressed_size

    return {
        "job_id": str(job_id),
        "source_filename": archive_path.name,
        "archive_type": archive_type,
        "member_count": len(extraction_result.files),
        "compressed_size_bytes": compressed_size,
        "estimated_uncompressed_bytes": extraction_result.total_size_bytes,
        "decompression_ratio": float(decompression_ratio) if decompression_ratio else None,
        "guardrail_status": status,
        "blocked_reason": blocked_reason,
        "warnings": extraction_result.warnings,
        "duration_seconds": extraction_result.duration_seconds,
    }
