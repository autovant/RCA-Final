"""Tests for watcher timeline and pattern functionality."""

import asyncio
from datetime import datetime, timedelta
import pytest

from core.watchers.timeline import (
    WatcherTimeline,
    WatcherEvent,
    TimelineStats,
    get_watcher_timeline,
)
from core.watchers.patterns import (
    PatternTester,
    PatternTestResult,
    PatternType,
    WatcherPreset,
    PresetRegistry,
    get_preset_registry,
)


class TestWatcherTimeline:
    """Test suite for WatcherTimeline."""
    
    @pytest.fixture
    async def timeline(self):
        """Create a timeline instance for testing."""
        timeline = WatcherTimeline(max_history=100, retention_hours=1)
        await timeline.start()
        yield timeline
        await timeline.stop()
        await timeline.clear()
    
    @pytest.mark.asyncio
    async def test_record_event(self, timeline):
        """Test recording events."""
        event = WatcherEvent(
            event_type="created",
            path="/test/file.log",
            timestamp=datetime.utcnow(),
            pattern_matched="*.log",
            status="completed",
        )
        
        await timeline.record_event(event)
        
        events = await timeline.get_events(limit=10)
        assert len(events) == 1
        assert events[0].path == "/test/file.log"
    
    @pytest.mark.asyncio
    async def test_event_filtering(self, timeline):
        """Test filtering events by various criteria."""
        now = datetime.utcnow()
        
        # Record multiple events
        for i in range(5):
            event = WatcherEvent(
                event_type="created" if i % 2 == 0 else "modified",
                path=f"/test/file{i}.log",
                timestamp=now - timedelta(minutes=i),
                pattern_matched="*.log",
                status="completed",
            )
            await timeline.record_event(event)
        
        # Filter by type
        created_events = await timeline.get_events(event_type="created")
        assert len(created_events) == 3
        
        # Filter by pattern
        log_events = await timeline.get_events(pattern="*.log")
        assert len(log_events) == 5
        
        # Filter by time
        recent_events = await timeline.get_events(
            since=now - timedelta(minutes=2)
        )
        assert len(recent_events) == 3
    
    @pytest.mark.asyncio
    async def test_timeline_stats(self, timeline):
        """Test statistics collection."""
        # Record events
        for i in range(10):
            event = WatcherEvent(
                event_type="created",
                path=f"/test/file{i}.log",
                timestamp=datetime.utcnow(),
                duration_ms=100.0 + i * 10,
                status="completed",
            )
            await timeline.record_event(event)
        
        stats = await timeline.get_stats()
        
        assert stats.total_events == 10
        assert stats.events_by_type["created"] == 10
        assert stats.events_by_status["completed"] == 10
        assert stats.avg_processing_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_timeline_view(self, timeline):
        """Test bucketed timeline view."""
        now = datetime.utcnow()
        
        # Record events over time
        for i in range(20):
            event = WatcherEvent(
                event_type="created",
                path=f"/test/file{i}.log",
                timestamp=now - timedelta(minutes=i * 5),
                status="completed",
            )
            await timeline.record_event(event)
        
        view = await timeline.get_timeline_view(interval_minutes=5, hours=2)
        
        assert len(view) > 0
        assert "timestamp" in view[0]
        assert "count" in view[0]
        assert "by_type" in view[0]
    
    @pytest.mark.asyncio
    async def test_event_subscription(self, timeline):
        """Test real-time event subscription."""
        queue = await timeline.subscribe()
        
        # Record an event
        event = WatcherEvent(
            event_type="created",
            path="/test/file.log",
            timestamp=datetime.utcnow(),
            status="completed",
        )
        await timeline.record_event(event)
        
        # Should receive event
        received_event = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert received_event.path == "/test/file.log"
        
        await timeline.unsubscribe(queue)


