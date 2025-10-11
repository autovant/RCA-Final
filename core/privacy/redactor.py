"""Utilities for sanitising sensitive data prior to processing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RedactionResult:
    """Outcome returned by the PII redactor."""

    text: str
    replacements: Dict[str, int]


class PiiRedactor:
    """Apply configurable regex-based redactions to textual content."""

    def __init__(
        self,
        enabled: Optional[bool] = None,
        patterns: Optional[Sequence[str]] = None,
        replacement: Optional[str] = None,
    ) -> None:
        privacy = settings.privacy
        self._enabled = privacy.ENABLE_PII_REDACTION if enabled is None else enabled
        configured_patterns = list(patterns or privacy.PII_REDACTION_PATTERNS)
        self._replacement = (
            replacement if replacement is not None else privacy.PII_REDACTION_REPLACEMENT
        )
        self._compiled_patterns: List[Tuple[str, re.Pattern[str]]] = []
        for index, entry in enumerate(configured_patterns):
            label, pattern = self._parse_entry(entry, index)
            try:
                compiled = re.compile(pattern, flags=re.MULTILINE)
            except re.error as exc:  # pragma: no cover - defensive guard
                logger.warning("Invalid PII pattern '%s': %s", label or pattern, exc)
                continue
            self._compiled_patterns.append((label, compiled))

    @property
    def is_enabled(self) -> bool:
        """Return whether redaction is active."""
        return self._enabled and bool(self._compiled_patterns)

    def redact(self, text: str) -> RedactionResult:
        """Redact PII occurrences from the supplied text."""
        if not self.is_enabled or not text:
            return RedactionResult(text=text, replacements={})

        replacements: Dict[str, int] = {}
        scrubbed = text
        for label, pattern in self._compiled_patterns:
            scrubbed, count = pattern.subn(self._replacement, scrubbed)
            if count:
                replacements[label] = replacements.get(label, 0) + count

        return RedactionResult(text=scrubbed, replacements=replacements)

    @staticmethod
    def _parse_entry(entry: str, index: int) -> Tuple[str, str]:
        raw = entry.strip()
        if not raw:
            return (f"pattern_{index}", "(?!)")  # safe no-op pattern

        if "::" in raw:
            label, pattern = raw.split("::", 1)
            label = label.strip() or f"pattern_{index}"
            pattern = pattern.strip()
        else:
            label = f"pattern_{index}"
            pattern = raw

        return label, pattern
