"""Heuristic platform detection orchestration for ingestion flows."""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from core.config import settings
from core.jobs.models import PlatformDetectionOutcome
from core.files.platforms import ParserResult, get_parser_for_platform

_SUPPORTED_PLATFORMS: Tuple[str, ...] = (
    "blue_prism",
    "uipath",
    "appian",
    "automation_anywhere",
    "pega",
)

_PLATFORM_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "blue_prism": (
        "blue prism",
        "bpserver",
        "work queue",
        "process studio",
        "session log",
    ),
    "uipath": (
        "uipath",
        "orchestrator",
        "robot executor",
        "robotics core",
        "xaml",
    ),
    "appian": (
        "appian",
        "smart service",
        "process model",
        "tempo",
        "sail",
    ),
    "automation_anywhere": (
        "automation anywhere",
        "control room",
        "bot runner",
        "metabot",
        "aatask",
    ),
    "pega": (
        "pega",
        "prpc",
        "ruleset",
        "autonomic event",
        "pega platform",
    ),
}

_PLATFORM_EXTENSION_HINTS: Dict[str, Tuple[str, ...]] = {
    "uipath": ("xaml",),
    "blue_prism": ("bprelease", "bprest", "bpa"),
}

_PLATFORM_METADATA_HINTS: Dict[str, Tuple[str, ...]] = {
    "blue_prism": ("blueprism", "blue prism"),
    "uipath": ("uipath",),
    "appian": ("appian",),
    "automation_anywhere": ("automation anywhere", "a2019"),
    "pega": ("pega", "prpc"),
}

_KEYWORD_WEIGHT = 0.3
_FILENAME_WEIGHT = 0.15
_METADATA_WEIGHT = 0.2
_EXTENSION_WEIGHT = 0.1
_KEYWORD_CAP = 0.6
_DEFAULT_MIN_CONFIDENCE = 0.15
_DEFAULT_ROLLOUT_CONFIDENCE = 0.65
_DEFAULT_CAPTURE_FLAGS = True


@dataclass(frozen=True)
class DetectionInput:
    """Signal extracted from an uploaded artefact."""

    name: str
    content: str
    content_type: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def normalised_name(self) -> str:
        return self.name.lower()

    def normalised_content(self) -> str:
        return self.content.lower()

    def normalised_metadata_values(self) -> List[str]:
        values: List[str] = []
        for value in self.metadata.values():
            if value is None:
                continue
            text = str(value).strip().lower()
            if text:
                values.append(text)
        return values

    def extension(self) -> Optional[str]:
        suffix = Path(self.name).suffix.lstrip(".").lower()
        return suffix or None


@dataclass(frozen=True)
class _AggregatedSignals:
    corpus: str
    filenames: Tuple[str, ...]
    metadata_values: Tuple[str, ...]
    extensions: Tuple[str, ...]


