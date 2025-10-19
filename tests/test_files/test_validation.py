"""Tests for archive extraction policy validation helpers."""

from __future__ import annotations

import pytest

from core.files import extraction, validation


class DummyResult(extraction.ExtractionResult):
    def __init__(self, *, total_size_bytes: int, duration_seconds: float):
        super().__init__(
            destination=extraction.Path("/tmp"),
            files=[],
            total_size_bytes=total_size_bytes,
            duration_seconds=duration_seconds,
            warnings=[],
            _owns_destination=False,
        )


def test_validate_extraction_result_flags_size_and_duration():
    result = DummyResult(total_size_bytes=200, duration_seconds=50)
    policy = validation.ExtractionPolicy(max_total_bytes=100, max_duration_seconds=30)

    violations = validation.validate_extraction_result(result, policy=policy)

    assert {violation.code for violation in violations} == {
        "size_limit_exceeded",
        "duration_exceeded",
    }


@pytest.mark.parametrize(
    "error, expected_code",
    [
        (extraction.ExtractionTimeoutExceeded("boom"), "duration_exceeded"),
        (extraction.ExtractionSizeLimitExceeded("boom"), "size_limit_exceeded"),
        (extraction.UnsupportedArchiveTypeError("boom"), "unsupported_archive"),
        (extraction.ArchiveExtractionError("boom"), "extraction_failed"),
        (RuntimeError("boom"), "extraction_failed"),
    ],
)
def test_map_extraction_error(error, expected_code):
    violation = validation.map_extraction_error(error)
    assert violation.code == expected_code
