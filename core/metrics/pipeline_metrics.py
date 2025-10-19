"""Utilities for pipeline stage Prometheus instrumentation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional
import time

from prometheus_client import Counter, Histogram

from core.metrics import registry

# Shared label set mandated by the specification / plan.
_PIPELINE_STAGE_LABELS = (
    "tenant_id",
    "stage",
    "platform",
    "file_type",
    "size_category",
    "status",
    "feature_flags",
)

# Buckets chosen to capture sub-second work up to multi-minute archival ingest.
# Exponential buckets ensure we retain fidelity around the SLA (4 minutes).
_PIPELINE_DURATION_BUCKETS = (
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    20.0,
    40.0,
    80.0,
    160.0,
    240.0,
    360.0,
)

_PIPELINE_STAGE_COUNTER = Counter(
    "rca_pipeline_stage_total",
    "Number of pipeline stage executions grouped by tenant and outcome.",
    _PIPELINE_STAGE_LABELS,
    registry=registry,
)

_PIPELINE_STAGE_DURATION = Histogram(
    "rca_pipeline_stage_duration_seconds",
    "Pipeline stage execution duration in seconds.",
    _PIPELINE_STAGE_LABELS,
    registry=registry,
    buckets=_PIPELINE_DURATION_BUCKETS,
)

_EMBEDDING_CACHE_REQUESTS = Counter(
    "rca_embedding_cache_requests_total",
    "Embedding cache lookup attempts grouped by tenant and model.",
    ("tenant_id", "model", "result"),
    registry=registry,
)

_EMBEDDING_CACHE_HITS = Counter(
    "rca_embedding_cache_hits_total",
    "Embedding cache hits grouped by tenant and model.",
    ("tenant_id", "model"),
    registry=registry,
)

_SIZE_BUCKETS = (
    (100 * 1024, "tiny"),       # <= 100 KiB
    (1 * 1024 * 1024, "small"),  # <= 1 MiB
    (5 * 1024 * 1024, "medium"), # <= 5 MiB
    (20 * 1024 * 1024, "large"), # <= 20 MiB
)
_DEFAULT_SIZE_CATEGORY = "xlarge"


def _normalise_feature_flags(flags: Optional[Iterable[str]]) -> str:
    if not flags:
        return "none"
    cleaned = sorted({flag.strip().lower() for flag in flags if flag})
    return "|".join(cleaned) or "none"


def _derive_size_category(size_bytes: Optional[int]) -> str:
    if size_bytes is None or size_bytes < 0:
        return _DEFAULT_SIZE_CATEGORY

    for threshold, label in _SIZE_BUCKETS:
        if size_bytes <= threshold:
            return label
    return _DEFAULT_SIZE_CATEGORY


@dataclass(frozen=True)
class StageLabels:
    """Computed label values for metrics emission."""

    tenant_id: str
    stage: str
    platform: str
    file_type: str
    size_category: str
    status: str
    feature_flags: str

    def to_kwargs(self) -> dict[str, str]:
        return {
            "tenant_id": self.tenant_id,
            "stage": self.stage,
            "platform": self.platform,
            "file_type": self.file_type,
            "size_category": self.size_category,
            "status": self.status,
            "feature_flags": self.feature_flags,
        }


class PipelineStageMetrics:
    """Convenience wrapper bound to a specific pipeline stage."""

    def __init__(self, stage: str) -> None:
        self._stage = stage

    def observe(
        self,
        *,
        tenant_id: str,
        status: str,
        duration_seconds: float,
        platform: str = "generic",
        file_type: str = "unknown",
        size_bytes: Optional[int] = None,
        feature_flags: Optional[Iterable[str]] = None,
    ) -> None:
        labels = StageLabels(
            tenant_id=tenant_id,
            stage=self._stage,
            platform=platform or "generic",
            file_type=file_type or "unknown",
            size_category=_derive_size_category(size_bytes),
            status=status or "unknown",
            feature_flags=_normalise_feature_flags(feature_flags),
        )
        kwargs = labels.to_kwargs()
        _PIPELINE_STAGE_COUNTER.labels(**kwargs).inc()
        _PIPELINE_STAGE_DURATION.labels(**kwargs).observe(max(duration_seconds, 0.0))

    def track(
        self,
        *,
        tenant_id: str,
        platform: str = "generic",
        file_type: str = "unknown",
        size_bytes: Optional[int] = None,
        feature_flags: Optional[Iterable[str]] = None,
        status_on_error: str = "failed",
    ) -> "_StageTimer":
        """Measure a stage using a context manager."""
        return _StageTimer(
            collector=self,
            tenant_id=tenant_id,
            platform=platform,
            file_type=file_type,
            size_bytes=size_bytes,
            feature_flags=feature_flags,
            status_on_error=status_on_error,
        )


class _StageTimer:
    """Context manager to time pipeline stages."""

    def __init__(
        self,
        *,
        collector: PipelineStageMetrics,
        tenant_id: str,
        platform: str,
        file_type: str,
        size_bytes: Optional[int],
        feature_flags: Optional[Iterable[str]],
        status_on_error: str,
    ) -> None:
        self._collector = collector
        self._tenant_id = tenant_id
        self._platform = platform
        self._file_type = file_type
        self._size_bytes = size_bytes
        self._feature_flags = feature_flags
        self._status_on_error = status_on_error
        self._status_override: Optional[str] = None
        self._start: Optional[float] = None

    def __enter__(self) -> "_StageTimer":  # pragma: no cover - trivial
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, _tb) -> None:  # pragma: no cover - exercise at integration level
        duration = 0.0
        if self._start is not None:
            duration = max(time.perf_counter() - self._start, 0.0)
        status = self._status_override or ("success" if exc_type is None else self._status_on_error)
        self._collector.observe(
            tenant_id=self._tenant_id,
            platform=self._platform,
            file_type=self._file_type,
            size_bytes=self._size_bytes,
            feature_flags=self._feature_flags,
            status=status,
            duration_seconds=duration,
        )
        # Propagate exception (if any) so caller can handle upstream.
        return None

    def status(self, value: str) -> None:
        """Override the final status label before exit."""
        self._status_override = value


class PipelineMetricsCollector:
    """Factory for stage-specific metrics collectors."""

    def __init__(self) -> None:
        self.ingest = PipelineStageMetrics("ingest")
        self.chunk = PipelineStageMetrics("chunk")
        self.embed = PipelineStageMetrics("embed")
        self.cache = PipelineStageMetrics("cache")
        self.storage = PipelineStageMetrics("storage")
        self.embedding_cache_requests = _EMBEDDING_CACHE_REQUESTS
        self.embedding_cache_hits = _EMBEDDING_CACHE_HITS

    def for_stage(self, stage: str) -> PipelineStageMetrics:
        mapping = {
            "ingest": self.ingest,
            "chunk": self.chunk,
            "embed": self.embed,
            "cache": self.cache,
            "storage": self.storage,
        }
        try:
            return mapping[stage]
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise ValueError(f"Unsupported pipeline stage: {stage}") from exc

    def record_cache_request(
        self,
        *,
        tenant_id: str,
        model: str,
        hit: bool,
    ) -> None:
        """Track cache request outcomes."""

        result = "hit" if hit else "miss"
        self.embedding_cache_requests.labels(tenant_id=tenant_id, model=model, result=result).inc()
        if hit:
            self.embedding_cache_hits.labels(tenant_id=tenant_id, model=model).inc()


__all__ = [
    "PipelineMetricsCollector",
    "PipelineStageMetrics",
    "StageLabels",
]
