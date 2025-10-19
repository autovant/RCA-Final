"""Unit tests for pipeline metrics helper wrappers."""

from __future__ import annotations

from typing import Dict

import pytest

from core.metrics import registry as metrics_registry
from core.metrics.pipeline_metrics import PipelineMetricsCollector, PipelineStageMetrics, StageLabels


def _get_sample(metric_name: str, labels: Dict[str, str]) -> float:
    value = metrics_registry.get_sample_value(metric_name, labels=labels)
    return float(value) if value is not None else 0.0


def test_stage_labels_to_kwargs() -> None:
    labels = StageLabels(
        tenant_id="tenant-123",
        stage="ingest",
        platform="worker",
        file_type="pdf",
        size_category="medium",
        status="success",
        feature_flags="telemetry|cache",
    )

    assert labels.to_kwargs() == {
        "tenant_id": "tenant-123",
        "stage": "ingest",
        "platform": "worker",
        "file_type": "pdf",
        "size_category": "medium",
        "status": "success",
        "feature_flags": "telemetry|cache",
    }


def test_observe_records_counter_and_histogram() -> None:
    metrics = PipelineStageMetrics("ingest")
    labels = {
        "tenant_id": "tenant-observe",
        "stage": "ingest",
        "platform": "worker",
        "file_type": "pdf",
        "size_category": "medium",
        "status": "success",
        "feature_flags": "cache|telemetry_enhanced",
    }

    before_count = _get_sample("rca_pipeline_stage_total", labels)
    before_hist_count = _get_sample("rca_pipeline_stage_duration_seconds_count", labels)
    before_hist_sum = _get_sample("rca_pipeline_stage_duration_seconds_sum", labels)

    metrics.observe(
        tenant_id="tenant-observe",
        status="success",
        duration_seconds=2.5,
        platform="worker",
        file_type="pdf",
        size_bytes=3 * 1024 * 1024,
        feature_flags=["Telemetry_Enhanced", "cache"],
    )

    assert _get_sample("rca_pipeline_stage_total", labels) == pytest.approx(before_count + 1.0)
    assert _get_sample("rca_pipeline_stage_duration_seconds_count", labels) == pytest.approx(before_hist_count + 1.0)
    assert _get_sample("rca_pipeline_stage_duration_seconds_sum", labels) >= before_hist_sum


def test_observe_normalises_optional_fields() -> None:
    metrics = PipelineStageMetrics("chunk")
    labels = {
        "tenant_id": "tenant-normalise",
        "stage": "chunk",
        "platform": "generic",
        "file_type": "unknown",
        "size_category": "xlarge",
        "status": "unknown",
        "feature_flags": "none",
    }

    before = _get_sample("rca_pipeline_stage_total", labels)

    metrics.observe(
        tenant_id="tenant-normalise",
        status="",
        duration_seconds=0.0,
        feature_flags=None,
        size_bytes=None,
    )

    assert _get_sample("rca_pipeline_stage_total", labels) == pytest.approx(before + 1.0)


def test_track_context_manager_records_duration_and_status_override() -> None:
    collector = PipelineMetricsCollector().embed
    labels = {
        "tenant_id": "tenant-track-success",
        "stage": "embed",
        "platform": "generic",
        "file_type": "txt",
        "size_category": "small",
        "status": "partial",
        "feature_flags": "telemetry",
    }

    before = _get_sample("rca_pipeline_stage_total", labels)

    with collector.track(
        tenant_id="tenant-track-success",
        file_type="txt",
        size_bytes=200 * 1024,
        feature_flags=["Telemetry"],
    ) as timer:
        timer.status("partial")

    assert _get_sample("rca_pipeline_stage_total", labels) == pytest.approx(before + 1.0)
    assert _get_sample("rca_pipeline_stage_duration_seconds_count", labels) >= 1.0


def test_track_records_failure_on_exception() -> None:
    collector = PipelineStageMetrics("storage")
    labels = {
        "tenant_id": "tenant-track-failure",
        "stage": "storage",
        "platform": "generic",
        "file_type": "csv",
        "size_category": "large",
        "status": "failed",
        "feature_flags": "none",
    }

    before = _get_sample("rca_pipeline_stage_total", labels)

    with pytest.raises(RuntimeError):
        with collector.track(
            tenant_id="tenant-track-failure",
            file_type="csv",
            size_bytes=10 * 1024 * 1024,
        ):
            raise RuntimeError("boom")

    assert _get_sample("rca_pipeline_stage_total", labels) == pytest.approx(before + 1.0)