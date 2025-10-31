"""Tenant management and multi-tenant endpoints."""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from core.db.database import get_db_session
from core.jobs.distributed import TenantGuardrails


router = APIRouter(prefix="/api/tenant", tags=["tenant"])


# --- Models ---

class TenantUsageResponse(BaseModel):
    """Tenant usage statistics."""
    tenant_id: str
    plan: str
    jobs_today: int
    cost_today: float
    jobs_this_month: int
    cost_this_month: float
    quota_limit_daily: int
    quota_remaining_today: int
    utilization_pct: float


class TenantQuotaUpdate(BaseModel):
    """Update tenant quota/plan."""
    plan: str = Field(..., description="Plan: free, starter, professional, enterprise")


class TenantJob(BaseModel):
    """Tenant job submission."""
    job_type: str = Field(..., description="Job type")
    payload: dict = Field(..., description="Job payload")
    priority: int = Field(5, ge=1, le=10, description="Priority 1-10")
    estimated_cost: Optional[float] = Field(None, description="Estimated cost")


# --- Endpoints ---

@router.get("/{tenant_id}/usage", response_model=TenantUsageResponse)
async def get_tenant_usage(
    tenant_id: str,
):
    """
    Get current usage statistics for a tenant.
    
    Returns job counts, costs, and quota information.
    """
    guardrails = TenantGuardrails()
    
    usage = await guardrails.get_usage(tenant_id)
    quota = guardrails._quotas.get(
        tenant_id,
        guardrails._default_quotas["free"]
    )
    
    jobs_today = usage.get("jobs_today", 0)
    quota_remaining = max(0, quota.max_jobs_per_day - jobs_today)
    utilization = (jobs_today / quota.max_jobs_per_day * 100) if quota.max_jobs_per_day > 0 else 0
    
    return TenantUsageResponse(
        tenant_id=tenant_id,
        plan=quota.plan,
        jobs_today=jobs_today,
        cost_today=usage.get("cost_today", 0.0),
        jobs_this_month=usage.get("jobs_this_month", 0),
        cost_this_month=usage.get("cost_this_month", 0.0),
        quota_limit_daily=quota.max_jobs_per_day,
        quota_remaining_today=quota_remaining,
        utilization_pct=round(utilization, 2),
    )


@router.put("/{tenant_id}/quota")
async def update_tenant_quota(
    tenant_id: str,
    update: TenantQuotaUpdate,
):
    """
    Update tenant quota/plan.
    
    Upgrades or changes the tenant's subscription plan.
    """
    valid_plans = ["free", "starter", "professional", "enterprise"]
    
    if update.plan not in valid_plans:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid plan. Must be one of: {', '.join(valid_plans)}"
        )
    
    guardrails = TenantGuardrails()
    
    success = await guardrails.upgrade_plan(tenant_id, update.plan)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to update tenant quota"
        )
    
    # Get updated usage
    usage = await guardrails.get_usage(tenant_id)
    quota = guardrails._quotas[tenant_id]
    
    return {
        "tenant_id": tenant_id,
        "plan": quota.plan,
        "max_jobs_per_day": quota.max_jobs_per_day,
        "max_cost_per_day": quota.max_cost_per_day,
        "max_concurrent_jobs": quota.max_concurrent_jobs,
        "priority_boost": quota.priority_boost,
        "current_usage": usage,
    }


@router.post("/{tenant_id}/jobs/check-quota")
async def check_job_quota(
    tenant_id: str,
    job: TenantJob,
):
    """
    Check if tenant has quota for a job.
    
    Returns whether the job can be submitted given current quota.
    """
    guardrails = TenantGuardrails()
    
    estimated_cost = job.estimated_cost or 1.0
    
    allowed = await guardrails.check_quota(
        tenant_id=tenant_id,
        job_type=job.job_type,
        estimated_cost=estimated_cost,
    )
    
    if not allowed:
        usage = await guardrails.get_usage(tenant_id)
        return {
            "allowed": False,
            "reason": "quota_exceeded",
            "usage": usage,
        }
    
    return {
        "allowed": True,
        "estimated_cost": estimated_cost,
    }


