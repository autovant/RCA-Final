"""
Health check endpoints for the API.
"""

from __future__ import annotations

from fastapi import APIRouter

from core.config import settings
from core.db.database import db_manager

router = APIRouter()


@router.get("/live")
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


__all__ = ["router"]
