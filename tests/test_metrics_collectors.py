"""Unit tests for Prometheus metric collectors."""

from __future__ import annotations

from typing import Dict

import pytest
from prometheus_client import CollectorRegistry, Counter, Histogram

from core.metrics import collectors
from core.metrics.models import (
    ArchiveGuardrailMetricEvent,
    DetectionMetricEvent,
    FingerprintMetricEvent,
    RelatedIncidentMetricEvent,
)


def _setup_detection_registry(monkeypatch) -> CollectorRegistry:
    registry = CollectorRegistry()
    monkeypatch.setattr(
        collectors,
        "_DETECTION_OUTCOME_COUNTER",
        Counter(
            "rca_platform_detection_total",
            "test",
            (
                "tenant_id",
                "platform",
                "outcome",
                "parser_executed",
                "detection_method",
                "feature_flags",
            ),
            registry=registry,
        ),
        raising=False,
    )
    monkeypatch.setattr(
        collectors,
        "_DETECTION_CONFIDENCE",
        Histogram(
            "rca_platform_detection_confidence",
            "test",
            ("tenant_id", "platform", "detection_method"),
            registry=registry,
        ),
        raising=False,
    )
    monkeypatch.setattr(
        collectors,
        "_DETECTION_DURATION",
        Histogram(
            "rca_platform_detection_duration_seconds",
            "test",
            ("tenant_id", "platform", "detection_method"),
            registry=registry,
        ),
        raising=False,
    )
    return registry


def _setup_archive_registry(monkeypatch) -> CollectorRegistry:
    registry = CollectorRegistry()
    monkeypatch.setattr(
        collectors,
        "_ARCHIVE_GUARDRAIL_COUNTER",
        Counter(
            "rca_archive_guardrail_total",
            "test",
            (
                "tenant_id",
                "archive_type",
                "status",
                "feature_flags",
                "blocked_reason",
            ),
            registry=registry,
        ),
        raising=False,
    )
    monkeypatch.setattr(
        collectors,
        "_ARCHIVE_DECOMPRESSION_RATIO",
        Histogram(
            "rca_archive_decompression_ratio",
            "test",
            ("tenant_id", "archive_type", "status"),
            registry=registry,
        ),
        raising=False,
    )
    monkeypatch.setattr(
        collectors,
        "_ARCHIVE_MEMBER_COUNT",
        Histogram(
            "rca_archive_member_count",
            "test",
            ("tenant_id", "archive_type", "status"),
            registry=registry,
        ),
        raising=False,
    )
    return registry


def _setup_related_registry(monkeypatch) -> CollectorRegistry:
    registry = CollectorRegistry()
    monkeypatch.setattr(
        collectors,
        "_RELATED_INCIDENT_RESPONSE_COUNTER",
        Counter(
            "rca_related_incident_responses_total",
            "test",
            (
                "source_workspace_id",
                "scope",
                "channel",
                "platform_filter",
                "audit_token",
            ),
            registry=registry,
        ),
        raising=False,
    )
    monkeypatch.setattr(
        collectors,
        "_RELATED_INCIDENT_RESULT_COUNT",
        Histogram(
            "rca_related_incident_results",
            "test",
            (
                "source_workspace_id",
                "scope",
                "channel",
            ),
            registry=registry,
        ),
        raising=False,
    )
    monkeypatch.setattr(
        collectors,
        "_RELATED_INCIDENT_CROSS_WORKSPACE",
        Histogram(
            "rca_related_incident_cross_workspace_matches",
            "test",
            (
                "source_workspace_id",
                "scope",
                "channel",
            ),
            registry=registry,
        ),
        raising=False,
    )
    return registry


