"""Domain primitives for upload telemetry emission and persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping, Optional

from pydantic import BaseModel, Field, ValidationInfo, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models import UploadTelemetryEventRecord


_MAX_DETAIL_ITEMS = 20
_MAX_DETAIL_LENGTH = 256
_METADATA_MAX_ITEMS = 25
_METADATA_MAX_NESTED_ITEMS = 10
_METADATA_MAX_DEPTH = 4
_METADATA_MAX_STRING = 512


def _normalise_detail_items(values: Iterable[Any]) -> List[str]:
    """Sanitise detail values for telemetry metadata."""

    normalised: List[str] = []
    seen: set[str] = set()
    for item in values:
        if item is None:
            continue
        text = str(item).strip()
        if not text:
            continue
        if len(text) > _MAX_DETAIL_LENGTH:
            text = f"{text[: _MAX_DETAIL_LENGTH - 3]}..."
        if text in seen:
            continue
        seen.add(text)
        normalised.append(text)
    return normalised


def coerce_metadata_value(value: Any, *, depth: int = 0) -> Any:
    """Normalise complex metadata into JSON-serialisable structures."""

    if depth >= _METADATA_MAX_DEPTH:
        return "..."

    if value is None or isinstance(value, (bool, int, float)):
        return value

    if isinstance(value, str):
        text = value.strip()
        return text[:_METADATA_MAX_STRING] if len(text) > _METADATA_MAX_STRING else text

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, uuid.UUID):
        return str(value)

    if isinstance(value, Mapping):
        items: Dict[str, Any] = {}
        for index, (raw_key, raw_value) in enumerate(value.items()):
            if index >= _METADATA_MAX_NESTED_ITEMS:
                items["__truncated__"] = True
                break
            key = str(raw_key)[:_METADATA_MAX_STRING]
            items[key] = coerce_metadata_value(raw_value, depth=depth + 1)
        return items

    if isinstance(value, (list, tuple, set)):
        sequence: List[Any] = []
        for index, item in enumerate(value):
            if index >= _METADATA_MAX_NESTED_ITEMS:
                sequence.append("...")
                break
            sequence.append(coerce_metadata_value(item, depth=depth + 1))
        return sequence

    return str(value)[:_METADATA_MAX_STRING]


def sanitise_metadata(metadata: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """Clamp nested telemetry metadata to predictable bounds."""

    if not metadata:
        return {}

    cleaned: Dict[str, Any] = {}
    for index, (raw_key, value) in enumerate(metadata.items()):
        if value is None:
            continue
        if index >= _METADATA_MAX_ITEMS:
            cleaned["__truncated__"] = True
            break
        key = str(raw_key)[:_METADATA_MAX_STRING]
        cleaned[key] = coerce_metadata_value(value, depth=0)
    return cleaned


@dataclass(slots=True)
class PartialUploadTelemetry:
    """Helper for constructing structured metadata for partial uploads."""

    skipped_items: Iterable[Any] = field(default_factory=tuple)
    warnings: Iterable[Any] = field(default_factory=tuple)
    reason: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    max_items: int = _MAX_DETAIL_ITEMS

    def apply(self, base_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Merge the partial upload details into telemetry metadata."""

        metadata: Dict[str, Any] = dict(base_metadata or {})
        for key, value in self.extra.items():
            if value is not None:
                metadata[key] = value

        skipped_all = _normalise_detail_items(self.skipped_items)
        warnings_all = _normalise_detail_items(self.warnings)

        metadata["skipped_count"] = len(skipped_all)
        if skipped_all:
            metadata["skipped_items"] = skipped_all[: self.max_items]

        metadata["warning_count"] = len(warnings_all)
        if warnings_all:
            metadata["warnings"] = warnings_all[: self.max_items]

        if self.reason:
            reason = str(self.reason).strip()
            if reason:
                metadata["partial_reason"] = (
                    reason[: _MAX_DETAIL_LENGTH]
                    if len(reason) > _MAX_DETAIL_LENGTH
                    else reason
                )

        return metadata

class PipelineStage(str, Enum):
    """Enumerates the pipeline stages we surface in telemetry."""

    INGEST = "ingest"
    CHUNK = "chunk"
    EMBED = "embed"
    CACHE = "cache"
    STORAGE = "storage"


class PipelineStatus(str, Enum):
    """Normalised status values for telemetry emission."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class UploadTelemetryEvent(BaseModel):
    """Validated payload persisted via the telemetry pipeline."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    tenant_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    upload_id: uuid.UUID
    stage: PipelineStage
    feature_flags: List[str] = Field(default_factory=list)
    status: PipelineStatus
    duration_ms: int
    started_at: datetime
    completed_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {uuid.UUID: str}

    @field_validator("duration_ms")
    def _validate_duration(cls, value: int) -> int:
        if value < 0:
            raise ValueError("duration_ms must be non-negative")
        return value

    @field_validator("completed_at")
    def _validate_completed_at(
        cls,
        value: datetime,
        info: ValidationInfo,
    ) -> datetime:
        start: Optional[datetime] = info.data.get("started_at")
        if start and value < start:
            raise ValueError("completed_at must be greater than or equal to started_at")
        return value

    @field_validator("metadata")
    def _validate_metadata(
        cls,
        value: Dict[str, Any],
        info: ValidationInfo,
    ) -> Dict[str, Any]:
        status = info.data.get("status")
        if status == PipelineStatus.PARTIAL and "skipped_count" not in (value or {}):
            raise ValueError(
                "metadata.skipped_count must be present when status is partial",
            )
        return value

    def feature_flag_label(self) -> str:
        """Provide a normalised value suitable for metrics labelling."""
        if not self.feature_flags:
            return "none"
        cleaned = sorted(flag.strip().lower() for flag in self.feature_flags if flag)
        return "|".join(cleaned) or "none"

    def to_record(self) -> Dict[str, Any]:
        """Convert the telemetry event into a dict for ORM persistence."""
        payload = self.dict()
        payload["feature_flags"] = sorted(
            {flag.strip().lower() for flag in self.feature_flags if flag}
        )
        return payload

    def derive_size_bytes(self) -> Optional[int]:
        """Read size information from metadata when available."""
        size_value = self.metadata.get("size_bytes")
        if isinstance(size_value, int) and size_value >= 0:
            return size_value
        return None

    def all_feature_flags(self, additional: Optional[Iterable[str]] = None) -> List[str]:
        """Combine the event's feature flags with optional extra flags."""
        result = list(self.feature_flags)
        if additional:
            result.extend(flag for flag in additional if flag)
        return result


async def persist_upload_telemetry_event(
    session: AsyncSession,
    event: UploadTelemetryEvent,
) -> UploadTelemetryEventRecord:
    """Persist a telemetry event using the supplied session."""
    record = UploadTelemetryEventRecord(**event.to_record())
    session.add(record)
    await session.flush()
    await session.refresh(record)
    return record


__all__ = [
    "PartialUploadTelemetry",
    "PipelineStage",
    "PipelineStatus",
    "UploadTelemetryEvent",
    "coerce_metadata_value",
    "persist_upload_telemetry_event",
    "sanitise_metadata",
]
