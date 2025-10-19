"""Helpers for publishing worker telemetry and job events."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import ValidationError

from core.jobs.models import IncidentFingerprintDTO
from core.jobs.service import JobService
from core.logging import get_logger
from core.metrics.collectors import observe_fingerprint_status
from core.metrics.models import FingerprintMetricEvent

logger = get_logger(__name__)


def _count_safeguard_notes(notes: Optional[Dict[str, Any]]) -> int:
    if not isinstance(notes, dict):
        return 0

    total = 0
    for value in notes.values():
        if isinstance(value, list):
            total += len([item for item in value if item is not None])
        elif value is not None:
            total += 1
    return total


async def emit_fingerprint_status(
    job_service: JobService,
    job_id: str,
    fingerprint_payload: Optional[Dict[str, Any]],
    *,
    job_type: str,
) -> None:
    """Publish job events and metrics describing fingerprint lifecycle state."""

    if not fingerprint_payload:
        return

    try:
        dto = IncidentFingerprintDTO.model_validate(fingerprint_payload)
    except ValidationError:
        logger.warning(
            "Skipping fingerprint telemetry due to invalid payload",
            extra={"job_id": job_id},
        )
        return

    await job_service.create_job_event(
        job_id,
        "fingerprint-status",
        {
            "status": dto.fingerprint_status.value,
            "visibility_scope": dto.visibility_scope.value,
            "embedding_present": dto.embedding_present,
            "tenant_id": dto.tenant_id,
            "safeguard_notes": dto.safeguard_notes,
        },
    )

    observe_fingerprint_status(
        FingerprintMetricEvent(
            tenant_id=dto.tenant_id,
            job_type=job_type,
            status=dto.fingerprint_status.value,
            visibility_scope=dto.visibility_scope.value,
            embedding_present=dto.embedding_present,
            safeguard_note_count=_count_safeguard_notes(dto.safeguard_notes),
        )
    )


__all__ = ["emit_fingerprint_status"]
