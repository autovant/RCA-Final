"""Smoke test helpers for encoding validation."""

from __future__ import annotations

from typing import Iterable

from core.files.encoding import TextProbe


def assert_text_probe(
    probe: TextProbe,
    *,
    min_confidence: float = 0.75,
    min_printable_ratio: float = 0.75,
) -> None:
    """Fail the smoke test early when the probe contains warnings."""

    failures: list[str] = []

    if probe.confidence < min_confidence:
        failures.append(
            f"detected encoding '{probe.encoding}' below confidence threshold "
            f"({probe.confidence:.2f} < {min_confidence:.2f})"
        )

    if probe.printable_ratio < min_printable_ratio:
        failures.append(
            f"printable ratio {probe.printable_ratio:.2f} below {min_printable_ratio:.2f}"
        )

    warnings = list(_normalise_strings(probe.warnings))
    if warnings:
        failures.extend(f"warning: {message}" for message in warnings)

    if failures:
        joined = "; ".join(failures)
        raise AssertionError(f"Encoding probe validation failed: {joined}")


def _normalise_strings(values: Iterable[str]) -> Iterable[str]:
    for value in values:
        if value:
            yield value.strip()