class TestPatternTester:
    """Test suite for PatternTester."""
    
    def test_glob_pattern_match(self):
        """Test glob pattern matching."""
        result = PatternTester.test_pattern(
            "*.log",
            "/test/app.log",
            PatternType.GLOB
        )
        assert result.matches is True
        
        result = PatternTester.test_pattern(
            "*.log",
            "/test/app.txt",
            PatternType.GLOB
        )
        assert result.matches is False
    
    def test_regex_pattern_match(self):
        """Test regex pattern matching."""
        result = PatternTester.test_pattern(
            r"file_\d+\.log",
            "/test/file_123.log",
            PatternType.REGEX
        )
        assert result.matches is True
        assert result.match_details is not None
    
    def test_extension_pattern_match(self):
        """Test extension-based matching."""
        result = PatternTester.test_pattern(
            ".csv",
            "/data/report.csv",
            PatternType.EXTENSION
        )
        assert result.matches is True
        
        result = PatternTester.test_pattern(
            "csv",  # Without dot
            "/data/report.csv",
            PatternType.EXTENSION
        )
        assert result.matches is True
    
    def test_prefix_pattern_match(self):
        """Test prefix matching."""
        result = PatternTester.test_pattern(
            "/data/",
            "/data/file.log",
            PatternType.PREFIX
        )
        assert result.matches is True
    
    def test_suffix_pattern_match(self):
        """Test suffix matching."""
        result = PatternTester.test_pattern(
            "_report.xlsx",
            "/test/sales_report.xlsx",
            PatternType.SUFFIX
        )
        assert result.matches is True
    
    def test_multiple_paths(self):
        """Test pattern against multiple paths."""
        paths = [
            "/test/file1.log",
            "/test/file2.log",
            "/test/file3.txt",
        ]
        
        results = PatternTester.test_multiple_paths(
            "*.log",
            paths,
            PatternType.GLOB
        )
        
        assert len(results) == 3
        assert results[0].matches is True
        assert results[1].matches is True
        assert results[2].matches is False
    
    def test_pattern_validation(self):
        """Test pattern validation."""
        # Valid glob
        result = PatternTester.validate_pattern("*.log", PatternType.GLOB)
        assert result["valid"] is True
        
        # Invalid regex
        result = PatternTester.validate_pattern("[invalid", PatternType.REGEX)
        assert result["valid"] is False
        assert len(result["errors"]) > 0


class TestPresetRegistry:
    """Test suite for PresetRegistry."""
    
    @pytest.fixture
    def registry(self):
        """Create a preset registry for testing."""
        return PresetRegistry()
    
    def test_get_builtin_preset(self, registry):
        """Test getting built-in presets."""
        logs_preset = registry.get_preset("logs")
        assert logs_preset is not None
        assert logs_preset.name == "logs"
        assert "*.log" in logs_preset.patterns
    
    def test_list_presets(self, registry):
        """Test listing presets."""
        all_presets = registry.list_presets()
        assert len(all_presets) > 0
        
        # Filter by category
        data_presets = registry.list_presets(category="data")
        assert len(data_presets) > 0
    
    def test_register_custom_preset(self, registry):
        """Test registering custom preset."""
        custom = WatcherPreset(
            name="custom_test",
            description="Test preset",
            patterns=["*.test"],
            pattern_type=PatternType.GLOB,
        )
        
        registry.register_preset(custom)
        
        retrieved = registry.get_preset("custom_test")
        assert retrieved is not None
        assert retrieved.name == "custom_test"
    
    def test_unregister_preset(self, registry):
        """Test unregistering custom preset."""
        custom = WatcherPreset(
            name="temp_preset",
            description="Temporary",
            patterns=["*.tmp"],
        )
        
        registry.register_preset(custom)
        assert registry.get_preset("temp_preset") is not None
        
        success = registry.unregister_preset("temp_preset")
        assert success is True
        assert registry.get_preset("temp_preset") is None
    
    def test_preset_to_config(self, registry):
        """Test converting preset to configuration."""
        logs_preset = registry.get_preset("logs")
        config = logs_preset.to_config()
        
        assert "patterns" in config
        assert "pattern_type" in config
        assert "processor" in config
        assert config["metadata"]["preset"] == "logs"
    
    def test_get_categories(self, registry):
        """Test getting available categories."""
        categories = registry.get_categories()
        assert "logs" in categories
        assert "data" in categories


class TestGlobalSingletons:
    """Test global singleton accessors."""
    
    def test_get_watcher_timeline(self):
        """Test global timeline accessor."""
        timeline1 = get_watcher_timeline()
        timeline2 = get_watcher_timeline()
        assert timeline1 is timeline2
    
    def test_get_preset_registry(self):
        """Test global registry accessor."""
        registry1 = get_preset_registry()
        registry2 = get_preset_registry()
        assert registry1 is registry2
