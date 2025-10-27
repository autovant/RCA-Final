"""Tests for ML tuning and distributed job processing."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import asyncio

from core.jobs.ml_tuning import (
    MLPipelineOptimizer,
    PipelineStageStats,
    OptimizationRecommendation,
)
from core.jobs.distributed import (
    TenantGuardrails,
    TenantQuota,
    DistributedJobScheduler,
    AITroubleshooter,
    WorkerNode,
)


class TestMLPipelineOptimizer:
    """Test suite for ML pipeline optimizer."""
    
    @pytest.fixture
    def optimizer(self):
        """Create optimizer instance."""
        return MLPipelineOptimizer(
            lookback_minutes=60,
            anomaly_threshold_stddev=2.0,
        )
    
    def test_record_stage_completion(self, optimizer):
        """Test recording stage completion."""
        optimizer.record_stage_completion(
            stage="embedding",
            duration_ms=150.0,
            success=True,
        )
        
        # Should have stats for stage
        assert "embedding" in optimizer._stage_stats
    
    def test_detect_bottleneck(self, optimizer):
        """Test bottleneck detection."""
        # Record slow stage
        for _ in range(10):
            optimizer.record_stage_completion("slow_stage", 500.0, True)
        
        # Record fast stage
        for _ in range(10):
            optimizer.record_stage_completion("fast_stage", 50.0, True)
        
        bottlenecks = optimizer.detect_bottlenecks(threshold_percentile=0.9)
        
        assert len(bottlenecks) > 0
        assert bottlenecks[0].stage == "slow_stage"
        assert bottlenecks[0].recommendation_type == "bottleneck"
    
    def test_optimize_batch_size(self, optimizer):
        """Test batch size optimization."""
        # Simulate various batch sizes and throughput
        test_data = [
            (10, 100.0),   # Small batch, low throughput
            (50, 400.0),   # Medium batch, better throughput
            (100, 500.0),  # Large batch, best throughput
            (200, 450.0),  # Too large, worse throughput
        ]
        
        recommendation = optimizer.optimize_batch_size(
            stage="processing",
            test_data=test_data,
        )
        
        assert recommendation is not None
        assert recommendation.stage == "processing"
        # Should recommend batch size with best throughput
        assert recommendation.current_value != recommendation.suggested_value
    
    def test_detect_anomalies(self, optimizer):
        """Test anomaly detection."""
        # Record normal durations
        for _ in range(50):
            optimizer.record_stage_completion("normal_stage", 100.0, True)
        
        # Record anomalous duration
        optimizer.record_stage_completion("normal_stage", 500.0, True)
        
        anomalies = optimizer.detect_anomalies()
        
        # Should detect the outlier
        assert len(anomalies) > 0
    
    def test_get_recommendations(self, optimizer):
        """Test getting all recommendations."""
        # Record data
        for _ in range(20):
            optimizer.record_stage_completion("stage1", 200.0, True)
            optimizer.record_stage_completion("stage2", 50.0, True)
        
        recommendations = optimizer.get_recommendations()
        
        assert isinstance(recommendations, list)
        # Should identify stage1 as bottleneck
        assert any(r.stage == "stage1" for r in recommendations)


class TestTenantGuardrails:
    """Test suite for tenant guardrails."""
    
    @pytest.fixture
    def guardrails(self):
        """Create guardrails instance."""
        return TenantGuardrails()
    
    @pytest.mark.asyncio
    async def test_check_quota_free_tier(self, guardrails):
        """Test quota check for free tier."""
        allowed = await guardrails.check_quota(
            tenant_id="tenant1",
            job_type="analysis",
            estimated_cost=5.0,
        )
        
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_quota_exceeded(self, guardrails):
        """Test quota exceeded scenario."""
        tenant_id = "tenant_exceed"
        
        # Consume quota
        for _ in range(5):
            await guardrails.check_quota(tenant_id, "analysis", 10.0)
        
        # Should be near or over limit
        usage = await guardrails.get_usage(tenant_id)
        assert usage["jobs_today"] >= 5
    
    @pytest.mark.asyncio
    async def test_record_usage(self, guardrails):
        """Test recording usage."""
        await guardrails.record_usage(
            tenant_id="tenant2",
            job_type="processing",
            actual_cost=8.5,
            duration_seconds=120.0,
        )
        
        usage = await guardrails.get_usage("tenant2")
        assert usage["jobs_today"] >= 1
        assert usage["cost_today"] >= 8.5
    
    @pytest.mark.asyncio
    async def test_upgrade_plan(self, guardrails):
        """Test upgrading tenant plan."""
        success = await guardrails.upgrade_plan("tenant3", "professional")
        assert success is True
        
        # Should have higher limits
        quota = guardrails._quotas.get("tenant3")
        assert quota.plan == "professional"
        assert quota.max_jobs_per_day > 50


class TestDistributedJobScheduler:
    """Test suite for distributed job scheduler."""
    
    @pytest.fixture
    def scheduler(self):
        """Create scheduler instance."""
        return DistributedJobScheduler(
            max_workers=5,
            heartbeat_interval_seconds=30,
        )
    
    @pytest.mark.asyncio
    async def test_register_worker(self, scheduler):
        """Test worker registration."""
        worker = WorkerNode(
            worker_id="worker1",
            host="localhost",
            capacity=10,
            capabilities=["analysis", "processing"],
        )
        
        await scheduler.register_worker(worker)
        
        workers = await scheduler.list_workers()
        assert len(workers) >= 1
        assert any(w.worker_id == "worker1" for w in workers)
    
    @pytest.mark.asyncio
    async def test_submit_job(self, scheduler):
        """Test job submission."""
        # Register worker first
        worker = WorkerNode(
            worker_id="worker1",
            host="localhost",
            port=8001,
            capabilities=["analysis"],
        )
        await scheduler.register_worker(worker)
        
        job_data = {
            "job_id": "job1",
            "job_type": "analysis",
            "tenant_id": "tenant1",
            "payload": {"data": "test"},
            "priority": 5,
        }
        
        job_id = await scheduler.submit_job(job_data)
        assert job_id == "job1"
    
    @pytest.mark.asyncio
    async def test_assign_job_to_worker(self, scheduler):
        """Test job assignment."""
        # Setup worker
        worker = WorkerNode(
            worker_id="worker1",
            host="localhost",
            port=8001,
            capabilities=["processing"],
        )
        await scheduler.register_worker(worker)
        
        # Submit job
        job_data = {
            "job_id": "job2",
            "job_type": "processing",
            "tenant_id": "tenant1",
            "payload": {},
            "priority": 5,
        }
        await scheduler.submit_job(job_data)
        
        # Assignment happens in background task
        await asyncio.sleep(0.1)
        
        # Check job status
        status = await scheduler.get_job_status("job2")
        assert status is not None
    
    @pytest.mark.asyncio
    async def test_load_balancing(self, scheduler):
        """Test load balancing across workers."""
        # Register multiple workers
        for i in range(3):
            worker = WorkerNode(
                worker_id=f"worker{i}",
                host=f"host{i}",
                port=8000 + i,
                capabilities=["processing"],
            )
            await scheduler.register_worker(worker)
        
        # Submit multiple jobs
        for i in range(10):
            job_data = {
                "job_id": f"job{i}",
                "job_type": "processing",
                "tenant_id": "tenant1",
                "payload": {},
                "priority": 5,
            }
            await scheduler.submit_job(job_data)
        
        # Allow scheduling
        await asyncio.sleep(0.2)
        
        # Verify jobs distributed
        workers = await scheduler.list_workers()
        assert len(workers) > 0


class TestAITroubleshooter:
    """Test suite for AI troubleshooter."""
    
    @pytest.fixture
    def troubleshooter(self):
        """Create troubleshooter instance."""
        return AITroubleshooter()
    
    @pytest.mark.asyncio
    async def test_analyze_failure(self, troubleshooter):
        """Test failure analysis."""
        analysis = await troubleshooter.analyze_failure(
            job_id="job1",
            error_type="timeout",
            error_message="Job exceeded time limit",
            context={"duration": 3600, "stage": "embedding"},
        )
        
        assert "diagnosis" in analysis
        assert "suggestions" in analysis
        assert len(analysis["suggestions"]) > 0
    
    @pytest.mark.asyncio
    async def test_pattern_recognition(self, troubleshooter):
        """Test error pattern recognition."""
        # Record similar errors
        for i in range(5):
            await troubleshooter.analyze_failure(
                job_id=f"job{i}",
                error_type="memory_error",
                error_message="Out of memory",
                context={"stage": "embedding"},
            )
        
        patterns = await troubleshooter.get_error_patterns(hours=1)
        
        assert len(patterns) > 0
        memory_pattern = next(
            (p for p in patterns if p["error_type"] == "memory_error"),
            None
        )
        assert memory_pattern is not None
        assert memory_pattern["count"] >= 5
    
    @pytest.mark.asyncio
    async def test_suggest_retry_strategy(self, troubleshooter):
        """Test retry strategy suggestion."""
        suggestion = await troubleshooter.suggest_retry_strategy(
            job_id="job1",
            error_type="transient_error",
            failure_count=2,
        )
        
        assert "should_retry" in suggestion
        assert "backoff_seconds" in suggestion
        assert "max_retries" in suggestion
    
    @pytest.mark.asyncio
    async def test_get_health_insights(self, troubleshooter):
        """Test getting health insights."""
        insights = await troubleshooter.get_health_insights()
        
        assert "total_failures" in insights
        assert "top_errors" in insights
        assert "health_score" in insights
        assert 0 <= insights["health_score"] <= 100
