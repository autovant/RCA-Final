"""Typed payloads for metrics emission covering detection and archive safeguards."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Optional

__all__ = [
    "DetectionMetricEvent",
    "ArchiveGuardrailMetricEvent",
    "RelatedIncidentMetricEvent",
    "FingerprintMetricEvent",
]


@dataclass(frozen=True)
class DetectionMetricEvent:
    """Metric payload describing platform detection and parser outcomes."""

    tenant_id: str
    platform: str
    outcome: str
    confidence: float
    parser_executed: bool
    detection_method: str
    feature_flags: Mapping[str, bool]
    parser_version: Optional[str] = None
    duration_seconds: Optional[float] = None

    def feature_flag_string(self) -> str:
        flags = sorted(k for k, v in self.feature_flags.items() if v)
        return "|".join(flags) if flags else "none"

    def parser_executed_label(self) -> str:
        return "yes" if self.parser_executed else "no"

    def metric_labels(self) -> dict[str, str]:  # pragma: no cover - deterministic mapping
        return {
            "tenant_id": self.tenant_id,
            "platform": self.platform or "unknown",
            "outcome": self.outcome or "unknown",
            "parser_executed": self.parser_executed_label(),
            "detection_method": self.detection_method or "unspecified",
            "feature_flags": self.feature_flag_string(),
        }


@dataclass(frozen=True)
class ArchiveGuardrailMetricEvent:
    """Metric payload for archive extraction safeguard outcomes."""

    tenant_id: str
    archive_type: str
    status: str
    member_count: int
    decompression_ratio: float
    blocked_reason: Optional[str] = None
    flags: Optional[Iterable[str]] = None

    def feature_flag_string(self) -> str:
        flags = sorted({flag.strip() for flag in self.flags or [] if flag})
        return "|".join(flags) if flags else "none"

    def metric_labels(self) -> dict[str, str]:  # pragma: no cover - deterministic mapping
        return {
            "tenant_id": self.tenant_id,
            "archive_type": self.archive_type or "unknown",
            "status": self.status or "unknown",
            "feature_flags": self.feature_flag_string(),
            "blocked_reason": self.blocked_reason or "none",
        }


@dataclass(frozen=True)
class RelatedIncidentMetricEvent:
    """Metric payload for related incident API responses."""

    source_workspace_id: Optional[str]
    scope: str
    channel: str
    result_count: int
    cross_workspace_count: int
    platform_filter: Optional[str] = None
    audit_token_issued: bool = False

    def _workspace_label(self) -> str:
        return (self.source_workspace_id or "unknown").lower()

    def _scope_label(self) -> str:
        return (self.scope or "unspecified").lower()

    def _channel_label(self) -> str:
        return (self.channel or "unspecified").lower()

    def _platform_label(self) -> str:
        value = (self.platform_filter or "any").strip().lower()
        return value or "any"

    def audit_label(self) -> str:
        return "yes" if self.audit_token_issued else "no"

    def counter_labels(self) -> dict[str, str]:  # pragma: no cover - deterministic mapping
        return {
            "source_workspace_id": self._workspace_label(),
            "scope": self._scope_label(),
            "channel": self._channel_label(),
            "platform_filter": self._platform_label(),
            "audit_token": self.audit_label(),
        }

    def histogram_labels(self) -> dict[str, str]:  # pragma: no cover - deterministic mapping
        return {
            "source_workspace_id": self._workspace_label(),
            "scope": self._scope_label(),
            "channel": self._channel_label(),
        }


@dataclass(frozen=True)
class FingerprintMetricEvent:
    """Metric payload describing fingerprint indexing outcomes."""

    tenant_id: Optional[str]
    job_type: str
    status: str
    visibility_scope: str
    embedding_present: bool
    safeguard_note_count: int = 0

    @staticmethod
    def _normalise(value: Optional[str], default: str) -> str:
        candidate = (value or "").strip().lower()
        return candidate if candidate else default

    def embedding_label(self) -> str:
        return "yes" if self.embedding_present else "no"

    def metric_labels(self) -> dict[str, str]:  # pragma: no cover - deterministic mapping
        return {
            "tenant_id": self._normalise(self.tenant_id, "unknown"),
            "job_type": self._normalise(self.job_type, "unspecified"),
            "status": self._normalise(self.status, "unspecified"),
            "visibility_scope": self._normalise(self.visibility_scope, "unspecified"),
            "embedding_present": self.embedding_label(),
        }
