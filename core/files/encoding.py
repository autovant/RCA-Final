"""Utilities for detecting and validating text file encodings."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
from typing import Iterable, List

import chardet

PrintableChars = set(range(32, 127)) | {9, 10, 13}
_MAX_SAMPLE_BYTES = 512 * 1024
_DEFAULT_CONFIDENCE_THRESHOLD = 0.75
_DEFAULT_PRINTABLE_THRESHOLD = 0.75


class EncodingProbeError(RuntimeError):
    """Raised when a file fails encoding validation during smoke tests."""


@dataclass(frozen=True)
class TextProbe:
    """Represents the analysed state of a text file."""

    path: Path
    text: str
    encoding: str
    confidence: float
    printable_ratio: float
    warnings: List[str] = field(default_factory=list)


def probe_text_file(
    path: Path | str,
    *,
    min_confidence: float = _DEFAULT_CONFIDENCE_THRESHOLD,
    min_printable_ratio: float = _DEFAULT_PRINTABLE_THRESHOLD,
) -> TextProbe:
    """Detect encoding and validate textual content for the supplied file."""

    file_path = Path(path)
    if not file_path.exists():
        raise EncodingProbeError(f"File not found: {file_path}")

    data = file_path.read_bytes()
    if not data:
        raise EncodingProbeError(f"File {file_path} is empty")

    sample = data[:_MAX_SAMPLE_BYTES]
    detection = chardet.detect(sample)
    encoding = (detection.get("encoding") or "utf-8").lower()
    confidence = float(detection.get("confidence") or 0.0)
    warnings: List[str] = []

    if confidence < min_confidence:
        warnings.append(
            f"low-confidence:{encoding}:{confidence:.2f}"
        )

    try:
        text = data.decode(encoding)
    except (LookupError, UnicodeDecodeError):
        try:
            text = data.decode("utf-8")
            warnings.append("fallback:utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError as exc:
            try:
                text = data.decode("latin-1", errors="ignore")
                warnings.append("fallback:latin-1-ignore")
                encoding = "latin-1"
            except Exception as fallback_exc:  # pragma: no cover - unexpected path
                raise EncodingProbeError(
                    f"Unable to decode file {file_path}: {exc}"
                ) from fallback_exc

    printable_ratio = _compute_printable_ratio(text)
    if printable_ratio < min_printable_ratio:
        warnings.append(f"low-printable:{printable_ratio:.2f}")

    if any(entry.startswith("low-printable") for entry in warnings):
        raise EncodingProbeError(
            f"File {file_path} failed printable ratio check"
        )

    return TextProbe(
        path=file_path,
        text=text,
        encoding=encoding,
        confidence=confidence,
        printable_ratio=printable_ratio,
        warnings=warnings,
    )


def _compute_printable_ratio(text: str) -> float:
    if not text:
        return 0.0

    printable = sum(1 for char in text if ord(char) in PrintableChars)
    return printable / len(text)