def _setup_fingerprint_registry(monkeypatch) -> CollectorRegistry:
    registry = CollectorRegistry()
    monkeypatch.setattr(
        collectors,
        "_FINGERPRINT_STATUS_COUNTER",
        Counter(
            "rca_fingerprint_status_total",
            "test",
            (
                "tenant_id",
                "job_type",
                "status",
                "visibility_scope",
                "embedding_present",
            ),
            registry=registry,
        ),
        raising=False,
    )
    monkeypatch.setattr(
        collectors,
        "_FINGERPRINT_GUARDRAIL_COUNT",
        Histogram(
            "rca_fingerprint_safeguard_notes",
            "test",
            (
                "tenant_id",
                "job_type",
                "status",
                "visibility_scope",
                "embedding_present",
            ),
            registry=registry,
        ),
        raising=False,
    )
    return registry


@pytest.mark.parametrize("parser_executed", [True, False])
def test_observe_detection_records_metrics(monkeypatch, parser_executed):
    registry = _setup_detection_registry(monkeypatch)

    event = DetectionMetricEvent(
        tenant_id="tenant-a",
        platform="uipath",
        outcome="success",
        confidence=0.87,
        parser_executed=parser_executed,
        detection_method="heuristic",
        feature_flags={"flag_a": True, "flag_b": False},
        duration_seconds=1.25 if parser_executed else None,
    )

    collectors.observe_detection(event)

    labels: Dict[str, str] = {
        "tenant_id": "tenant-a",
        "platform": "uipath",
        "outcome": "success",
        "parser_executed": "yes" if parser_executed else "no",
        "detection_method": "heuristic",
        "feature_flags": "flag_a",
    }

    counter_samples = collectors._DETECTION_OUTCOME_COUNTER.collect()[0].samples  # type: ignore[attr-defined]
    assert any(sample.value == 1.0 and sample.labels == labels for sample in counter_samples)

    histogram_samples = collectors._DETECTION_CONFIDENCE.collect()[0].samples  # type: ignore[attr-defined]
    confidence_sum_sample = next(
        sample for sample in histogram_samples if sample.name.endswith("_sum")
    )
    confidence_count_sample = next(
        sample for sample in histogram_samples if sample.name.endswith("_count")
    )
    assert confidence_sum_sample.value == pytest.approx(0.87)
    assert confidence_count_sample.value == 1.0

    duration_samples = collectors._DETECTION_DURATION.collect()[0].samples  # type: ignore[attr-defined]
    if parser_executed:
        duration_sum_sample = next(sample for sample in duration_samples if sample.name.endswith("_sum"))
        duration_count_sample = next(sample for sample in duration_samples if sample.name.endswith("_count"))
        assert duration_sum_sample.value == pytest.approx(1.25)
        assert duration_count_sample.value == 1.0
    else:
        duration_sum_sample = next(
            (sample for sample in duration_samples if sample.name.endswith("_sum")),
            None,
        )
        duration_count_sample = next(
            (sample for sample in duration_samples if sample.name.endswith("_count")),
            None,
        )
        if duration_sum_sample is None or duration_count_sample is None:
            assert duration_samples == []
        else:
            assert duration_sum_sample.value == 0.0
            assert duration_count_sample.value == 0.0


