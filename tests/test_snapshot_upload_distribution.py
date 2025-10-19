"""Tests for the upload distribution snapshot script."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import pytest

from scripts.pipeline.snapshot_upload_distribution import (
    FileTypeSnapshot,
    SnapshotPayload,
    UploadSample,
    compute_file_type_stats,
    render_snapshot,
)


@pytest.fixture
def samples() -> list[UploadSample]:
    return [
        UploadSample(extension="log", size_bytes=1_000),
        UploadSample(extension="log", size_bytes=2_000),
        UploadSample(extension="txt", size_bytes=500),
        UploadSample(extension="txt", size_bytes=3_000),
        UploadSample(extension="txt", size_bytes=7_000),
    ]


def test_compute_file_type_stats_orders_by_count(samples: list[UploadSample]) -> None:
    total, stats = compute_file_type_stats(samples, limit=5)

    assert total == 5
    assert [item.extension for item in stats] == ["txt", "log"]

    txt = stats[0]
    assert txt.count == 3
    assert txt.p50_size_bytes == 3_000
    assert txt.p95_size_bytes >= txt.p50_size_bytes
    assert txt.average_size_bytes == pytest.approx(3500.0, rel=1e-3)


def test_compute_file_type_stats_limits_results(samples: list[UploadSample]) -> None:
    _, stats = compute_file_type_stats(samples, limit=1)
    assert len(stats) == 1


def test_render_snapshot_produces_serialisable_payload(samples: list[UploadSample]) -> None:
    total, file_types = compute_file_type_stats(samples, limit=5)
    tenant_id = UUID("12345678-1234-5678-1234-567812345678")
    payload = render_snapshot(
        total,
        file_types,
        tenant_ids=[tenant_id],
        start=datetime(2025, 10, 10, 12, 0, 0),
        end=datetime(2025, 10, 14, 12, 0, 0),
    )

    assert isinstance(payload, SnapshotPayload)
    assert payload.tenant_scope == str(tenant_id)
    serialised = payload.to_dict()
    assert serialised["total_uploads"] == 5
    assert len(serialised["file_types"]) == 2


def test_compute_file_type_stats_handles_empty_input() -> None:
    total, stats = compute_file_type_stats([], limit=5)
    assert total == 0
    assert stats == []
