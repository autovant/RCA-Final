"""Tests for RCA output rendering utilities."""

import uuid
from typing import Any, cast

import pytest

try:
    from core.db.models import Job
    from core.jobs.processor import FileSummary, JobProcessor
    from core.privacy import PiiRedactor
    from core.watchers.service import WatcherService
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency guard
    pytest.skip(f"SQLAlchemy not installed: {exc}", allow_module_level=True)


def _make_summary() -> FileSummary:
    return FileSummary(
        file_id="file-1",
        filename="error.log",
        checksum="deadbeef",
        file_size=1024,
        content_type="text/plain",
        line_count=42,
        error_count=3,
        warning_count=1,
        critical_count=0,
        info_count=38,
        sample_head=["ERROR failed to connect", "WARN retrying"],
        sample_tail=["INFO recovered service"],
        top_keywords=["error", "failed", "retrying"],
        chunk_count=1,
    )


def test_render_outputs_generates_expected_sections():
    """Ensure Markdown/HTML/JSON bundles are produced by the processor."""
    from datetime import datetime, timezone, timedelta
    
    job = Job(
        job_type="rca_analysis",
        user_id="tester",
        input_manifest={},
        provider="openai",
        model="gpt-4o",
    )
    job_ref = cast(Any, job)
    job_ref.id = uuid.uuid4()
    job_ref.ticketing = {"platform": "jira"}

    # Set timestamps for timeline testing
    job_ref.created_at = datetime.now(timezone.utc) - timedelta(seconds=60)
    job_ref.started_at = datetime.now(timezone.utc) - timedelta(seconds=45)
    job_ref.completed_at = datetime.now(timezone.utc)

    metrics = {
        "files": 1,
        "lines": 42,
        "errors": 3,
        "warnings": 1,
        "critical": 0,
        "chunks": 1,
    }

    processor = JobProcessor()
    primary_cause = "Database connection pool exhaustion during peak load."
    llm_summary = f"""
## Executive Summary
Authentication service outage triggered by database saturation.

## Root Cause Analysis
### Primary Root Cause
{primary_cause}
### Contributing Factors
1. Connection leak in UserService.authenticate() method
2. Missing connection timeout configuration
### Evidence
- 347 instances of \"Cannot get connection from pool\"
- Errors peaked at 14:30 UTC
### Impact Assessment
- Severity: Critical outage
- Scope: Authentication service
- Duration: 15 minutes
- Business Impact: Complete login failure

## Recommended Actions
- Immediate: Increase connection pool size to 200.
- Urgent: Restart application nodes with staggered rollout.
- Follow-up: Audit database connection handling for leaks.
""".strip()
    fingerprint_payload = {
        "session_id": str(job.id),
        "tenant_id": "workspace-123",
        "summary_text": "Previous RCA determined database connection exhaustion as root cause.",
        "relevance_threshold": 0.72,
        "visibility_scope": "multi_tenant",
        "fingerprint_status": "available",
        "embedding_present": True,
        "safeguard_notes": {"policy": "Cross-workspace review requires manager approval."},
    }

    related_payload = {
        "audit_token": "audit-token-123",
        "source_workspace_id": "workspace-456",
        "results": [
            {
                "session_id": "3e5d9a4d-e2f1-4e4d-bd13-a0f54b7e8e5d",
                "tenant_id": "workspace-123",
                "relevance": 0.91,
                "summary": "Database saturation triggered cascading service retries.",
                "detected_platform": "uipath",
                "fingerprint_status": "available",
                "occurred_at": "2025-02-15T12:34:00Z",
                "safeguards": ["requires-approval"],
            },
            {
                "session_id": "20794af7-bf80-4fda-9a5d-1e5d3d1d79c9",
                "tenant_id": "workspace-789",
                "relevance": 0.67,
                "summary": "Intermittent network outage impacted same downstream system.",
                "detected_platform": "appian",
                "fingerprint_status": "available",
                "occurred_at": "2025-01-22T08:12:00Z",
                "safeguards": ["notify-security", "requires-approval"],
            },
        ],
    }

    outputs = processor._render_outputs(  # pylint: disable=protected-access
        job,
        metrics,
        [ _make_summary() ],
        {"summary": llm_summary, "provider": "test", "model": "mock"},
        mode="rca_analysis",
        fingerprint=fingerprint_payload,
        related_incidents=related_payload,
    )

    assert "markdown" in outputs
    assert "html" in outputs
    assert "json" in outputs

    json_bundle = outputs["json"]
    assert json_bundle["severity"] == "high"
    assert json_bundle["analysis_type"] == "rca_analysis"
    assert json_bundle["recommended_actions"]
    assert "Increase connection pool size" in outputs["markdown"]
    assert "PII Protection" in outputs["markdown"]
    assert "pii_protection" in json_bundle
    assert json_bundle["pii_protection"]["files_sanitised"] == 0

    # Root cause enrichment
    assert "## 🎯 Root Cause Analysis" in outputs["markdown"]
    assert json_bundle["root_cause_analysis"]["primary_root_cause"] == primary_cause
    assert json_bundle["root_cause_analysis"]["contributing_factors"]
    assert json_bundle["root_cause_analysis"]["contributing_factors"][0].startswith("Connection leak")
    assert "Root Cause Analysis" in outputs["html"]

    # Fingerprint enrichment
    assert json_bundle["fingerprint"]
    assert json_bundle["fingerprint"]["fingerprint_status"] == "available"
    assert "Incident Fingerprint" in outputs["markdown"]
    assert "🧬" in outputs["html"]

    # Related incidents enrichment
    assert json_bundle["related_incidents"]["summary"]["count"] == 2
    assert json_bundle["related_incidents"]["display_subset"]
    assert json_bundle["executive_summary"]["related_matches"] == 2
    assert "Related Incident Signals" in outputs["markdown"]
    assert "🧩" in outputs["html"]
    
    # Test new enhancements
    # Executive Summary
    assert "## 📝 Executive Summary" in outputs["markdown"]
    assert "executive_summary" in json_bundle
    assert "severity_level" in json_bundle["executive_summary"]
    assert json_bundle["executive_summary"]["severity_level"] == "high"
    
    # Timeline
    assert "timeline" in json_bundle
    assert "created_at" in json_bundle["timeline"]
    assert "duration_seconds" in json_bundle["timeline"]
    
    # Action Priorities
    assert "action_priorities" in json_bundle
    assert "high_priority" in json_bundle["action_priorities"]
    assert "standard_priority" in json_bundle["action_priorities"]
    
    # Enhanced PII Protection
    assert "security_guarantee" in json_bundle["pii_protection"]
    assert "compliance" in json_bundle["pii_protection"]
    assert "GDPR" in json_bundle["pii_protection"]["compliance"]
    
    # HTML enhancements
    assert "<!DOCTYPE html>" in outputs["html"]
    assert "--fluent-blue-500" in outputs["html"]  # Fluent Design CSS variables
    assert "severity-" in outputs["html"]  # Severity class
    assert "Executive Summary" in outputs["html"]
    assert "linear-gradient" in outputs["html"]  # Gradient styling
    
    # Markdown enhancements
    assert "🔴" in outputs["markdown"] or "🟠" in outputs["markdown"] or "🟡" in outputs["markdown"] or "🟢" in outputs["markdown"]
    assert "Analysis Metadata" in outputs["markdown"]
    assert "Root Cause Analysis Report" in outputs["markdown"]


def test_watcher_service_normalises_iterables():
    """Verify watcher configuration helper coerces inputs into lists."""
    assert WatcherService._normalise_list("path") == ["path"]
    assert WatcherService._normalise_list({"a", "b"}) == ["a", "b"] or ["b", "a"]
    assert WatcherService._normalise_list(None) is None


def test_pii_redactor_redacts_email():
    """Ensure email addresses are redacted when the feature is enabled."""
    redactor = PiiRedactor(
        enabled=True,
        patterns=["email::[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+"],
        replacement="[MASKED]",
    )
    result = redactor.redact("Contact me via jane.doe@example.com for details.")
    assert result.text == "Contact me via [MASKED] for details."
    assert result.replacements == {"email": 1}


def test_pii_redactor_disabled():
    """When disabled the redactor should return the original text."""
    redactor = PiiRedactor(enabled=False)
    text = "Sensitive: 123-45-6789"
    result = redactor.redact(text)
    assert result.text == text
    assert result.replacements == {}
