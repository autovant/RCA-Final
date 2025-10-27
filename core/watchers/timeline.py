"""
File watcher timeline and history tracking.

Provides event stream visualization, pattern analysis, and historical statistics
for file watcher activity.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
import statistics

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class WatcherEvent:
    """Structured representation of a watcher event."""
    
    event_type: str  # created, modified, deleted, moved
    path: str
    timestamp: datetime
    size: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    pattern_matched: Optional[str] = None
    processor: Optional[str] = None
    duration_ms: Optional[float] = None
    status: str = "pending"  # pending, processing, completed, failed


@dataclass
class TimelineStats:
    """Statistical summary of watcher activity."""
    
    total_events: int = 0
    events_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    events_by_pattern: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    events_by_status: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    avg_processing_time_ms: float = 0.0
    peak_events_per_minute: int = 0
    first_event: Optional[datetime] = None
    last_event: Optional[datetime] = None
    busiest_hour: Optional[int] = None
    busiest_path: Optional[str] = None
    path_frequencies: Dict[str, int] = field(default_factory=lambda: defaultdict(int))


class WatcherTimeline:
    """
    Tracks file watcher events over time with efficient history management.
    
    Provides:
    - Event stream with filtering and search
    - Pattern matching statistics
    - Performance metrics
    - Historical data with configurable retention
    """
    
    def __init__(
        self,
        max_history: int = 10000,
        retention_hours: int = 24,
        stats_interval_seconds: int = 60,
    ):
        self.max_history = max_history
        self.retention_hours = retention_hours
        self.stats_interval_seconds = stats_interval_seconds
        
        # Circular buffer for events
        self._events: deque[WatcherEvent] = deque(maxlen=max_history)
        
        # Real-time stats tracking
        self._stats = TimelineStats()
        self._minute_buckets: Dict[datetime, int] = {}
        self._hour_buckets: Dict[int, int] = defaultdict(int)
        
        # Event streaming
        self._subscribers: List[asyncio.Queue[WatcherEvent]] = []
        self._lock = asyncio.Lock()
        
        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start background tasks."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Watcher timeline started (max_history=%d, retention=%dh)",
                       self.max_history, self.retention_hours)
    
    async def stop(self) -> None:
        """Stop background tasks."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Watcher timeline stopped")
    
    async def record_event(self, event: WatcherEvent) -> None:
        """Record a new watcher event and update statistics."""
        async with self._lock:
            self._events.append(event)
            self._update_stats(event)
            
            # Notify subscribers
            for queue in self._subscribers:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    logger.debug("Timeline subscriber queue full, dropping event")
    
    def _update_stats(self, event: WatcherEvent) -> None:
        """Update running statistics with new event."""
        self._stats.total_events += 1
        self._stats.events_by_type[event.event_type] += 1
        
        if event.pattern_matched:
            self._stats.events_by_pattern[event.pattern_matched] += 1
        
        self._stats.events_by_status[event.status] += 1
        
        if event.duration_ms is not None:
            # Running average
            n = self._stats.total_events
            old_avg = self._stats.avg_processing_time_ms
            self._stats.avg_processing_time_ms = (
                (old_avg * (n - 1) + event.duration_ms) / n
            )
        
        # Track first/last events
        if self._stats.first_event is None:
            self._stats.first_event = event.timestamp
        self._stats.last_event = event.timestamp
        
        # Track events per minute for peak detection
        minute_key = event.timestamp.replace(second=0, microsecond=0)
        self._minute_buckets[minute_key] = self._minute_buckets.get(minute_key, 0) + 1
        if self._minute_buckets[minute_key] > self._stats.peak_events_per_minute:
            self._stats.peak_events_per_minute = self._minute_buckets[minute_key]
        
        # Track busiest hour
        hour = event.timestamp.hour
        self._hour_buckets[hour] += 1
        if self._stats.busiest_hour is None or \
           self._hour_buckets[hour] > self._hour_buckets[self._stats.busiest_hour]:
            self._stats.busiest_hour = hour
        
        # Track path frequencies
        self._stats.path_frequencies[event.path] += 1
        if self._stats.busiest_path is None or \
           self._stats.path_frequencies[event.path] > \
           self._stats.path_frequencies[self._stats.busiest_path]:
            self._stats.busiest_path = event.path
    
    async def get_events(
        self,
        limit: int = 100,
        offset: int = 0,
        event_type: Optional[str] = None,
        pattern: Optional[str] = None,
        status: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        path_contains: Optional[str] = None,
    ) -> List[WatcherEvent]:
        """
        Query events with filtering.
        
        Args:
            limit: Maximum events to return
            offset: Skip this many events
            event_type: Filter by event type (created, modified, etc.)
            pattern: Filter by matched pattern
            status: Filter by processing status
            since: Filter events after this time
            until: Filter events before this time
            path_contains: Filter paths containing this string
        
        Returns:
            Filtered list of events, newest first
        """
        async with self._lock:
            events = list(self._events)
        
        # Apply filters
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if pattern:
            events = [e for e in events if e.pattern_matched == pattern]
        
        if status:
            events = [e for e in events if e.status == status]
        
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        if until:
            events = [e for e in events if e.timestamp <= until]
        
        if path_contains:
            path_lower = path_contains.lower()
            events = [e for e in events if path_lower in e.path.lower()]
        
        # Sort by timestamp descending (newest first)
        events.sort(key=lambda e: e.timestamp, reverse=True)
        
        # Apply pagination
        return events[offset:offset + limit]
    
    async def get_stats(self) -> TimelineStats:
        """Get current timeline statistics."""
        async with self._lock:
            # Return a copy to prevent external mutations
            return TimelineStats(
                total_events=self._stats.total_events,
                events_by_type=dict(self._stats.events_by_type),
                events_by_pattern=dict(self._stats.events_by_pattern),
                events_by_status=dict(self._stats.events_by_status),
                avg_processing_time_ms=self._stats.avg_processing_time_ms,
                peak_events_per_minute=self._stats.peak_events_per_minute,
                first_event=self._stats.first_event,
                last_event=self._stats.last_event,
                busiest_hour=self._stats.busiest_hour,
                busiest_path=self._stats.busiest_path,
                path_frequencies=dict(self._stats.path_frequencies),
            )
    
    async def get_timeline_view(
        self,
        interval_minutes: int = 5,
        hours: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Get bucketed event counts for timeline visualization.
        
        Args:
            interval_minutes: Bucket size in minutes
            hours: How many hours back to include
        
        Returns:
            List of time buckets with event counts and metadata
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=hours)
        
        async with self._lock:
            events = [e for e in self._events if e.timestamp >= cutoff]
        
        # Create buckets
        buckets: Dict[datetime, Dict[str, Any]] = {}
        
        for event in events:
            # Round to interval
            bucket_time = event.timestamp.replace(second=0, microsecond=0)
            bucket_time = bucket_time.replace(
                minute=(event.timestamp.minute // interval_minutes) * interval_minutes
            )
            
            if bucket_time not in buckets:
                buckets[bucket_time] = {
                    "timestamp": bucket_time,
                    "count": 0,
                    "by_type": defaultdict(int),
                    "by_status": defaultdict(int),
                }
            
            buckets[bucket_time]["count"] += 1
            buckets[bucket_time]["by_type"][event.event_type] += 1
            buckets[bucket_time]["by_status"][event.status] += 1
        
        # Convert to sorted list
        result = sorted(buckets.values(), key=lambda b: b["timestamp"])
        
        # Convert defaultdicts to regular dicts for JSON serialization
        for bucket in result:
            bucket["by_type"] = dict(bucket["by_type"])
            bucket["by_status"] = dict(bucket["by_status"])
        
        return result
    
    async def subscribe(self) -> asyncio.Queue[WatcherEvent]:
        """Subscribe to real-time event stream."""
        queue: asyncio.Queue[WatcherEvent] = asyncio.Queue(maxsize=1000)
        async with self._lock:
            self._subscribers.append(queue)
        return queue
    
    async def unsubscribe(self, queue: asyncio.Queue[WatcherEvent]) -> None:
        """Unsubscribe from event stream."""
        async with self._lock:
            if queue in self._subscribers:
                self._subscribers.remove(queue)
    
    async def _cleanup_loop(self) -> None:
        """Background task to clean up old events and buckets."""
        while True:
            try:
                await asyncio.sleep(self.stats_interval_seconds)
                await self._cleanup_old_data()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Error in timeline cleanup: %s", exc, exc_info=True)
    
    async def _cleanup_old_data(self) -> None:
        """Remove events and buckets older than retention period."""
        cutoff = datetime.utcnow() - timedelta(hours=self.retention_hours)
        
        async with self._lock:
            # Clean up minute buckets
            old_minutes = [k for k in self._minute_buckets if k < cutoff]
            for k in old_minutes:
                del self._minute_buckets[k]
            
            if old_minutes:
                logger.debug("Cleaned up %d old minute buckets", len(old_minutes))
    
    async def clear(self) -> None:
        """Clear all events and reset statistics (for testing/admin)."""
        async with self._lock:
            self._events.clear()
            self._stats = TimelineStats()
            self._minute_buckets.clear()
            self._hour_buckets.clear()
            logger.info("Watcher timeline cleared")


# Global singleton
_timeline: Optional[WatcherTimeline] = None


def get_watcher_timeline() -> WatcherTimeline:
    """Get or create the global watcher timeline instance."""
    global _timeline
    if _timeline is None:
        _timeline = WatcherTimeline()
    return _timeline