class PlatformDetectionOrchestrator:
    """Applies heuristic scoring to infer RPA platform signals."""

    def __init__(
        self,
        *,
        enabled: Optional[bool] = None,
        min_confidence: Optional[float] = None,
        rollout_confidence: Optional[float] = None,
        capture_feature_flags: Optional[bool] = None,
        detection_method: str = "heuristic",
    ) -> None:
        self._enabled_override = enabled
        self._min_confidence_override = min_confidence
        self._rollout_confidence_override = rollout_confidence
        self._capture_flags_override = capture_feature_flags
        self._method = detection_method

    def detect(
        self,
        job_id: str,
        inputs: Sequence[DetectionInput],
        *,
        feature_flags: Optional[Mapping[str, bool]] = None,
    ) -> PlatformDetectionOutcome:
        start = time.perf_counter()

        enabled = self._is_enabled()
        capture_flags = self._capture_flags()
        snapshot = self._capture_snapshot(enabled, feature_flags) if capture_flags else {}

        if not enabled or not inputs:
            return PlatformDetectionOutcome(
                job_id=job_id,
                detected_platform="unknown",
                confidence_score=0.0,
                detection_method=self._method,
                parser_executed=False,
                parser_version=None,
                extracted_entities=[],
                feature_flag_snapshot=snapshot,
                duration_ms=self._elapsed_ms(start),
            )

        signals = self._aggregate(inputs)
        best_platform, best_score = self._score_platforms(signals)

        min_conf = self._min_confidence()
        rollout = self._rollout_confidence()

        if best_score < min_conf:
            best_platform = "unknown"

        parser_executed = best_platform != "unknown" and best_score >= rollout
        parser_version = None
        extracted_entities: List[Dict[str, Any]] = []

        # Execute parser if threshold met
        if parser_executed:
            parser_result = self._execute_parser(best_platform, inputs)
            if parser_result is not None:
                parser_executed = parser_result.success
                parser_version = parser_result.parser_version
                extracted_entities = parser_result.extracted_entities

        return PlatformDetectionOutcome(
            job_id=job_id,
            detected_platform=best_platform,
            confidence_score=float(round(best_score, 4)),
            detection_method=self._method,
            parser_executed=parser_executed,
            parser_version=parser_version,
            extracted_entities=extracted_entities,
            feature_flag_snapshot=snapshot,
            duration_ms=self._elapsed_ms(start),
        )

    def _is_enabled(self) -> bool:
        if self._enabled_override is not None:
            return bool(self._enabled_override)
        if hasattr(settings, "PLATFORM_DETECTION_ENABLED"):
            return bool(getattr(settings, "PLATFORM_DETECTION_ENABLED"))
        return True

    def _min_confidence(self) -> float:
        if self._min_confidence_override is not None:
            return self._clamp(self._min_confidence_override)
        value = self._platform_setting("MIN_CONFIDENCE")
        if value is None and hasattr(settings, "PLATFORM_DETECTION_MIN_CONFIDENCE"):
            value = getattr(settings, "PLATFORM_DETECTION_MIN_CONFIDENCE")
        if value is None:
            return _DEFAULT_MIN_CONFIDENCE
        return self._clamp(value)

    def _rollout_confidence(self) -> float:
        if self._rollout_confidence_override is not None:
            return self._clamp(self._rollout_confidence_override)
        value = self._platform_setting("ROLLOUT_CONFIDENCE")
        if value is None and hasattr(settings, "PLATFORM_DETECTION_ROLLOUT_CONFIDENCE"):
            value = getattr(settings, "PLATFORM_DETECTION_ROLLOUT_CONFIDENCE")
        if value is None:
            return _DEFAULT_ROLLOUT_CONFIDENCE
        return self._clamp(value)

    def _capture_flags(self) -> bool:
        if self._capture_flags_override is not None:
            return bool(self._capture_flags_override)
        value = self._platform_setting("CAPTURE_FEATURE_FLAGS")
        if value is None and hasattr(settings, "PLATFORM_DETECTION_CAPTURE_FLAGS"):
            value = getattr(settings, "PLATFORM_DETECTION_CAPTURE_FLAGS")
        if value is None:
            return _DEFAULT_CAPTURE_FLAGS
        return bool(value)

    @staticmethod
    def _elapsed_ms(start: float) -> int:
        elapsed = max((time.perf_counter() - start) * 1000, 0.0)
        value = int(round(elapsed))
        return value if value > 0 else 1

    @staticmethod
    def _clamp(value: Any) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            return _DEFAULT_MIN_CONFIDENCE
        if numeric < 0.0:
            return 0.0
        if numeric > 1.0:
            return 1.0
        return numeric

    @staticmethod
    def _platform_setting(field: str) -> Optional[Any]:
        config = getattr(settings, "platform_detection", None)
        if config is not None and hasattr(config, field):
            return getattr(config, field)
        return None

    def _capture_snapshot(
        self,
        enabled: bool,
        feature_flags: Optional[Mapping[str, bool]] = None,
    ) -> Dict[str, bool]:
        snapshot: MutableMapping[str, bool] = {}
        for key, value in settings.feature_flags.as_dict().items():
            snapshot[str(key)] = bool(value)
        if feature_flags:
            for key, value in feature_flags.items():
                snapshot[str(key)] = bool(value)
        snapshot["platform_detection_enabled"] = bool(enabled)
        return dict(snapshot)

    @staticmethod
    def _aggregate(inputs: Sequence[DetectionInput]) -> _AggregatedSignals:
        content_parts: List[str] = []
        filenames: List[str] = []
        metadata_values: List[str] = []
        extensions: List[str] = []

        for item in inputs:
            filenames.append(item.normalised_name())
            content_parts.append(item.normalised_content())
            metadata_values.extend(item.normalised_metadata_values())
            extension = item.extension()
            if extension:
                extensions.append(extension)

        corpus = "\n".join(part for part in content_parts if part)
        return _AggregatedSignals(
            corpus=corpus,
            filenames=tuple(filenames),
            metadata_values=tuple(metadata_values),
            extensions=tuple(extensions),
        )

    def _score_platforms(self, signals: _AggregatedSignals) -> Tuple[str, float]:
        corpus = signals.corpus
        best_platform = "unknown"
        best_score = 0.0

        for platform in _SUPPORTED_PLATFORMS:
            score = self._score_platform(platform, signals, corpus)
            if score > best_score or (score == best_score and platform < best_platform):
                best_platform = platform
                best_score = score

        if best_score <= 0.0:
            return "unknown", 0.0
        return best_platform, min(best_score, 1.0)

    def _score_platform(
        self,
        platform: str,
        signals: _AggregatedSignals,
        corpus: str,
    ) -> float:
        keywords = _PLATFORM_KEYWORDS.get(platform, ())
        keyword_matches = {
            keyword
            for keyword in keywords
            if keyword and keyword in corpus
        }
        keyword_score = min(len(keyword_matches) * _KEYWORD_WEIGHT, _KEYWORD_CAP)

        filename_score = 0.0
        if keywords and any(keyword in name for keyword in keywords for name in signals.filenames):
            filename_score = _FILENAME_WEIGHT

        metadata_hints = _PLATFORM_METADATA_HINTS.get(platform, ())
        metadata_score = 0.0
        if metadata_hints and any(
            hint in value for hint in metadata_hints for value in signals.metadata_values
        ):
            metadata_score = _METADATA_WEIGHT

        extension_score = 0.0
        ext_hints = _PLATFORM_EXTENSION_HINTS.get(platform, ())
        if ext_hints and any(ext in ext_hints for ext in signals.extensions):
            extension_score = _EXTENSION_WEIGHT

        return keyword_score + filename_score + metadata_score + extension_score

    def _execute_parser(
        self,
        platform: str,
        inputs: Sequence[DetectionInput],
    ) -> Optional[ParserResult]:
        """Execute platform-specific parser on detection inputs."""
        parser = get_parser_for_platform(platform)
        if parser is None:
            return None

        try:
            # Convert DetectionInput to parser file format
            files = [
                {
                    "name": inp.name,
                    "content": inp.content,
                    "metadata": dict(inp.metadata) if inp.metadata else {},
                }
                for inp in inputs
            ]

            # Get parser timeout from settings
            timeout_seconds = None
            if hasattr(settings, "PLATFORM_DETECTION_PARSER_TIMEOUT"):
                timeout_seconds = getattr(settings, "PLATFORM_DETECTION_PARSER_TIMEOUT")
            elif hasattr(settings, "platform_detection"):
                pd_settings = getattr(settings, "platform_detection")
                if hasattr(pd_settings, "PARSER_TIMEOUT"):
                    timeout_seconds = getattr(pd_settings, "PARSER_TIMEOUT")

            return parser.parse(files, timeout_seconds=timeout_seconds)

        except Exception:
            # Parser failures are non-fatal; return None to indicate no execution
            return None


__all__ = [
    "DetectionInput",
    "PlatformDetectionOrchestrator",
]
