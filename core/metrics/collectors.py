"""Prometheus metric collectors for ingestion intelligence features."""

from __future__ import annotations

from typing import Dict

from prometheus_client import Counter, Histogram

from core.metrics import registry

from .models import (
    ArchiveGuardrailMetricEvent,
    DetectionMetricEvent,
    FingerprintMetricEvent,
    RelatedIncidentMetricEvent,
)


_DETECTION_OUTCOME_COUNTER = Counter(
    "rca_platform_detection_total",
    "Count of platform detection attempts grouped by outcome and parser execution state.",
    (
        "tenant_id",
        "platform",
        "outcome",
        "parser_executed",
        "detection_method",
        "feature_flags",
    ),
    registry=registry,
)

_DETECTION_CONFIDENCE = Histogram(
    "rca_platform_detection_confidence",
    "Distribution of detection confidence scores (0-1 range).",
    (
        "tenant_id",
        "platform",
        "detection_method",
    ),
    buckets=(0.1, 0.25, 0.5, 0.75, 0.9, 0.99, 1.0),
    registry=registry,
)

_DETECTION_DURATION = Histogram(
    "rca_platform_detection_duration_seconds",
    "Time spent evaluating platform detection heuristics/parsers.",
    (
        "tenant_id",
        "platform",
        "detection_method",
    ),
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
    registry=registry,
)

_ARCHIVE_GUARDRAIL_COUNTER = Counter(
    "rca_archive_guardrail_total",
    "Archive extraction guardrail outcomes by status and archive type.",
    (
        "tenant_id",
        "archive_type",
        "status",
        "feature_flags",
        "blocked_reason",
    ),
    registry=registry,
)

_ARCHIVE_DECOMPRESSION_RATIO = Histogram(
    "rca_archive_decompression_ratio",
    "Observed decompression ratios for processed archives.",
    (
        "tenant_id",
        "archive_type",
        "status",
    ),
    buckets=(1.0, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0),
    registry=registry,
)

_ARCHIVE_MEMBER_COUNT = Histogram(
    "rca_archive_member_count",
    "Member counts observed during archive extraction.",
    (
        "tenant_id",
        "archive_type",
        "status",
    ),
    buckets=(1, 5, 10, 25, 50, 100, 250, 500, 1000),
    registry=registry,
)

_RELATED_INCIDENT_RESPONSE_COUNTER = Counter(
    "rca_related_incident_responses_total",
    "Related incident API responses grouped by scope, channel, and audit state.",
    (
        "source_workspace_id",
        "scope",
        "channel",
        "platform_filter",
        "audit_token",
    ),
    registry=registry,
)

_RELATED_INCIDENT_RESULT_COUNT = Histogram(
    "rca_related_incident_results",
    "Distribution of related incident match counts returned to analysts.",
    (
        "source_workspace_id",
        "scope",
        "channel",
    ),
    buckets=(0, 1, 2, 3, 5, 10, 20, 50),
    registry=registry,
)

_RELATED_INCIDENT_CROSS_WORKSPACE = Histogram(
    "rca_related_incident_cross_workspace_matches",
    "Count of cross-workspace matches returned in related incident responses.",
    (
        "source_workspace_id",
        "scope",
        "channel",
    ),
    buckets=(0, 1, 2, 3, 5, 10, 20, 50),
    registry=registry,
)


def _bounded(value: float, minimum: float = 0.0) -> float:
    return max(value, minimum)


_FINGERPRINT_STATUS_COUNTER = Counter(
    "rca_fingerprint_status_total",
    "Fingerprint lifecycle outcomes grouped by job type and visibility scope.",
    (
        "tenant_id",
        "job_type",
        "status",
        "visibility_scope",
        "embedding_present",
    ),
    registry=registry,
)

_FINGERPRINT_GUARDRAIL_COUNT = Histogram(
    "rca_fingerprint_safeguard_notes",
    "Distribution of safeguard note counts recorded alongside fingerprint indexing outcomes.",
    (
        "tenant_id",
        "job_type",
        "status",
        "visibility_scope",
        "embedding_present",
    ),
    buckets=(0, 1, 2, 3, 5, 10, 20),
    registry=registry,
)


def observe_detection(event: DetectionMetricEvent) -> None:
    """Record metrics for a single platform detection attempt."""

    labels: Dict[str, str] = event.metric_labels()
    _DETECTION_OUTCOME_COUNTER.labels(**labels).inc()

    confidence_labels = {
        "tenant_id": labels["tenant_id"],
        "platform": labels["platform"],
        "detection_method": labels["detection_method"],
    }
    _DETECTION_CONFIDENCE.labels(**confidence_labels).observe(_bounded(event.confidence, 0.0))

    if event.duration_seconds is not None:
        _DETECTION_DURATION.labels(**confidence_labels).observe(
            _bounded(event.duration_seconds, 0.0)
        )


def observe_archive_guardrail(event: ArchiveGuardrailMetricEvent) -> None:
    """Record metrics for archive extraction guardrail evaluation."""

    labels = event.metric_labels()
    _ARCHIVE_GUARDRAIL_COUNTER.labels(**labels).inc()

    histogram_labels = {
        "tenant_id": labels["tenant_id"],
        "archive_type": labels["archive_type"],
        "status": labels["status"],
    }
    if event.decompression_ratio is not None:
        _ARCHIVE_DECOMPRESSION_RATIO.labels(**histogram_labels).observe(
            _bounded(event.decompression_ratio, 0.0)
        )
    if event.member_count is not None:
        _ARCHIVE_MEMBER_COUNT.labels(**histogram_labels).observe(
            float(_bounded(event.member_count, 0.0))
        )


def observe_related_incident_response(event: RelatedIncidentMetricEvent) -> None:
    """Record metrics describing related incident API responses."""

    counter_labels = event.counter_labels()
    _RELATED_INCIDENT_RESPONSE_COUNTER.labels(**counter_labels).inc()

    histogram_labels = event.histogram_labels()
    _RELATED_INCIDENT_RESULT_COUNT.labels(**histogram_labels).observe(
        float(_bounded(event.result_count, 0.0))
    )
    _RELATED_INCIDENT_CROSS_WORKSPACE.labels(**histogram_labels).observe(
        float(_bounded(event.cross_workspace_count, 0.0))
    )


def observe_fingerprint_status(event: FingerprintMetricEvent) -> None:
    """Record metrics describing fingerprint indexing results."""

    labels = event.metric_labels()
    _FINGERPRINT_STATUS_COUNTER.labels(**labels).inc()
    _FINGERPRINT_GUARDRAIL_COUNT.labels(**labels).observe(
        float(_bounded(event.safeguard_note_count, 0.0))
    )


__all__ = [
    "observe_detection",
    "observe_archive_guardrail",
    "observe_related_incident_response",
    "observe_fingerprint_status",
]
