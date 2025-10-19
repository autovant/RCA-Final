import pytest
from fastapi import HTTPException

from apps.api.routers import jobs as jobs_router


class _FakeFingerprint:
    def __init__(self, session_id: str):
        self._payload = {
            "session_id": session_id,
            "tenant_id": "3fbb72a3-5a0c-4e19-b665-382e8df1ad9c",
            "fingerprint_status": "available",
            "visibility_scope": "multi_tenant",
            "summary_text": "Example summary",
            "relevance_threshold": 0.42,
            "safeguard_notes": {"notes": ["ok"]},
            "created_at": "2024-08-31T12:00:00+00:00",
            "updated_at": "2024-08-31T12:05:00+00:00",
        }
        self.embedding_vector = [0.1, 0.2]

    def to_dict(self):  # pragma: no cover - trivially exercised
        return self._payload


class _FingerprintServiceStub:
    def __init__(self, fingerprint):
        self._fingerprint = fingerprint

    async def get_job_fingerprint(self, job_id: str):  # pragma: no cover - simple stub
        return self._fingerprint


@pytest.mark.asyncio
async def test_get_job_fingerprint_returns_payload(monkeypatch):
    fingerprint = _FakeFingerprint("7d7f7651-a5a9-40f5-b3a3-5f51051d6a0e")
    service = _FingerprintServiceStub(fingerprint)
    monkeypatch.setattr(jobs_router, "job_service", service)

    response = await jobs_router.get_job_fingerprint("7d7f7651-a5a9-40f5-b3a3-5f51051d6a0e")

    assert response.job_id == "7d7f7651-a5a9-40f5-b3a3-5f51051d6a0e"
    assert response.tenant_id == "3fbb72a3-5a0c-4e19-b665-382e8df1ad9c"
    assert response.fingerprint_status == "available"
    assert response.visibility_scope == "multi_tenant"
    assert response.summary_text == "Example summary"
    assert response.relevance_threshold == pytest.approx(0.42)
    assert response.safeguard_notes == {"notes": ["ok"]}
    assert response.embedding_present is True
    assert response.created_at == "2024-08-31T12:00:00+00:00"
    assert response.updated_at == "2024-08-31T12:05:00+00:00"


class _FingerprintServiceMissingStub:
    async def get_job_fingerprint(self, job_id: str):  # pragma: no cover - simple stub
        return None


@pytest.mark.asyncio
async def test_get_job_fingerprint_missing_returns_404(monkeypatch):
    monkeypatch.setattr(jobs_router, "job_service", _FingerprintServiceMissingStub())

    with pytest.raises(HTTPException) as exc:
        await jobs_router.get_job_fingerprint("non-existent")

    assert exc.value.status_code == 404
    assert "Fingerprint not found" in exc.value.detail

