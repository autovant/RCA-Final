"""Smoke tests ensuring file ingestion handles diverse encodings."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.files.encoding import EncodingProbeError, TextProbe, probe_text_file
from tests.smoke.harness import assert_text_probe

FIXTURE_DIR = Path(__file__).parent / "files"


@pytest.mark.parametrize(
    ("filename", "expected_phrase", "expected_encodings"),
    [
        ("utf8_sample.log", "UTF-8 sample", {"utf-8", "ascii"}),
        ("utf16le_sample.log", "UTF-16 LE sample", {"utf-16-le", "utf-16"}),
        ("utf16be_sample.log", "UTF-16 BE sample", {"utf-16-be", "utf-16"}),
    ],
)
def test_encoding_probe_decodes_text_samples(
    filename: str,
    expected_phrase: str,
    expected_encodings: set[str],
) -> None:
    probe: TextProbe = probe_text_file(FIXTURE_DIR / filename)

    assert expected_phrase in probe.text

    encoding = probe.encoding.lower().replace("_", "-")
    normalised = encoding.replace("-", "")
    expected_normalised = {value.replace("-", "") for value in expected_encodings}
    assert normalised in expected_normalised

    assert_text_probe(probe)


def test_encoding_probe_rejects_malformed_sample() -> None:
    malformed_path = FIXTURE_DIR / "malformed_sample.bin"
    with pytest.raises(EncodingProbeError):
        probe_text_file(malformed_path)


def test_harness_rejects_low_confidence_probe() -> None:
    probe = TextProbe(
        path=FIXTURE_DIR / "utf8_sample.log",
        text="garbled",
        encoding="utf-8",
        confidence=0.2,
        printable_ratio=0.5,
        warnings=["simulated-warning"],
    )

    with pytest.raises(AssertionError):
        assert_text_probe(probe)
