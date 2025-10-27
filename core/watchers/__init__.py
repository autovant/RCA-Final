"""Watcher subsystem exports."""

from .event_bus import WatcherEventBus, watcher_event_bus
from .processors import WatcherProcessorRegistry, watcher_processor_registry
from .service import WatcherService
from .timeline import WatcherTimeline, WatcherEvent, TimelineStats, get_watcher_timeline
from .patterns import (
    PatternTester,
    PatternTestResult,
    PatternType,
    WatcherPreset,
    PresetRegistry,
    get_preset_registry,
)
from .advanced import (
    WatcherSchedule,
    WebhookTarget,
    StorageBackend,
    LocalStorageBackend,
    S3StorageBackend,
    AzureBlobStorageBackend,
    MultiWatcherConfig,
    CustomProcessorRegistry,
    get_custom_processor_registry,
)

__all__ = [
    # Core
    "WatcherEventBus",
    "watcher_event_bus",
    "WatcherProcessorRegistry",
    "watcher_processor_registry",
    "WatcherService",
    # Timeline & History
    "WatcherTimeline",
    "WatcherEvent",
    "TimelineStats",
    "get_watcher_timeline",
    # Patterns & Presets
    "PatternTester",
    "PatternTestResult",
    "PatternType",
    "WatcherPreset",
    "PresetRegistry",
    "get_preset_registry",
    # Advanced Features
    "WatcherSchedule",
    "WebhookTarget",
    "StorageBackend",
    "LocalStorageBackend",
    "S3StorageBackend",
    "AzureBlobStorageBackend",
    "MultiWatcherConfig",
    "CustomProcessorRegistry",
    "get_custom_processor_registry",
]
