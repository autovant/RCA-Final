"""
Multi-Tenant Guardrails and Distributed Processing

Provides:
- Tenant isolation and resource quotas
- Distributed job processing
- AI-guided troubleshooting
- Cross-tenant security enforcement
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from enum import Enum

from core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# Multi-Tenant Guardrails
# ============================================================================

class TenantPlan(str, Enum):
    """Subscription plans with different resource limits."""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


@dataclass
class TenantQuota:
    """Resource quota for a tenant."""
    
    max_jobs_per_hour: int
    max_concurrent_jobs: int
    max_file_size_mb: int
    max_storage_gb: int
    max_api_calls_per_minute: int
    max_embedding_requests_per_day: int
    priority: int  # 0=lowest, 10=highest
    features: Set[str] = field(default_factory=set)
    
    @staticmethod
    def for_plan(plan: TenantPlan) -> "TenantQuota":
        """Get quota configuration for a plan."""
        quotas = {
            TenantPlan.FREE: TenantQuota(
                max_jobs_per_hour=10,
                max_concurrent_jobs=2,
                max_file_size_mb=10,
                max_storage_gb=1,
                max_api_calls_per_minute=30,
                max_embedding_requests_per_day=100,
                priority=1,
                features={"basic_analysis"},
            ),
            TenantPlan.STARTER: TenantQuota(
                max_jobs_per_hour=50,
                max_concurrent_jobs=5,
                max_file_size_mb=50,
                max_storage_gb=10,
                max_api_calls_per_minute=100,
                max_embedding_requests_per_day=1000,
                priority=3,
                features={"basic_analysis", "pii_redaction", "platform_detection"},
            ),
            TenantPlan.PROFESSIONAL: TenantQuota(
                max_jobs_per_hour=200,
                max_concurrent_jobs=10,
                max_file_size_mb=100,
                max_storage_gb=100,
                max_api_calls_per_minute=500,
                max_embedding_requests_per_day=10000,
                priority=5,
                features={
                    "basic_analysis",
                    "pii_redaction",
                    "platform_detection",
                    "ml_insights",
                    "custom_processors",
                    "webhook_notifications",
                },
            ),
            TenantPlan.ENTERPRISE: TenantQuota(
                max_jobs_per_hour=10000,
                max_concurrent_jobs=50,
                max_file_size_mb=1000,
                max_storage_gb=1000,
                max_api_calls_per_minute=5000,
                max_embedding_requests_per_day=100000,
                priority=10,
                features={
                    "basic_analysis",
                    "pii_redaction",
                    "platform_detection",
                    "ml_insights",
                    "custom_processors",
                    "webhook_notifications",
                    "distributed_processing",
                    "dedicated_resources",
                    "sla_support",
                    "custom_integrations",
                },
            ),
        }
        
        return quotas.get(plan, quotas[TenantPlan.FREE])


@dataclass
class TenantUsage:
    """Current usage tracking for a tenant."""
    
    tenant_id: str
    jobs_this_hour: int = 0
    concurrent_jobs: int = 0
    storage_used_gb: float = 0.0
    api_calls_this_minute: int = 0
    embedding_requests_today: int = 0
    last_reset_hour: Optional[datetime] = None
    last_reset_minute: Optional[datetime] = None
    last_reset_day: Optional[datetime] = None


class TenantGuardrails:
    """
    Enforces multi-tenant resource limits and isolation.
    
    Ensures:
    - Resource quotas are respected
    - Tenants are isolated from each other
    - Fair resource allocation
    - Usage tracking and billing integration
    """
    
    def __init__(self):
        self._tenant_quotas: Dict[str, TenantQuota] = {}
        self._tenant_usage: Dict[str, TenantUsage] = {}
        self._lock = asyncio.Lock()
    
    async def register_tenant(
        self,
        tenant_id: str,
        plan: TenantPlan = TenantPlan.FREE,
        custom_quota: Optional[TenantQuota] = None,
    ) -> None:
        """Register a tenant with their quota."""
        async with self._lock:
            quota = custom_quota or TenantQuota.for_plan(plan)
            self._tenant_quotas[tenant_id] = quota
            
            if tenant_id not in self._tenant_usage:
                self._tenant_usage[tenant_id] = TenantUsage(tenant_id=tenant_id)
            
            logger.info("Registered tenant %s with plan %s", tenant_id, plan)
    
    async def check_job_quota(self, tenant_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if tenant can start a new job.
        
        Returns:
            (allowed, reason_if_denied)
        """
        async with self._lock:
            if tenant_id not in self._tenant_quotas:
                return False, "Tenant not registered"
            
            quota = self._tenant_quotas[tenant_id]
            usage = self._tenant_usage[tenant_id]
            
            # Reset hourly counter if needed
            now = datetime.utcnow()
            if usage.last_reset_hour is None or \
               now - usage.last_reset_hour > timedelta(hours=1):
                usage.jobs_this_hour = 0
                usage.last_reset_hour = now
            
            # Check concurrent jobs
            if usage.concurrent_jobs >= quota.max_concurrent_jobs:
                return False, f"Max concurrent jobs reached ({quota.max_concurrent_jobs})"
            
            # Check hourly limit
            if usage.jobs_this_hour >= quota.max_jobs_per_hour:
                return False, f"Hourly job limit reached ({quota.max_jobs_per_hour})"
            
            return True, None
    
    async def track_job_start(self, tenant_id: str) -> None:
        """Track job start for usage accounting."""
        async with self._lock:
            if tenant_id in self._tenant_usage:
                usage = self._tenant_usage[tenant_id]
                usage.jobs_this_hour += 1
                usage.concurrent_jobs += 1
    
    async def track_job_complete(self, tenant_id: str) -> None:
        """Track job completion."""
        async with self._lock:
            if tenant_id in self._tenant_usage:
                usage = self._tenant_usage[tenant_id]
                usage.concurrent_jobs = max(0, usage.concurrent_jobs - 1)
    
    async def check_file_size(
        self,
        tenant_id: str,
        file_size_mb: float,
    ) -> tuple[bool, Optional[str]]:
        """Check if file size is within tenant limits."""
        async with self._lock:
            if tenant_id not in self._tenant_quotas:
                return False, "Tenant not registered"
            
            quota = self._tenant_quotas[tenant_id]
            
            if file_size_mb > quota.max_file_size_mb:
                return False, f"File size exceeds limit ({quota.max_file_size_mb}MB)"
            
            return True, None
    
    async def check_storage(
        self,
        tenant_id: str,
        additional_gb: float = 0.0,
    ) -> tuple[bool, Optional[str]]:
        """Check if storage quota allows additional data."""
        async with self._lock:
            if tenant_id not in self._tenant_quotas:
                return False, "Tenant not registered"
            
            quota = self._tenant_quotas[tenant_id]
            usage = self._tenant_usage[tenant_id]
            
            if usage.storage_used_gb + additional_gb > quota.max_storage_gb:
                return False, f"Storage limit exceeded ({quota.max_storage_gb}GB)"
            
            return True, None
    
    async def check_feature_access(
        self,
        tenant_id: str,
        feature: str,
    ) -> bool:
        """Check if tenant has access to a feature."""
        async with self._lock:
            if tenant_id not in self._tenant_quotas:
                return False
            
            quota = self._tenant_quotas[tenant_id]
            return feature in quota.features
    
    async def get_tenant_priority(self, tenant_id: str) -> int:
        """Get tenant's priority level for job scheduling."""
        async with self._lock:
            if tenant_id not in self._tenant_quotas:
                return 0
            
            return self._tenant_quotas[tenant_id].priority
    
    async def get_usage_summary(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get current usage summary for a tenant."""
        async with self._lock:
            if tenant_id not in self._tenant_usage:
                return None
            
            usage = self._tenant_usage[tenant_id]
            quota = self._tenant_quotas.get(tenant_id)
            
            if quota is None:
                return None
            
            return {
                "tenant_id": tenant_id,
                "quota": {
                    "max_jobs_per_hour": quota.max_jobs_per_hour,
                    "max_concurrent_jobs": quota.max_concurrent_jobs,
                    "max_file_size_mb": quota.max_file_size_mb,
                    "max_storage_gb": quota.max_storage_gb,
                },
                "current_usage": {
                    "jobs_this_hour": usage.jobs_this_hour,
                    "concurrent_jobs": usage.concurrent_jobs,
                    "storage_used_gb": usage.storage_used_gb,
                },
                "limits_percentage": {
                    "jobs": (usage.jobs_this_hour / quota.max_jobs_per_hour) * 100,
                    "concurrent": (usage.concurrent_jobs / quota.max_concurrent_jobs) * 100,
                    "storage": (usage.storage_used_gb / quota.max_storage_gb) * 100,
                },
            }


# ============================================================================
# Distributed Processing
# ============================================================================

@dataclass
class WorkerNode:
    """Represents a worker node in distributed cluster."""
    
    node_id: str
    hostname: str
    capacity: int  # Max concurrent jobs
    current_load: int = 0
    last_heartbeat: Optional[datetime] = None
    capabilities: Set[str] = field(default_factory=set)
    region: Optional[str] = None
    
    def is_healthy(self, timeout_seconds: int = 30) -> bool:
        """Check if worker is healthy based on heartbeat."""
        if self.last_heartbeat is None:
            return False
        
        age = (datetime.utcnow() - self.last_heartbeat).total_seconds()
        return age < timeout_seconds
    
    def available_capacity(self) -> int:
        """Get available capacity."""
        return max(0, self.capacity - self.current_load)


class DistributedJobScheduler:
    """
    Schedules jobs across distributed worker nodes.
    
    Features:
    - Load balancing
    - Locality optimization
    - Failure recovery
    - Priority-based scheduling
    """
    
    def __init__(self):
        self._workers: Dict[str, WorkerNode] = {}
        self._job_assignments: Dict[str, str] = {}  # job_id -> node_id
        self._lock = asyncio.Lock()
    
    async def register_worker(
        self,
        node_id: str,
        hostname: str,
        capacity: int,
        capabilities: Optional[Set[str]] = None,
        region: Optional[str] = None,
    ) -> None:
        """Register a worker node."""
        async with self._lock:
            self._workers[node_id] = WorkerNode(
                node_id=node_id,
                hostname=hostname,
                capacity=capacity,
                capabilities=capabilities or set(),
                region=region,
                last_heartbeat=datetime.utcnow(),
            )
            logger.info("Registered worker node: %s (%s)", node_id, hostname)
    
    async def update_heartbeat(self, node_id: str) -> None:
        """Update worker heartbeat."""
        async with self._lock:
            if node_id in self._workers:
                self._workers[node_id].last_heartbeat = datetime.utcnow()
    
    async def assign_job(
        self,
        job_id: str,
        required_capabilities: Optional[Set[str]] = None,
        preferred_region: Optional[str] = None,
        priority: int = 5,
    ) -> Optional[str]:
        """
        Assign job to a worker node.
        
        Returns:
            Selected node_id or None if no capacity
        """
        async with self._lock:
            eligible_workers = []
            
            for worker in self._workers.values():
                # Check health
                if not worker.is_healthy():
                    continue
                
                # Check capacity
                if worker.available_capacity() <= 0:
                    continue
                
                # Check capabilities
                if required_capabilities and \
                   not required_capabilities.issubset(worker.capabilities):
                    continue
                
                eligible_workers.append(worker)
            
            if not eligible_workers:
                logger.warning("No eligible workers for job %s", job_id)
                return None
            
            # Prioritize by region if specified
            if preferred_region:
                regional = [w for w in eligible_workers if w.region == preferred_region]
                if regional:
                    eligible_workers = regional
            
            # Select worker with most available capacity
            selected = max(eligible_workers, key=lambda w: w.available_capacity())
            
            # Record assignment
            self._job_assignments[job_id] = selected.node_id
            selected.current_load += 1
            
            logger.info("Assigned job %s to worker %s", job_id, selected.node_id)
            return selected.node_id
    
    async def release_job(self, job_id: str) -> None:
        """Release job assignment and free worker capacity."""
        async with self._lock:
            if job_id not in self._job_assignments:
                return
            
            node_id = self._job_assignments[job_id]
            if node_id in self._workers:
                worker = self._workers[node_id]
                worker.current_load = max(0, worker.current_load - 1)
            
            del self._job_assignments[job_id]
    
    async def get_cluster_status(self) -> Dict[str, Any]:
        """Get overall cluster status."""
        async with self._lock:
            total_capacity = sum(w.capacity for w in self._workers.values())
            total_load = sum(w.current_load for w in self._workers.values())
            healthy_workers = sum(1 for w in self._workers.values() if w.is_healthy())
            
            return {
                "total_workers": len(self._workers),
                "healthy_workers": healthy_workers,
                "total_capacity": total_capacity,
                "current_load": total_load,
                "utilization_percent": (total_load / total_capacity * 100) if total_capacity > 0 else 0,
                "active_jobs": len(self._job_assignments),
                "workers": [
                    {
                        "node_id": w.node_id,
                        "hostname": w.hostname,
                        "capacity": w.capacity,
                        "current_load": w.current_load,
                        "available": w.available_capacity(),
                        "healthy": w.is_healthy(),
                        "region": w.region,
                    }
                    for w in self._workers.values()
                ],
            }


# ============================================================================
# AI-Guided Troubleshooting
# ============================================================================

@dataclass
class TroubleshootingHint:
    """AI-generated troubleshooting hint."""
    
    issue: str
    severity: str  # low, medium, high, critical
    suggested_action: str
    explanation: str
    confidence: float  # 0.0 to 1.0
    references: List[str] = field(default_factory=list)


class AITroubleshooter:
    """
    AI-guided troubleshooting assistant.
    
    Analyzes errors and provides actionable guidance.
    """
    
    COMMON_PATTERNS = {
        "connection_refused": TroubleshootingHint(
            issue="Connection Refused",
            severity="high",
            suggested_action="Check if the target service is running and firewall allows connections",
            explanation="The application attempted to connect to a service but was refused. This typically means the service is not running or is blocking connections.",
            confidence=0.9,
            references=["networking", "connectivity"],
        ),
        "timeout": TroubleshootingHint(
            issue="Operation Timeout",
            severity="medium",
            suggested_action="Increase timeout values or check network latency",
            explanation="An operation took longer than the configured timeout. This could indicate network issues or overloaded services.",
            confidence=0.85,
            references=["performance", "networking"],
        ),
        "permission_denied": TroubleshootingHint(
            issue="Permission Denied",
            severity="high",
            suggested_action="Check file/directory permissions and user credentials",
            explanation="The application lacks necessary permissions to access a resource. Verify user permissions and authentication.",
            confidence=0.95,
            references=["security", "authentication"],
        ),
    }
    
    def analyze_error(
        self,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[TroubleshootingHint]:
        """
        Analyze error and provide troubleshooting hints.
        
        Returns:
            List of relevant hints sorted by confidence
        """
        hints = []
        error_lower = error_message.lower()
        
        # Check common patterns
        if "connection refused" in error_lower or "could not connect" in error_lower:
            hints.append(self.COMMON_PATTERNS["connection_refused"])
        
        if "timeout" in error_lower or "timed out" in error_lower:
            hints.append(self.COMMON_PATTERNS["timeout"])
        
        if "permission denied" in error_lower or "access denied" in error_lower:
            hints.append(self.COMMON_PATTERNS["permission_denied"])
        
        # Sort by confidence
        hints.sort(key=lambda h: h.confidence, reverse=True)
        
        return hints


# Global singletons
_tenant_guardrails: Optional[TenantGuardrails] = None
_distributed_scheduler: Optional[DistributedJobScheduler] = None
_ai_troubleshooter: Optional[AITroubleshooter] = None


def get_tenant_guardrails() -> TenantGuardrails:
    """Get or create the global tenant guardrails instance."""
    global _tenant_guardrails
    if _tenant_guardrails is None:
        _tenant_guardrails = TenantGuardrails()
    return _tenant_guardrails


def get_distributed_scheduler() -> DistributedJobScheduler:
    """Get or create the global distributed scheduler."""
    global _distributed_scheduler
    if _distributed_scheduler is None:
        _distributed_scheduler = DistributedJobScheduler()
    return _distributed_scheduler


def get_ai_troubleshooter() -> AITroubleshooter:
    """Get or create the global AI troubleshooter."""
    global _ai_troubleshooter
    if _ai_troubleshooter is None:
        _ai_troubleshooter = AITroubleshooter()
    return _ai_troubleshooter