def test_observe_archive_guardrail_records_metrics(monkeypatch):
    registry = _setup_archive_registry(monkeypatch)

    event = ArchiveGuardrailMetricEvent(
        tenant_id="tenant-b",
        archive_type="zip",
        status="blocked",
        member_count=42,
        decompression_ratio=12.5,
        blocked_reason="ratio_exceeded",
        flags=["dual-mode", "guard"],
    )

    collectors.observe_archive_guardrail(event)

    labels = {
        "tenant_id": "tenant-b",
        "archive_type": "zip",
        "status": "blocked",
        "feature_flags": "dual-mode|guard",
        "blocked_reason": "ratio_exceeded",
    }
    guardrail_samples = collectors._ARCHIVE_GUARDRAIL_COUNTER.collect()[0].samples  # type: ignore[attr-defined]
    assert any(sample.value == 1.0 and sample.labels == labels for sample in guardrail_samples)

    ratio_samples = collectors._ARCHIVE_DECOMPRESSION_RATIO.collect()[0].samples  # type: ignore[attr-defined]
    ratio_sum = next(sample for sample in ratio_samples if sample.name.endswith("_sum"))
    ratio_count = next(sample for sample in ratio_samples if sample.name.endswith("_count"))
    assert ratio_sum.value == pytest.approx(12.5)
    assert ratio_count.value == 1.0

    member_samples = collectors._ARCHIVE_MEMBER_COUNT.collect()[0].samples  # type: ignore[attr-defined]
    member_sum = next(sample for sample in member_samples if sample.name.endswith("_sum"))
    member_count = next(sample for sample in member_samples if sample.name.endswith("_count"))
    assert member_sum.value == pytest.approx(42.0)
    assert member_count.value == 1.0


def test_observe_related_incident_response_records_metrics(monkeypatch):
    registry = _setup_related_registry(monkeypatch)

    event = RelatedIncidentMetricEvent(
        source_workspace_id="workspace-a",
        scope="authorized_workspaces",
        channel="session",
        result_count=5,
        cross_workspace_count=2,
        platform_filter="uipath",
        audit_token_issued=True,
    )

    collectors.observe_related_incident_response(event)

    counter_samples = collectors._RELATED_INCIDENT_RESPONSE_COUNTER.collect()[0].samples  # type: ignore[attr-defined]
    expected_counter_labels = {
        "source_workspace_id": "workspace-a",
        "scope": "authorized_workspaces",
        "channel": "session",
        "platform_filter": "uipath",
        "audit_token": "yes",
    }
    assert any(sample.value == 1.0 and sample.labels == expected_counter_labels for sample in counter_samples)

    result_samples = collectors._RELATED_INCIDENT_RESULT_COUNT.collect()[0].samples  # type: ignore[attr-defined]
    result_sum = next(sample for sample in result_samples if sample.name.endswith("_sum"))
    result_count = next(sample for sample in result_samples if sample.name.endswith("_count"))
    assert result_sum.value == pytest.approx(5.0)
    assert result_count.value == 1.0

    cross_samples = collectors._RELATED_INCIDENT_CROSS_WORKSPACE.collect()[0].samples  # type: ignore[attr-defined]
    cross_sum = next(sample for sample in cross_samples if sample.name.endswith("_sum"))
    cross_count = next(sample for sample in cross_samples if sample.name.endswith("_count"))
    assert cross_sum.value == pytest.approx(2.0)
    assert cross_count.value == 1.0


def test_observe_fingerprint_status_records_metrics(monkeypatch):
    registry = _setup_fingerprint_registry(monkeypatch)

    event = FingerprintMetricEvent(
        tenant_id="tenant-123",
        job_type="rca_analysis",
        status="available",
        visibility_scope="multi_tenant",
        embedding_present=True,
        safeguard_note_count=2,
    )

    collectors.observe_fingerprint_status(event)

    expected = {
        "tenant_id": "tenant-123",
        "job_type": "rca_analysis",
        "status": "available",
        "visibility_scope": "multi_tenant",
        "embedding_present": "yes",
    }

    counter_samples = collectors._FINGERPRINT_STATUS_COUNTER.collect()[0].samples  # type: ignore[attr-defined]
    assert any(sample.value == 1.0 and sample.labels == expected for sample in counter_samples)

    histogram_samples = collectors._FINGERPRINT_GUARDRAIL_COUNT.collect()[0].samples  # type: ignore[attr-defined]
    total_sample = next(sample for sample in histogram_samples if sample.name.endswith("_sum"))
    count_sample = next(sample for sample in histogram_samples if sample.name.endswith("_count"))
    assert total_sample.value == pytest.approx(2.0)
    assert count_sample.value == pytest.approx(1.0)