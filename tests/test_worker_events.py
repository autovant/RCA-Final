"""Tests for worker event telemetry helpers."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, cast

import pytest

from apps.worker.events import emit_fingerprint_status


class _StubJobService:
    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []

    async def create_job_event(
        self,
        job_id: str,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
        *,
        session=None,
    ) -> None:
        self.events.append({
            "job_id": job_id,
            "event_type": event_type,
            "data": data or {},
        })


@pytest.mark.asyncio
async def test_emit_fingerprint_status_emits_event_and_metrics(monkeypatch):
    job_service = _StubJobService()
    captured = {}

    def _capture_metric(event) -> None:
        captured["event"] = event

    monkeypatch.setattr("apps.worker.events.observe_fingerprint_status", _capture_metric)

    payload = {
        "session_id": "job-123",
        "tenant_id": "tenant-xyz",
        "summary_text": "Summary text",
        "relevance_threshold": 0.7,
        "visibility_scope": "multi_tenant",
        "fingerprint_status": "available",
        "safeguard_notes": {"fingerprint": ["ok"]},
        "embedding_present": True,
    }

    await emit_fingerprint_status(
        cast(Any, job_service),
        "job-123",
        payload,
        job_type="rca_analysis",
    )

    assert len(job_service.events) == 1
    recorded = job_service.events[0]
    assert recorded["job_id"] == "job-123"
    assert recorded["event_type"] == "fingerprint-status"
    assert recorded["data"]["status"] == "available"
    assert recorded["data"]["visibility_scope"] == "multi_tenant"
    assert captured["event"].status == "available"
    assert captured["event"].embedding_present is True
    assert captured["event"].safeguard_note_count == 1


@pytest.mark.asyncio
async def test_emit_fingerprint_status_ignores_empty_payload(monkeypatch):
    job_service = _StubJobService()
    called = {"metrics": False}

    def _capture_metric(event) -> None:
        called["metrics"] = True

    monkeypatch.setattr("apps.worker.events.observe_fingerprint_status", _capture_metric)

    await emit_fingerprint_status(
        cast(Any, job_service),
        "job-456",
        None,
        job_type="rca_analysis",
    )

    assert job_service.events == []
    assert called["metrics"] is False
