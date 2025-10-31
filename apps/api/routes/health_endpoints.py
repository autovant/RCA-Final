"""Health check and monitoring endpoints."""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

from core.db.database import get_db_session
from core.metrics.enhanced_collectors import TelemetryValidator
from core.watchers.timeline import get_watcher_timeline
from core.jobs.distributed import DistributedJobScheduler


router = APIRouter(prefix="/health", tags=["health"])


@router.get("/telemetry")
async def check_telemetry_health():
    """
    Validate telemetry system health.
    
    Runs comprehensive validation checks on embedding cache metrics,
    compressed ingestion metrics, and overall telemetry infrastructure.
    """
    results = TelemetryValidator.validate_all()
    
    status_code = 200 if results["status"] == "healthy" else 503
    
    return {
        "status": results["status"],
        "timestamp": results["timestamp"],
        "components": results["components"],
        "checks_passed": sum(
            1 for comp in results["components"].values()
            if comp["status"] == "healthy"
        ),
        "total_checks": len(results["components"]),
    }


@router.get("/watchers")
async def check_watcher_health():
    """
    Check file watcher system health.
    
    Returns statistics and status of the file watcher system.
    """
    timeline = get_watcher_timeline()
    
    stats = await timeline.get_stats(hours=1)
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "timeline_stats": {
            "total_events": stats.total_events,
            "events_by_type": stats.events_by_type,
            "events_by_status": stats.events_by_status,
            "avg_processing_time_ms": stats.avg_processing_time_ms,
        },
        "recent_errors": [
            event for event in await timeline.get_events(limit=10, status="error")
        ],
    }


@router.get("/database")
async def check_database_health(db: AsyncSession = Depends(get_db_session)):
    """
    Check database connectivity and health.
    
    Performs basic database health checks.
    """
    try:
        # Test connection
        result = await db.execute(sa.text("SELECT 1"))
        result.scalar_one()
        
        # Get pool stats
        pool = db.get_bind().pool
        pool_stats = {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        }
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "connection": "ok",
            "pool": pool_stats,
        }
    
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
        }


@router.get("/cluster")
async def check_cluster_health():
    """
    Check distributed cluster health.
    
    Returns status of distributed job scheduler and worker nodes.
    """
    try:
        scheduler = DistributedJobScheduler()
        
        workers = await scheduler.list_workers()
        active_workers = [w for w in workers if w.status == "active"]
        
        # Get queue depths
        queue_stats = await scheduler.get_queue_stats()
        
        return {
            "status": "healthy" if len(active_workers) > 0 else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "workers": {
                "total": len(workers),
                "active": len(active_workers),
                "inactive": len(workers) - len(active_workers),
            },
            "queues": queue_stats,
            "load_distribution": [
                {
                    "worker_id": w.worker_id,
                    "current_load": w.current_load,
                    "capacity": w.capacity,
                    "utilization_pct": (w.current_load / w.capacity * 100) if w.capacity > 0 else 0,
                }
                for w in active_workers
            ],
        }
    
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
        }


@router.get("")
async def overall_health(
    db: AsyncSession = Depends(get_db_session),
):
    """
    Overall system health check.
    
    Aggregates health status from all subsystems.
    """
    try:
        # Check all subsystems
        db_health = await check_database_health(db)
        telemetry_health = await check_telemetry_health()
        watcher_health = await check_watcher_health()
        cluster_health = await check_cluster_health()
        
        # Determine overall status
        statuses = [
            db_health.get("status"),
            telemetry_health.get("status"),
            watcher_health.get("status"),
            cluster_health.get("status"),
        ]
        
        if all(s == "healthy" for s in statuses):
            overall_status = "healthy"
        elif any(s == "unhealthy" for s in statuses):
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "subsystems": {
                "database": db_health.get("status"),
                "telemetry": telemetry_health.get("status"),
                "watchers": watcher_health.get("status"),
                "cluster": cluster_health.get("status"),
            },
            "details": {
                "database": db_health,
                "telemetry": telemetry_health,
                "watchers": watcher_health,
                "cluster": cluster_health,
            },
        }
    
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
        }


@router.get("/cache")
async def check_cache_health():
    """
    Check cache system health and statistics.
    
    Returns cache hit/miss rates, memory usage, and performance metrics.
    """
    try:
        from core.cache.response_cache import get_cache
        
        cache = get_cache()
        stats = cache.get_stats()
        
        # Calculate numeric hit rate for health check
        total_requests = stats.get("hits", 0) + stats.get("misses", 0)
        numeric_hit_rate = (stats.get("hits", 0) / total_requests) if total_requests > 0 else 1.0
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "cache_stats": {
                "size": stats.get("size", 0),
                "max_size": stats.get("max_size", 1000),
                "hits": stats.get("hits", 0),
                "misses": stats.get("misses", 0),
                "hit_rate": stats.get("hit_rate", "0.00%"),
                "evictions": stats.get("evictions", 0),
                "expirations": stats.get("expirations", 0),
            },
            "health_indicators": {
                "hit_rate_ok": numeric_hit_rate >= 0.5 if total_requests > 10 else True,
                "memory_ok": stats.get("size", 0) < stats.get("max_size", 1000),
                "evictions_ok": stats.get("evictions", 0) < total_requests * 0.1 if total_requests > 0 else True,
            },
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