@router.get("/{tenant_id}/jobs/history")
async def get_tenant_job_history(
    tenant_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    job_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get job history for a tenant.
    
    Returns paginated list of jobs submitted by the tenant.
    """
    try:
        import sqlalchemy as sa
        
        query_text = """
            SELECT 
                job_id,
                job_type,
                status,
                created_at,
                completed_at,
                duration_seconds,
                cost
            FROM jobs
            WHERE tenant_id = :tenant_id
        """
        
        params = {"tenant_id": tenant_id, "limit": limit, "offset": offset}
        
        if job_type:
            query_text += " AND job_type = :job_type"
            params["job_type"] = job_type
        
        query_text += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        
        result = await db.execute(sa.text(query_text), params)
        
        jobs = [
            {
                "job_id": row.job_id,
                "job_type": row.job_type,
                "status": row.status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                "duration_seconds": row.duration_seconds,
                "cost": float(row.cost) if row.cost else 0.0,
            }
            for row in result
        ]
        
        # Get total count
        count_query = sa.text("""
            SELECT COUNT(*) FROM jobs WHERE tenant_id = :tenant_id
        """ + (" AND job_type = :job_type" if job_type else ""))
        
        count_result = await db.execute(count_query, params)
        total = count_result.scalar_one()
        
        return {
            "tenant_id": tenant_id,
            "total": total,
            "limit": limit,
            "offset": offset,
            "jobs": jobs,
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve job history: {str(e)}"
        )


@router.get("/{tenant_id}/analytics")
async def get_tenant_analytics(
    tenant_id: str,
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get analytics for a tenant.
    
    Returns aggregated metrics about the tenant's usage patterns.
    """
    try:
        import sqlalchemy as sa
        from datetime import timedelta
        
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Job type distribution
        type_query = sa.text("""
            SELECT 
                job_type,
                COUNT(*) as count,
                AVG(duration_seconds) as avg_duration,
                SUM(cost) as total_cost
            FROM jobs
            WHERE tenant_id = :tenant_id 
                AND created_at >= :since
            GROUP BY job_type
            ORDER BY count DESC
        """)
        
        type_result = await db.execute(
            type_query,
            {"tenant_id": tenant_id, "since": since}
        )
        
        job_types = [
            {
                "job_type": row.job_type,
                "count": row.count,
                "avg_duration_seconds": float(row.avg_duration) if row.avg_duration else 0,
                "total_cost": float(row.total_cost) if row.total_cost else 0,
            }
            for row in type_result
        ]
        
        # Status distribution
        status_query = sa.text("""
            SELECT 
                status,
                COUNT(*) as count
            FROM jobs
            WHERE tenant_id = :tenant_id 
                AND created_at >= :since
            GROUP BY status
        """)
        
        status_result = await db.execute(
            status_query,
            {"tenant_id": tenant_id, "since": since}
        )
        
        statuses = {row.status: row.count for row in status_result}
        
        # Success rate
        total_jobs = sum(statuses.values())
        success_rate = (statuses.get("completed", 0) / total_jobs * 100) if total_jobs > 0 else 0
        
        return {
            "tenant_id": tenant_id,
            "time_period_hours": hours,
            "total_jobs": total_jobs,
            "success_rate_pct": round(success_rate, 2),
            "job_types": job_types,
            "status_distribution": statuses,
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve analytics: {str(e)}"
        )


@router.post("/{tenant_id}/reset-quota")
async def reset_tenant_quota(
    tenant_id: str,
):
    """
    Reset tenant's daily quota.
    
    Admin endpoint to manually reset a tenant's quota (e.g., for debugging).
    """
    guardrails = TenantGuardrails()
    
    # Reset usage tracking
    if tenant_id in guardrails._usage_tracking:
        del guardrails._usage_tracking[tenant_id]
    
    return {
        "tenant_id": tenant_id,
        "message": "Quota reset successfully",
        "reset_at": datetime.utcnow().isoformat(),
    }
