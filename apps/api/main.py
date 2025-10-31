#!/usr/bin/env python3
"""
RCA Engine - Unified API Application
Main FastAPI application entry point for the unified RCA engine.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from core.config import settings
from core.db.database import init_db, close_db
from core.logging import setup_logging
from core.metrics import setup_metrics
from core.security import setup_security
from core.jobs.event_bus import job_event_bus
from core.watchers.event_bus import watcher_event_bus
from apps.api.routers import (
    auth,
    conversation,
    files,
    health,
    incidents,
    jobs,
    prompts,
    sse,
    summary,
    tickets,
    watcher,
)
from apps.api.routes import demo_endpoints, health_endpoints, tenant_endpoints
from apps.api.middleware import SecurityMiddleware, RateLimitMiddleware, RequestLoggingMiddleware

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger.info("Starting RCA Engine API...")
    
    # Initialize database
    await init_db()
    
    # Setup metrics
    setup_metrics()
    
    # Setup security
    setup_security()
    
    # Start cache cleanup task
    from core.cache.response_cache import cache_cleanup_task
    cleanup_task = asyncio.create_task(cache_cleanup_task(interval=300))
    logger.info("Started cache cleanup task")
    
    yield
    
    # Cleanup
    logger.info("Shutting down RCA Engine API...")
    cleanup_task.cancel()
    await close_db()
    await job_event_bus.close()
    await watcher_event_bus.close()


# Create FastAPI application
app = FastAPI(
    title="RCA Engine API",
    description="Unified Root Cause Analysis Engine API",
    version="1.0.0",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan
)

# Setup CORS
security_settings = settings.security
app.add_middleware(
    CORSMiddleware,
    allow_origins=security_settings.CORS_ALLOW_ORIGINS,
    allow_credentials=security_settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=security_settings.CORS_ALLOW_METHODS,
    allow_headers=security_settings.CORS_ALLOW_HEADERS,
)

# Add compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add request logging and security middleware
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityMiddleware)

# Add rate limiting when enabled
if settings.security.RATE_LIMITING_ENABLED:
    app.add_middleware(RateLimitMiddleware)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(incidents.router, prefix="/api/v1/incidents", tags=["incidents"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(sse.router, prefix="/api/sse", tags=["streaming"])
app.include_router(summary.router, prefix="/api/summary", tags=["summary"])
app.include_router(conversation.router, prefix="/api/conversation", tags=["conversation"])
app.include_router(tickets.router, prefix="/api/tickets", tags=["tickets"])
app.include_router(watcher.router, prefix="/api/watcher", tags=["watcher"])
app.include_router(prompts.router, prefix="/api/v1/prompts", tags=["prompts"])

# Include new feature endpoints
app.include_router(demo_endpoints.router)  # Demo feedback, analytics, sharing
app.include_router(health_endpoints.router)  # Enhanced health checks
app.include_router(tenant_endpoints.router)  # Tenant management

# Mount metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "request_id": getattr(request.state, "request_id", None)
        }
    )


@app.get("/api/")
async def root():
    """Root endpoint."""
    return {
        "message": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "docs": "/api/docs" if settings.DEBUG else None
    }


@app.get("/api/status")
async def status():
    """Detailed status endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "features": {
            "redis": settings.redis.REDIS_ENABLED,
            "metrics": True,
            "streaming": True
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.DEBUG,
        log_level="info"
    )

