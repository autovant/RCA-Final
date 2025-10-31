"""
Request deduplication middleware to prevent duplicate submissions.
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestDeduplicationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to prevent duplicate POST/PUT/PATCH requests within a time window.
    
    Uses request hash (method + path + body) to detect duplicates.
    Configurable time window for considering requests as duplicates.
    """
    
    def __init__(
        self,
        app,
        window_seconds: int = 5,
        max_cache_size: int = 1000
    ):
        """
        Initialize deduplication middleware.
        
        Args:
            app: FastAPI application
            window_seconds: Time window in seconds to consider requests as duplicates
            max_cache_size: Maximum number of recent requests to track
        """
        super().__init__(app)
        self.window_seconds = window_seconds
        self.max_cache_size = max_cache_size
        # Format: {request_hash: (timestamp, response)}
        self._recent_requests: Dict[str, Tuple[datetime, Response]] = {}
    
    def _generate_request_hash(self, request: Request, body: bytes) -> str:
        """
        Generate a hash for the request based on method, path, and body.
        
        Args:
            request: FastAPI request
            body: Request body bytes
            
        Returns:
            Hash string
        """
        hash_input = f"{request.method}:{request.url.path}:{body.decode('utf-8', errors='ignore')}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def _cleanup_old_entries(self) -> None:
        """Remove expired entries from the cache."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.window_seconds)
        
        # Remove expired entries
        expired_keys = [
            key for key, (timestamp, _) in self._recent_requests.items()
            if timestamp < cutoff
        ]
        
        for key in expired_keys:
            del self._recent_requests[key]
        
        # If still too large, remove oldest entries
        if len(self._recent_requests) > self.max_cache_size:
            sorted_items = sorted(
                self._recent_requests.items(),
                key=lambda x: x[1][0]
            )
            to_remove = len(self._recent_requests) - self.max_cache_size
            for key, _ in sorted_items[:to_remove]:
                del self._recent_requests[key]
    
    async def dispatch(self, request: Request, call_next):
        """
        Process the request and check for duplicates.
        
        Args:
            request: Incoming request
            call_next: Next middleware in chain
            
        Returns:
            Response (either cached or newly generated)
        """
        # Only check POST, PUT, PATCH requests
        if request.method not in ["POST", "PUT", "PATCH"]:
            return await call_next(request)
        
        # Skip health check endpoints
        if request.url.path in ["/health", "/health/live", "/health/ready", "/health/healthz"]:
            return await call_next(request)
        
        try:
            # Read request body
            body = await request.body()
            
            # Generate request hash
            request_hash = self._generate_request_hash(request, body)
            
            # Clean up old entries
            self._cleanup_old_entries()
            
            # Check if we've seen this request recently
            now = datetime.now(timezone.utc)
            if request_hash in self._recent_requests:
                timestamp, cached_response = self._recent_requests[request_hash]
                
                # Check if within time window
                if (now - timestamp).total_seconds() < self.window_seconds:
                    logger.warning(
                        f"Duplicate request detected: {request.method} {request.url.path} "
                        f"(hash: {request_hash[:8]}..., age: {(now - timestamp).total_seconds():.1f}s)"
                    )
                    
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": "Duplicate request detected",
                            "message": f"This request was already processed {(now - timestamp).total_seconds():.1f} seconds ago",
                            "retry_after": self.window_seconds
                        },
                        headers={
                            "Retry-After": str(self.window_seconds),
                            "X-Duplicate-Request": "true"
                        }
                    )
            
            # Process the request
            response = await call_next(request)
            
            # Cache successful requests (2xx status codes)
            if 200 <= response.status_code < 300:
                self._recent_requests[request_hash] = (now, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in deduplication middleware: {e}")
            # On error, let the request through
            return await call_next(request)


__all__ = ["RequestDeduplicationMiddleware"]
