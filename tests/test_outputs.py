"""Tests for RCA output rendering utilities."""

import uuid

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
    job = Job(
        job_type="rca_analysis",
        user_id="tester",
        input_manifest={},
        provider="openai",
        model="gpt-4o",
    )
    job.id = uuid.uuid4()
    job.ticketing = {"platform": "jira"}

    metrics = {
        "files": 1,
        "lines": 42,
        "errors": 3,
        "warnings": 1,
        "critical": 0,
        "chunks": 1,
    }

    processor = JobProcessor()
    outputs = processor._render_outputs(  # pylint: disable=protected-access
        job,
        metrics,
        [ _make_summary() ],
        {"summary": "- Restart the database service", "provider": "test", "model": "mock"},
        mode="rca_analysis",
    )

    assert "markdown" in outputs
    assert "html" in outputs
    assert "json" in outputs

    json_bundle = outputs["json"]
    assert json_bundle["severity"] == "high"
    assert json_bundle["analysis_type"] == "rca_analysis"
    assert json_bundle["recommended_actions"]
    assert "Restart the database service" in outputs["markdown"]
    assert "PII Protection" in outputs["markdown"]
    assert "pii_protection" in json_bundle
    assert json_bundle["pii_protection"]["files_sanitised"] == 0


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
