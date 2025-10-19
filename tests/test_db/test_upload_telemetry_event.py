"""Validation tests for UploadTelemetryEventRecord."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from core.db.models import UploadTelemetryEventRecord


def test_duration_must_be_non_negative():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        UploadTelemetryEventRecord(
            tenant_id=uuid4(),
            job_id=None,
            upload_id=uuid4(),
            stage="ingest",
            feature_flags=[],
            status="success",
            duration_ms=-1,
            started_at=now,
            completed_at=now,
            metadata={},
        )


def test_completed_at_must_not_precede_started_at():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        UploadTelemetryEventRecord(
            tenant_id=uuid4(),
            job_id=None,
            upload_id=uuid4(),
            stage="ingest",
            feature_flags=[],
            status="success",
            duration_ms=100,
            started_at=now,
            completed_at=now - timedelta(seconds=1),
            metadata={},
        )


def test_metadata_accepts_dict():
    now = datetime.now(timezone.utc)
    payload = {
        "warnings": ["skipped"],
        "skipped_count": 2,
    }
    event = UploadTelemetryEventRecord(
        tenant_id=uuid4(),
        job_id=None,
        upload_id=uuid4(),
        stage="ingest",
        feature_flags=["telemetry"],
        status="partial",
        duration_ms=1200,
        started_at=now,
        completed_at=now + timedelta(milliseconds=1200),
        metadata=payload,
    )
    assert event.metadata == payload


def test_metadata_must_be_dict():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        UploadTelemetryEventRecord(
            tenant_id=uuid4(),
            job_id=None,
            upload_id=uuid4(),
            stage="ingest",
            feature_flags=[],
            status="success",
            duration_ms=100,
            started_at=now,
            completed_at=now,
            metadata=["invalid"],
        )