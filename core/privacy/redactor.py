"""Utilities for sanitising sensitive data prior to processing."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RedactionResult:
    """Outcome returned by the PII redactor."""

    text: str
    replacements: Dict[str, int]
    validation_passed: bool = True
    validation_warnings: Optional[List[str]] = None
    failsafe_triggered: bool = False

    def __post_init__(self):
        if self.validation_warnings is None:
            self.validation_warnings = []


class PiiRedactor:
    """Apply configurable regex-based redactions to textual content with multi-pass validation."""

    def __init__(
        self,
        enabled: Optional[bool] = None,
        patterns: Optional[Sequence[str]] = None,
        replacement: Optional[str] = None,
        multi_pass: Optional[bool] = None,
        strict_mode: Optional[bool] = None,
        validation_passes: Optional[int] = None,
        fail_closed: Optional[bool] = None,
        block_replacement: Optional[str] = None,
        high_entropy_min_length: Optional[int] = None,
        high_entropy_threshold: Optional[float] = None,
    ) -> None:
        privacy = settings.privacy
        self._enabled = privacy.ENABLE_PII_REDACTION if enabled is None else enabled
        configured_patterns = list(patterns or privacy.PII_REDACTION_PATTERNS)
        self._replacement = (
            replacement if replacement is not None else privacy.PII_REDACTION_REPLACEMENT
        )
        self._multi_pass = (
            multi_pass if multi_pass is not None else privacy.PII_REDACTION_MULTI_PASS
        )
        self._strict_mode = (
            strict_mode if strict_mode is not None else privacy.PII_REDACTION_STRICT_MODE
        )
        passes_from_config = privacy.PII_REDACTION_VALIDATION_PASSES
        self._validation_max_passes = (
            passes_from_config if validation_passes is None else validation_passes
        )
        if self._validation_max_passes < 0:
            self._validation_max_passes = 0
        self._fail_closed = (
            privacy.PII_REDACTION_FAIL_CLOSED if fail_closed is None else fail_closed
        )
        self._block_replacement = (
            privacy.PII_REDACTION_FAILSAFE_REPLACEMENT
            if block_replacement is None
            else block_replacement
        )
        self._high_entropy_min_length = (
            privacy.PII_HIGH_ENTROPY_MIN_LENGTH
            if high_entropy_min_length is None
            else max(1, high_entropy_min_length)
        )
        self._high_entropy_threshold = (
            privacy.PII_HIGH_ENTROPY_THRESHOLD
            if high_entropy_threshold is None
            else max(0.0, high_entropy_threshold)
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

        self._high_entropy_pattern: Optional[re.Pattern[str]] = None
        if self._high_entropy_min_length > 0:
            entropy_pattern = rf"\b[A-Za-z0-9+/=_-]{{{self._high_entropy_min_length},}}\b"
            try:
                self._high_entropy_pattern = re.compile(entropy_pattern)
            except re.error:  # pragma: no cover - defensive guard
                logger.exception(
                    "Invalid high entropy pattern compiled with length %s",
                    self._high_entropy_min_length,
                )
                self._high_entropy_pattern = None

        # Validation patterns to ensure no sensitive data leaked through
        self._validation_patterns = self._build_validation_patterns()

    def _build_validation_patterns(self) -> List[Tuple[str, re.Pattern[str]]]:
        """Build patterns to validate redaction effectiveness."""
        patterns = [
            # High-confidence indicators of leaked secrets
            ("potential_email", re.compile(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}\b")),
            ("potential_aws_key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
            ("potential_jwt", re.compile(r"\beyJ[a-zA-Z0-9_-]{20,}\.")),
            ("potential_api_key", re.compile(r"(?i)(?:key|token|secret)\s*[:=]\s*['\"]?[a-zA-Z0-9\-_]{32,}")),
            ("potential_password", re.compile(r"(?i)password\s*[:=]\s*['\"]?[^\s'\"]{8,}")),
            ("potential_ipv4", re.compile(r"\b(?:10|172\.(?:1[6-9]|2[0-9]|3[01])|192\.168)\.\d{1,3}\.\d{1,3}\b")),
            ("potential_openai_key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
            ("potential_github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
            ("potential_slack_token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}[A-Za-z0-9-]*")),
            ("potential_private_key", re.compile(r"-----BEGIN[\s\w]*PRIVATE KEY-----")),
            ("potential_ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
            ("potential_credit_card", re.compile(r"\b(?:\d[ -]*?){13,16}\b")),
            ("potential_phone", re.compile(r"\b\+?\d[\d\s().-]{7,}\b")),
            ("potential_ipv6", re.compile(r"\b(?:[0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}\b")),
        ]
        if self._high_entropy_pattern is not None:
            patterns.append(("potential_high_entropy", self._high_entropy_pattern))
        for label, compiled in self._compiled_patterns:
            patterns.append((f"configured_{label}", compiled))
        return patterns

    @staticmethod
    def _calculate_entropy(token: str) -> float:
        """Calculate Shannon entropy for a given token."""
        if not token:
            return 0.0
        length = len(token)
        frequency: Dict[str, int] = {}
        for char in token:
            frequency[char] = frequency.get(char, 0) + 1
        entropy = 0.0
        for count in frequency.values():
            probability = count / length
            entropy -= probability * math.log2(probability)
        return entropy

    def _scrub_high_entropy_sequences(
        self,
        text: str,
        replacements: Dict[str, int],
    ) -> Tuple[str, int]:
        """Mask sequences that exhibit high entropy typical of secrets."""
        if self._high_entropy_pattern is None:
            return text, 0

        matches = list(self._high_entropy_pattern.finditer(text))
        if not matches:
            return text, 0

        last_index = 0
        total_replacements = 0
        rebuilt: List[str] = []
        for match in matches:
            start, end = match.span()
            candidate = match.group(0)
            rebuilt.append(text[last_index:start])
            last_index = end

            if candidate in (self._replacement, self._block_replacement):
                rebuilt.append(candidate)
                continue

            entropy_value = self._calculate_entropy(candidate)
            if entropy_value >= self._high_entropy_threshold:
                rebuilt.append(self._replacement)
                total_replacements += 1
            else:
                rebuilt.append(candidate)

        rebuilt.append(text[last_index:])
        if total_replacements:
            replacements["high_entropy"] = replacements.get("high_entropy", 0) + total_replacements
            logger.info(
                "High-entropy redaction masked %d potential secret token(s)",
                total_replacements,
            )
            return "".join(rebuilt), total_replacements

        return text, 0

    def _run_validation(self, text: str) -> List[Tuple[str, re.Pattern[str], int]]:
        """Return validation matches for the supplied text."""
        issues: List[Tuple[str, re.Pattern[str], int]] = []
        for label, pattern in self._validation_patterns:
            matches = pattern.findall(text)
            if matches:
                count = len(matches)
                issues.append((label, pattern, count))
        return issues

    @property
    def is_enabled(self) -> bool:
        """Return whether redaction is active."""
        return self._enabled and bool(self._compiled_patterns)

    def redact(self, text: str) -> RedactionResult:
        """Redact PII occurrences from the supplied text with multi-pass validation."""
        if not self.is_enabled or not text:
            return RedactionResult(text=text, replacements={})

        replacements: Dict[str, int] = {}
        scrubbed = text

        # First pass: Apply all configured patterns
        for label, pattern in self._compiled_patterns:
            scrubbed, count = pattern.subn(self._replacement, scrubbed)
            if count:
                replacements[label] = replacements.get(label, 0) + count

        # Multi-pass: Run again to catch patterns that might have been revealed
        if self._multi_pass and replacements:
            max_passes = 3
            for pass_num in range(2, max_passes + 1):
                additional_found = False
                for label, pattern in self._compiled_patterns:
                    before_count = replacements.get(label, 0)
                    scrubbed, count = pattern.subn(self._replacement, scrubbed)
                    if count:
                        replacements[label] = replacements.get(label, 0) + count
                        additional_found = True
                        logger.info(
                            "Multi-pass redaction (pass %d) found %d additional %s occurrences",
                            pass_num, count, label
                        )
                if not additional_found:
                    break  # No more patterns found, safe to exit

        # Track high entropy sequences that may have been consumed by other patterns
        if self._high_entropy_pattern is not None:
            for match in self._high_entropy_pattern.finditer(text):
                candidate = match.group(0)
                if candidate in (self._replacement, self._block_replacement):
                    continue
                if candidate in scrubbed:
                    continue
                if self._calculate_entropy(candidate) >= self._high_entropy_threshold:
                    replacements["high_entropy"] = replacements.get("high_entropy", 0) + 1

        scrubbed, _ = self._scrub_high_entropy_sequences(scrubbed, replacements)

        # Validation: Check if any sensitive data might have leaked through
        validation_passed = True
        validation_warnings: List[str] = []
        warning_messages: Set[str] = set()
        failsafe_triggered = False
        if self._strict_mode:
            issues = self._run_validation(scrubbed)
            if issues:
                validation_passed = False
            attempt = 0
            while issues and attempt < self._validation_max_passes:
                attempt += 1
                for validator_label, validator_pattern, match_count in issues:
                    if self._validation_max_passes > 0:
                        warning = (
                            f"Validation detected {match_count} potential {validator_label} pattern(s); "
                            f"automatically masking them (pass {attempt}/{self._validation_max_passes})."
                        )
                    else:
                        warning = (
                            f"Validation detected {match_count} potential {validator_label} pattern(s); "
                            "no automatic masking performed (validation passes set to 0)."
                        )
                    if warning not in warning_messages:
                        validation_warnings.append(warning)
                        warning_messages.add(warning)
                        logger.warning(
                            "SECURITY NOTICE: %s", warning
                        )
                    scrubbed, count = validator_pattern.subn(self._replacement, scrubbed)
                    if count:
                        key = f"validation_{validator_label}"
                        replacements[key] = replacements.get(key, 0) + count
                issues = self._run_validation(scrubbed)

            if issues:
                validation_passed = False
                for validator_label, _, match_count in issues:
                    warning = (
                        f"Failsafe triggered: {match_count} potential {validator_label} pattern(s) "
                        f"remain after {self._validation_max_passes} validation pass(es)."
                    )
                    if warning not in warning_messages:
                        validation_warnings.append(warning)
                        warning_messages.add(warning)
                        logger.error("SECURITY BLOCK: %s", warning)
                if self._fail_closed:
                    failsafe_triggered = True
                    scrubbed = self._block_replacement
                    replacements["failsafe_block"] = replacements.get("failsafe_block", 0) + 1
                    if "Failsafe content replacement applied." not in warning_messages:
                        validation_warnings.append("Failsafe content replacement applied.")
                        warning_messages.add("Failsafe content replacement applied.")
                        logger.error("SECURITY BLOCK: Failsafe content replacement applied.")
            else:
                if warning_messages:
                    validation_passed = True

        total_redactions = sum(replacements.values())
        if total_redactions > 0:
            logger.info(
                "Redacted %d sensitive item(s) across %d pattern type(s)%s",
                total_redactions,
                len(replacements),
                " with validation warnings" if validation_warnings else ""
            )

        return RedactionResult(
            text=scrubbed,
            replacements=replacements,
            validation_passed=validation_passed,
            validation_warnings=validation_warnings,
            failsafe_triggered=failsafe_triggered,
        )

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
