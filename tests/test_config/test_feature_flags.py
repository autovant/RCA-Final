"""Unit tests for feature flag definitions and helper set class."""

from __future__ import annotations

from core.config.feature_flags import (
    ALL_FEATURE_FLAGS,
    COMPRESSED_INGESTION,
    FeatureFlagSet,
    TELEMETRY_ENHANCED_METRICS,
)


def test_all_feature_flags_default_false():
    flags = FeatureFlagSet(ALL_FEATURE_FLAGS)
    assert not flags.is_enabled(TELEMETRY_ENHANCED_METRICS.key)
    assert not flags.is_enabled(COMPRESSED_INGESTION.key)


def test_overrides_enable_flags():
    overrides = {
        TELEMETRY_ENHANCED_METRICS.key: True,
        COMPRESSED_INGESTION.key: True,
    }
    flags = FeatureFlagSet(ALL_FEATURE_FLAGS, overrides=overrides)
    assert flags.is_enabled(TELEMETRY_ENHANCED_METRICS.key)
    assert flags.is_enabled(COMPRESSED_INGESTION.key)
    # unrelated keys default to False
    assert not flags.is_enabled("nonexistent_flag")
