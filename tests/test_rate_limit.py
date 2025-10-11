"""Tests for the Redis-backed rate limiting middleware."""

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from httpx import AsyncClient

pytest.importorskip("sqlalchemy")

from core.security.middleware import RateLimitMiddleware
from core.config import settings


@pytest.mark.asyncio
async def test_rate_limit_enforcement(monkeypatch):
    # Configure aggressive limits to keep the test fast
    security = settings.security
    redis_settings = settings.redis
    monkeypatch.setattr(security, "RATE_LIMITING_ENABLED", True)
    monkeypatch.setattr(security, "RATE_LIMIT_DEFAULT", "2/second")
    monkeypatch.setattr(security, "RATE_LIMIT_BURST", "2/second")
    monkeypatch.setattr(security, "RATE_LIMIT_AUTH", "2/second")
    monkeypatch.setattr(redis_settings, "REDIS_ENABLED", False)

    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.get("/")
    async def read_root():
        return JSONResponse({"ok": True})

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        first = await client.get("/")
        second = await client.get("/")
        third = await client.get("/")

    assert first.status_code == 200
    assert second.headers["X-RateLimit-Remaining"] >= "0"
    assert third.status_code == 429
