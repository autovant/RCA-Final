"""
Health check endpoints for the API.
"""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.db.database import db_manager, get_db
from core.cache.response_cache import cached

router = APIRouter()


@router.get("/live")
@cached(ttl=30)  # Cache for 30 seconds
async def liveness() -> dict:
    """Simple liveness probe."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@router.get("/ready")
async def readiness() -> dict:
    """Report whether critical dependencies are ready."""
    healthy = False
    if db_manager.is_initialized:
        healthy = await db_manager.health_check()
    return {
        "status": "ready" if healthy else "starting",
        "database": healthy,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/deep")
async def deep_health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Comprehensive health check for monitoring and debugging.
    Tests all critical dependencies and returns detailed status.
    """
    checks: Dict[str, Any] = {}
    
    # Database check
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        checks["database"] = {
            "status": "healthy",
            "pool": db_manager.get_pool_stats()
        }
    except Exception as e:
        checks["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Redis check (if configured)
    try:
        if hasattr(settings, 'redis') and settings.redis.REDIS_ENABLED:
            # Import here to avoid errors if redis not installed
            from redis import asyncio as aioredis
            redis_client = aioredis.from_url(
                settings.redis.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await redis_client.ping()
            await redis_client.close()
            checks["redis"] = {"status": "healthy"}
        else:
            checks["redis"] = {"status": "disabled"}
    except Exception as e:
        checks["redis"] = {"status": "degraded", "error": str(e)}
    
    # LLM Provider check
    try:
        # Quick check if LLM config is present
        if settings.llm.OPENAI_API_KEY and not str(settings.llm.OPENAI_API_KEY).startswith("your-"):
            checks["llm"] = {"status": "configured", "provider": "openai"}
        elif settings.llm.OLLAMA_BASE_URL:
            checks["llm"] = {"status": "configured", "provider": "ollama"}
        else:
            checks["llm"] = {"status": "not_configured"}
    except Exception as e:
        checks["llm"] = {"status": "error", "error": str(e)}
    
    # Determine overall status
    critical_checks = ["database"]
    overall = "healthy"
    
    for check_name in critical_checks:
        if checks.get(check_name, {}).get("status") == "unhealthy":
            overall = "unhealthy"
            break
        elif checks.get(check_name, {}).get("status") in ["degraded", "error"]:
            overall = "degraded"
    
    return {
        "status": overall,
        "timestamp": str(__import__('datetime').datetime.now(__import__('datetime').timezone.utc)),
        "checks": checks,
        "environment": settings.ENVIRONMENT
    }


@router.get("/pool")
@cached(ttl=10)  # Cache for 10 seconds
async def database_pool_stats() -> Dict[str, Any]:
    """
    Get database connection pool statistics for monitoring.
    Useful for debugging connection leaks and pool exhaustion.
    """
    return db_manager.get_pool_stats()


@router.get("/cache")
async def cache_stats() -> Dict[str, Any]:
    """
    Get response cache statistics.
    Shows hit rate, size, and eviction metrics.
    """
    from core.cache.response_cache import get_cache
    return get_cache().get_stats()


# Kubernetes-style aliases
@router.get("/healthz")
async def healthz() -> dict:
    """Kubernetes-style liveness probe alias."""
    return await liveness()


@router.get("/readyz")
async def readyz() -> dict:
    """Kubernetes-style readiness probe alias."""
    return await readiness()


__all__ = ["router"]
