#!/usr/bin/env python3
"""
RCA Engine - Unified API Application
Main FastAPI application entry point for the unified RCA engine.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from core.config import settings
from core.db.database import init_db, close_db
from core.db.models import Base
from core.logging import setup_logging
from core.metrics import setup_metrics
from core.security import setup_security
from apps.api.routers import auth, jobs, files, health, sse
from apps.api.middleware import SecurityMiddleware, RateLimitMiddleware

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
    
    yield
    
    # Cleanup
    logger.info("Shutting down RCA Engine API...")
    await close_db()


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.SECURITY.CORS_ALLOW_ORIGINS,
    allow_credentials=settings.SECURITY.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.SECURITY.CORS_ALLOW_METHODS,
    allow_headers=settings.SECURITY.CORS_ALLOW_HEADERS,
)

# Add compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add security middleware
app.add_middleware(SecurityMiddleware)

# Add rate limiting (if Redis is available)
if settings.REDIS_ENABLED:
    app.add_middleware(RateLimitMiddleware)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(sse.router, prefix="/api/sse", tags=["streaming"])

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
        "message": "RCA Engine API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/api/docs" if settings.DEBUG else None
    }


@app.get("/api/status")
async def status():
    """Detailed status endpoint."""
    return {
        "status": "healthy",
        "timestamp": asyncio.get_event_loop().time(),
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "features": {
            "redis": settings.REDIS_ENABLED,
            "metrics": True,
            "streaming": True
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )