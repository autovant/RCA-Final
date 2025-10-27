"""
ML-Driven Pipeline Tuning and Enhanced Metrics

Provides:
- Rich pipeline metrics collection
- ML-based performance optimization
- Adaptive resource allocation
- Performance prediction and anomaly detection
"""

from __future__ import annotations

import asyncio
import statistics
from collections import deque, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from prometheus_client import Counter, Histogram, Gauge
from core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# Pipeline Metrics
# ============================================================================

pipeline_stage_duration = Histogram(
    "rca_pipeline_stage_duration_seconds",
    "Duration of each pipeline stage",
    ["stage", "success"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
)

pipeline_throughput = Histogram(
    "rca_pipeline_throughput_items_per_second",
    "Pipeline throughput in items per second",
    ["stage"],
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
)

pipeline_queue_depth = Gauge(
    "rca_pipeline_queue_depth",
    "Number of items waiting in pipeline stage queues",
    ["stage"],
)

pipeline_resource_usage = Gauge(
    "rca_pipeline_resource_usage",
    "Resource usage for pipeline stages",
    ["stage", "resource"],  # resource: cpu, memory, io
)

pipeline_errors = Counter(
    "rca_pipeline_errors_total",
    "Total pipeline errors by stage and type",
    ["stage", "error_type"],
)

pipeline_retries = Counter(
    "rca_pipeline_retries_total",
    "Total retry attempts by stage",
    ["stage", "reason"],
)

pipeline_ml_predictions = Histogram(
    "rca_pipeline_ml_prediction_accuracy",
    "Accuracy of ML predictions for pipeline optimization",
    ["model_type"],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99],
)


# ============================================================================
# ML-Driven Tuning
# ============================================================================

class OptimizationStrategy(str, Enum):
    """Optimization strategies for pipeline tuning."""
    THROUGHPUT = "throughput"  # Maximize items/sec
    LATENCY = "latency"  # Minimize response time
    RESOURCE = "resource"  # Minimize resource usage
    BALANCED = "balanced"  # Balance all factors


@dataclass
class PipelineStageStats:
    """Statistics for a pipeline stage."""
    
    name: str
    total_processed: int = 0
    total_duration_ms: float = 0.0
    success_count: int = 0
    error_count: int = 0
    recent_durations: deque = field(default_factory=lambda: deque(maxlen=100))
    recent_throughputs: deque = field(default_factory=lambda: deque(maxlen=100))
    queue_depth_history: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def avg_duration_ms(self) -> float:
        """Calculate average duration."""
        if self.total_processed == 0:
            return 0.0
        return self.total_duration_ms / self.total_processed
    
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.error_count
        if total == 0:
            return 0.0
        return self.success_count / total
    
    def p95_duration_ms(self) -> float:
        """Calculate 95th percentile duration."""
        if not self.recent_durations:
            return 0.0
        sorted_durations = sorted(self.recent_durations)
        idx = int(len(sorted_durations) * 0.95)
        return sorted_durations[min(idx, len(sorted_durations) - 1)]
    
    def avg_throughput(self) -> float:
        """Calculate average throughput."""
        if not self.recent_throughputs:
            return 0.0
        return statistics.mean(self.recent_throughputs)


@dataclass
class OptimizationRecommendation:
    """ML-generated optimization recommendation."""
    
    stage: str
    parameter: str
    current_value: Any
    recommended_value: Any
    expected_improvement: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    reason: str


class MLPipelineOptimizer:
    """
    ML-driven pipeline optimizer.
    
    Uses historical performance data to:
    - Predict optimal batch sizes
    - Adjust concurrency levels
    - Allocate resources dynamically
    - Detect performance anomalies
    """
    
    def __init__(self, strategy: OptimizationStrategy = OptimizationStrategy.BALANCED):
        self.strategy = strategy
        self.stage_stats: Dict[str, PipelineStageStats] = {}
        self.optimization_history: List[OptimizationRecommendation] = []
        
        # ML model placeholders (simplified for now)
        self._performance_model: Optional[Any] = None
        self._anomaly_detector: Optional[Any] = None
    
    def record_stage_execution(
        self,
        stage: str,
        duration_ms: float,
        success: bool,
        items_processed: int = 1,
        queue_depth: int = 0,
    ) -> None:
        """Record execution metrics for a pipeline stage."""
        if stage not in self.stage_stats:
            self.stage_stats[stage] = PipelineStageStats(name=stage)
        
        stats = self.stage_stats[stage]
        stats.total_processed += items_processed
        stats.total_duration_ms += duration_ms
        
        if success:
            stats.success_count += 1
        else:
            stats.error_count += 1
        
        stats.recent_durations.append(duration_ms)
        
        if duration_ms > 0:
            throughput = (items_processed * 1000) / duration_ms
            stats.recent_throughputs.append(throughput)
        
        stats.queue_depth_history.append(queue_depth)
        
        # Update Prometheus metrics
        pipeline_stage_duration.labels(
            stage=stage,
            success="yes" if success else "no",
        ).observe(duration_ms / 1000.0)
        
        if duration_ms > 0:
            pipeline_throughput.labels(stage=stage).observe(throughput)
        
        pipeline_queue_depth.labels(stage=stage).set(queue_depth)
    
    def detect_bottleneck(self) -> Optional[str]:
        """
        Identify pipeline bottleneck stage.
        
        Returns:
            Name of bottleneck stage or None
        """
        if not self.stage_stats:
            return None
        
        # Simple heuristic: stage with highest average queue depth
        max_queue_depth = 0.0
        bottleneck_stage = None
        
        for stage, stats in self.stage_stats.items():
            if stats.queue_depth_history:
                avg_queue = statistics.mean(stats.queue_depth_history)
                if avg_queue > max_queue_depth:
                    max_queue_depth = avg_queue
                    bottleneck_stage = stage
        
        if max_queue_depth > 10:  # Threshold
            return bottleneck_stage
        
        return None
    
    def predict_optimal_batch_size(self, stage: str) -> Optional[int]:
        """
        Predict optimal batch size for a stage.
        
        Uses historical throughput data to find sweet spot.
        """
        if stage not in self.stage_stats:
            return None
        
        stats = self.stage_stats[stage]
        
        if len(stats.recent_throughputs) < 10:
            return None  # Not enough data
        
        # Simple optimization: find batch size with best throughput
        # In production, this would use actual ML models
        avg_throughput = stats.avg_throughput()
        
        if self.strategy == OptimizationStrategy.THROUGHPUT:
            # Recommend larger batches for throughput
            if avg_throughput < 50:
                return 100
            elif avg_throughput < 100:
                return 250
            else:
                return 500
        
        elif self.strategy == OptimizationStrategy.LATENCY:
            # Smaller batches for lower latency
            return 10
        
        else:  # BALANCED or RESOURCE
            # Medium batch size
            return 50
    
    def recommend_concurrency(self, stage: str) -> Optional[int]:
        """
        Recommend optimal concurrency level for a stage.
        
        Based on queue depth and processing time.
        """
        if stage not in self.stage_stats:
            return None
        
        stats = self.stage_stats[stage]
        
        if not stats.queue_depth_history:
            return None
        
        avg_queue = statistics.mean(stats.queue_depth_history)
        avg_duration = stats.avg_duration_ms()
        
        if avg_queue > 50:
            # High queue, increase concurrency
            return min(int(avg_queue / 10), 20)
        
        elif avg_queue < 5 and avg_duration < 100:
            # Low queue and fast processing, reduce concurrency
            return max(int(avg_queue / 2), 1)
        
        # Current level seems fine
        return None
    
    def generate_recommendations(self) -> List[OptimizationRecommendation]:
        """
        Generate optimization recommendations for all stages.
        
        Returns:
            List of recommendations sorted by expected improvement
        """
        recommendations = []
        
        for stage in self.stage_stats:
            # Batch size recommendation
            optimal_batch = self.predict_optimal_batch_size(stage)
            if optimal_batch:
                recommendations.append(OptimizationRecommendation(
                    stage=stage,
                    parameter="batch_size",
                    current_value="auto",
                    recommended_value=optimal_batch,
                    expected_improvement=0.2,
                    confidence=0.7,
                    reason=f"Based on throughput analysis for {self.strategy.value} strategy",
                ))
            
            # Concurrency recommendation
            optimal_concurrency = self.recommend_concurrency(stage)
            if optimal_concurrency:
                recommendations.append(OptimizationRecommendation(
                    stage=stage,
                    parameter="concurrency",
                    current_value="auto",
                    recommended_value=optimal_concurrency,
                    expected_improvement=0.15,
                    confidence=0.8,
                    reason=f"Queue depth optimization for {stage}",
                ))
        
        # Identify bottleneck
        bottleneck = self.detect_bottleneck()
        if bottleneck:
            recommendations.append(OptimizationRecommendation(
                stage=bottleneck,
                parameter="priority",
                current_value="normal",
                recommended_value="high",
                expected_improvement=0.3,
                confidence=0.9,
                reason=f"Detected bottleneck in {bottleneck} stage",
            ))
        
        # Sort by expected improvement
        recommendations.sort(key=lambda r: r.expected_improvement, reverse=True)
        
        return recommendations
    
    def detect_anomalies(self, stage: str) -> List[str]:
        """
        Detect performance anomalies in a stage.
        
        Returns:
            List of detected anomalies
        """
        if stage not in self.stage_stats:
            return []
        
        stats = self.stage_stats[stage]
        anomalies = []
        
        # Check for high error rate
        if stats.success_rate() < 0.95:
            anomalies.append(f"Low success rate: {stats.success_rate():.2%}")
        
        # Check for high latency
        if stats.recent_durations:
            avg = statistics.mean(stats.recent_durations)
            recent = list(stats.recent_durations)[-10:]
            recent_avg = statistics.mean(recent) if recent else 0
            
            if recent_avg > avg * 1.5:
                anomalies.append(f"Latency spike detected: {recent_avg:.1f}ms vs {avg:.1f}ms avg")
        
        # Check for queue buildup
        if stats.queue_depth_history:
            recent_queue = list(stats.queue_depth_history)[-50:]
            if recent_queue and statistics.mean(recent_queue) > 100:
                anomalies.append(f"Queue buildup: {statistics.mean(recent_queue):.0f} items")
        
        return anomalies
    
    def get_stage_summary(self, stage: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive summary for a stage."""
        if stage not in self.stage_stats:
            return None
        
        stats = self.stage_stats[stage]
        
        return {
            "name": stage,
            "total_processed": stats.total_processed,
            "success_rate": stats.success_rate(),
            "avg_duration_ms": stats.avg_duration_ms(),
            "p95_duration_ms": stats.p95_duration_ms(),
            "avg_throughput": stats.avg_throughput(),
            "anomalies": self.detect_anomalies(stage),
            "recommendations": [
                r for r in self.generate_recommendations()
                if r.stage == stage
            ],
        }


# Global optimizer
_ml_optimizer: Optional[MLPipelineOptimizer] = None


def get_ml_optimizer() -> MLPipelineOptimizer:
    """Get or create the global ML pipeline optimizer."""
    global _ml_optimizer
    if _ml_optimizer is None:
        _ml_optimizer = MLPipelineOptimizer()
    return _ml_optimizer
