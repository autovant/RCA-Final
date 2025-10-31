"""Tests for partial upload telemetry helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
import uuid

import pytest

pytest.importorskip("aiofiles")

from core.files.telemetry import (
    PartialUploadTelemetry,
    PipelineStage,
    PipelineStatus,
    UploadTelemetryEvent,
    coerce_metadata_value,
    sanitise_metadata,
)


def test_partial_metadata_merges_and_normalises():
    base_metadata = {"size_bytes": 1024}
    details = PartialUploadTelemetry(
        skipped_items=["unsupported.bin", " encrypted.zip ", "unsupported.bin"],
        warnings=["skipped unsupported file", "", " encryption not supported "],
        reason="unsupported_members",
        extra={"note": "archive contains unsupported entries"},
    )

    metadata = details.apply(base_metadata)

    assert metadata["size_bytes"] == 1024
    assert metadata["skipped_count"] == 2
    assert metadata["skipped_items"] == ["unsupported.bin", "encrypted.zip"]
    assert metadata["warning_count"] == 2
    assert metadata["warnings"] == [
        "skipped unsupported file",
        "encryption not supported",
    ]
    assert metadata["partial_reason"] == "unsupported_members"
    assert metadata["note"] == "archive contains unsupported entries"


def test_partial_metadata_truncates_detail_lists():
    details = PartialUploadTelemetry(
        skipped_items=[f"file-{idx}.txt" for idx in range(30)],
        warnings=[f"warning-{idx}" for idx in range(2)],
    )

    metadata = details.apply()

    assert metadata["skipped_count"] == 30
    assert len(metadata["skipped_items"]) == 20
    assert metadata["skipped_items"][0] == "file-0.txt"
    assert metadata["warning_count"] == 2


def test_partial_metadata_integrates_with_upload_event():
    details = PartialUploadTelemetry(
        skipped_items=["file-1.log"],
        warnings=["unsupported extension"],
        reason="unsupported_members",
    )
    metadata = details.apply()

    event = UploadTelemetryEvent(
        tenant_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        upload_id=uuid.uuid4(),
        stage=PipelineStage.INGEST,
        feature_flags=["test-flag"],
        status=PipelineStatus.PARTIAL,
        duration_ms=15,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        metadata=metadata,
    )

    assert event.metadata["skipped_count"] == 1
    assert event.metadata["skipped_items"] == ["file-1.log"]
    assert event.metadata["warnings"] == ["unsupported extension"]


def test_sanitise_metadata_limits_complex_payloads():
    metadata = {
        "long_text": "x" * 600,
        "numbers": list(range(15)),
        "mapping": {f"key-{idx}": idx for idx in range(12)},
        "custom": SimpleNamespace(name="example"),
        "none_value": None,
    }

    cleaned = sanitise_metadata(metadata)

    assert "none_value" not in cleaned
    assert len(cleaned["long_text"]) == 512
    assert len(cleaned["numbers"]) == 11
    assert cleaned["numbers"][-1] == "..."
    assert cleaned["mapping"]["__truncated__"] is True
    assert cleaned["custom"] == "namespace(name='example')"


def test_coerce_metadata_value_truncates_depth():
    nested = {"inner": {"value": list(range(15))}}

    coerced = coerce_metadata_value(nested)

    assert coerced["inner"]["value"][-1] == "..."
    assert len(coerced["inner"]["value"]) == 11
    assert coerce_metadata_value(SimpleNamespace(flag=True)) == "namespace(flag=True)"
