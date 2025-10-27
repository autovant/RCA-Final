import pytest

from apps.api.routers import watcher as watcher_router


class _ConfigStub:
    def __init__(self):
        self.id = "config-1"
        self.enabled = True
        self.roots = ["/watch"]
        self.include_globs = ["**/*.log"]
        self.exclude_globs = ["**/~*"]
        self.max_file_size_mb = 100
        self.allowed_mime_types = ["text/plain"]
        self.batch_window_seconds = 5
        self.auto_create_jobs = True
        self.created_at = None
        self.updated_at = None


class _WatcherServiceStub:
    def __init__(self, pattern_result=None, stats_result=None):
        self._config = _ConfigStub()
        self._available_processors = [
            {
                "id": "log-event",
                "name": "Event Logger",
                "description": "Emit structured log lines whenever a watcher event is received.",
                "default_options": {"level": "info"},
            }
        ]
        self._pattern_result = pattern_result or {
            "path": "/tmp/sample.log",
            "status": "included",
            "reason": "Matches include rules",
            "matched_includes": ["**/*.log"],
            "matched_excludes": [],
            "include_globs": ["**/*.log"],
            "exclude_globs": [],
        }
        self._stats_result = stats_result or {
            "lookback_hours": 24,
            "total_events": 5,
            "event_types": [
                {
                    "event_type": "file-detected",
                    "total": 3,
                    "timeline": [
                        {"bucket": "2025-10-20T10:00:00+00:00", "count": 2},
                        {"bucket": "2025-10-20T11:00:00+00:00", "count": 1},
                    ],
                },
                {
                    "event_type": "job-created",
                    "total": 2,
                    "timeline": [
                        {"bucket": "2025-10-20T10:00:00+00:00", "count": 2},
                    ],
                },
            ],
        }
        self.test_patterns_calls = []
        self.stats_calls = []
        self.update_calls = []

    def available_processors(self):
        return self._available_processors

    async def get_config(self):
        return {"config": self._config, "available_processors": self._available_processors}

    async def update_config(self, payload):
        self.update_calls.append(payload)
        for key, value in payload.items():
            setattr(self._config, key, value)
        return self._config

    async def test_patterns(self, sample_path, include_globs=None, exclude_globs=None):
        self.test_patterns_calls.append(
            {
                "sample_path": sample_path,
                "include_globs": include_globs,
                "exclude_globs": exclude_globs,
            }
        )
        return self._pattern_result

    async def get_statistics(self, lookback_hours=24):
        self.stats_calls.append(lookback_hours)
        return self._stats_result


@pytest.mark.asyncio
async def test_list_presets_matches_constant():
    presets = await watcher_router.list_presets()
    assert len(presets) == len(watcher_router.WATCHER_PRESETS)
    assert presets[0].name == watcher_router.WATCHER_PRESETS[0]["name"]


@pytest.mark.asyncio
async def test_pattern_test_uses_service(monkeypatch):
    stub = _WatcherServiceStub()
    monkeypatch.setattr(watcher_router, "watcher_service", stub)

    result = await watcher_router.pattern_test(
        watcher_router.PatternTestRequest(
            path="/tmp/error.log",
            include_globs=["**/*.log"],
            exclude_globs=["**/~*"],
        )
    )

    assert result.status == "included"
    assert stub.test_patterns_calls == [
        {
            "sample_path": "/tmp/error.log",
            "include_globs": ["**/*.log"],
            "exclude_globs": ["**/~*"],
        }
    ]


@pytest.mark.asyncio
async def test_watcher_stats_surface_payload(monkeypatch):
    stub = _WatcherServiceStub()
    monkeypatch.setattr(watcher_router, "watcher_service", stub)

    result = await watcher_router.watcher_stats(lookback_hours=12)

    assert result.lookback_hours == 24
    assert result.total_events == 5
    assert stub.stats_calls == [12]
    assert result.event_types[0].event_type == "file-detected"
    assert result.event_types[0].timeline[0].bucket.endswith("10:00:00+00:00")


@pytest.mark.asyncio
async def test_get_config_includes_processors(monkeypatch):
    stub = _WatcherServiceStub()
    monkeypatch.setattr(watcher_router, "watcher_service", stub)

    response = await watcher_router.get_config()

    assert response.available_processors
    assert response.available_processors[0].id == "log-event"
    assert response.enabled is True
