"""Feature flag definitions and helpers for pipeline enhancements."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, MutableMapping, Optional


@dataclass(frozen=True)
class FeatureFlagDefinition:
    """Describes a feature flag including its default state."""

    key: str
    description: str
    default: bool = False


TELEMETRY_ENHANCED_METRICS = FeatureFlagDefinition(
    key="telemetry_enhanced_metrics_enabled",
    description="Exposes expanded ingest/chunk/embed/cache/storage metrics for Prometheus.",
    default=False,
)

COMPRESSED_INGESTION = FeatureFlagDefinition(
    key="compressed_ingestion_enabled",
    description="Enables .gz/.zip archive extraction during file ingest.",
    default=False,
)


class FeatureFlagSet:
    """Mutable collection of feature flags with default fallbacks."""

    def __init__(
        self,
        definitions: Iterable[FeatureFlagDefinition],
        overrides: Optional[Mapping[str, bool]] = None,
    ) -> None:
        base: Dict[str, bool] = {definition.key: definition.default for definition in definitions}
        if overrides:
            base.update({key: bool(value) for key, value in overrides.items()})
        self._values: MutableMapping[str, bool] = base

    def is_enabled(self, key: str) -> bool:
        """Return the resolved state for the supplied feature flag key."""
        return bool(self._values.get(key, False))

    def enable(self, key: str) -> None:
        """Enable a feature flag for the current set."""
        self._values[key] = True

    def disable(self, key: str) -> None:
        """Disable a feature flag for the current set."""
        self._values[key] = False

    def as_dict(self) -> Dict[str, bool]:
        """Return a copy of the internal mapping."""
        return dict(self._values)


ALL_FEATURE_FLAGS: tuple[FeatureFlagDefinition, ...] = (
    TELEMETRY_ENHANCED_METRICS,
    COMPRESSED_INGESTION,
)


__all__ = [
    "FeatureFlagDefinition",
    "FeatureFlagSet",
    "TELEMETRY_ENHANCED_METRICS",
    "COMPRESSED_INGESTION",
    "ALL_FEATURE_FLAGS",
]
