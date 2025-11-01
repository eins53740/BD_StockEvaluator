"""
API Gateway middleware for Epic 9 F9.3.

Provides:
- Rate limiting per client
- API key authentication
- Request logging and metrics
"""

from __future__ import annotations

import os
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException, Request, status
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware


# ============================================================================
# Rate Limiting
# ============================================================================

class RateLimiter:
    """
    In-memory rate limiter with sliding window algorithm.

    For production, use Redis-backed limiter for distributed systems.
    """

    def __init__(self, requests_per_minute: int = 60):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute per client
        """
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # seconds
        self.requests: Dict[str, list[float]] = defaultdict(list)

    def _clean_old_requests(self, client_id: str, now: float) -> None:
        """Remove requests older than the window."""
        cutoff = now - self.window_size
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id] if req_time > cutoff
        ]

    def check_rate_limit(self, client_id: str) -> tuple[bool, Dict[str, Any]]:
        """
        Check if client has exceeded rate limit.

        Args:
            client_id: Unique client identifier (IP or API key)

        Returns:
            Tuple of (is_allowed, metadata dict with limit info)
        """
        now = time.time()
        self._clean_old_requests(client_id, now)

        request_count = len(self.requests[client_id])
        remaining = max(0, self.requests_per_minute - request_count)

        metadata = {
            "limit": self.requests_per_minute,
            "remaining": remaining,
            "reset": int(now + self.window_size),
        }

        if request_count >= self.requests_per_minute:
            return False, metadata

        # Record this request
        self.requests[client_id].append(now)
        metadata["remaining"] = remaining - 1

        return True, metadata


# ============================================================================
# API Key Authentication
# ============================================================================

# API key header
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKeyAuthenticator:
    """
    Simple API key authentication.

    For production, integrate with proper user management system.
    """

    def __init__(self):
        """Initialize authenticator with API keys from environment."""
        self.api_keys = self._load_api_keys()
        self.require_auth = os.getenv("REQUIRE_API_KEY", "false").lower() == "true"

    def _load_api_keys(self) -> set[str]:
        """Load valid API keys from environment."""
        keys_str = os.getenv("VALID_API_KEYS", "")
        if not keys_str:
            # Generate a default key for development
            default_key = os.getenv("DEFAULT_API_KEY", "dev-key-123")
            return {default_key}

        # Parse comma-separated keys
        return set(key.strip() for key in keys_str.split(",") if key.strip())

    def authenticate(self, api_key: Optional[str]) -> tuple[bool, Optional[str]]:
        """
        Authenticate request with API key.

        Args:
            api_key: API key from header

        Returns:
            Tuple of (is_authenticated, client_id or error_message)
        """
        # If auth not required, allow all
        if not self.require_auth:
            return True, "anonymous"

        # Check API key
        if not api_key:
            return False, "Missing API key"

        if api_key not in self.api_keys:
            return False, "Invalid API key"

        return True, api_key


# ============================================================================
# Rate Limiting Middleware
# ============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting and authentication.
    """

    def __init__(self, app, requests_per_minute: int = 60):
        """
        Initialize middleware.

        Args:
            app: FastAPI application
            requests_per_minute: Rate limit per client
        """
        super().__init__(app)
        self.limiter = RateLimiter(requests_per_minute)
        self.authenticator = APIKeyAuthenticator()

        # Exempt paths from rate limiting (health checks, docs)
        self.exempt_paths = {
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Any:
        """Process request with rate limiting and auth."""

        # Skip exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        # Authenticate
        api_key = request.headers.get("X-API-Key")
        is_authenticated, client_id = self.authenticator.authenticate(api_key)

        if not is_authenticated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=client_id,  # Error message
                headers={"WWW-Authenticate": "ApiKey"},
            )

        # Fallback to IP if no API key
        if client_id == "anonymous":
            client_id = request.client.host if request.client else "unknown"

        # Check rate limit
        is_allowed, metadata = self.limiter.check_rate_limit(client_id)

        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {metadata['reset'] - time.time():.0f} seconds.",
                headers={
                    "X-RateLimit-Limit": str(metadata["limit"]),
                    "X-RateLimit-Remaining": str(metadata["remaining"]),
                    "X-RateLimit-Reset": str(metadata["reset"]),
                    "Retry-After": str(int(metadata["reset"] - time.time())),
                },
            )

        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(metadata["limit"])
        response.headers["X-RateLimit-Remaining"] = str(metadata["remaining"])
        response.headers["X-RateLimit-Reset"] = str(metadata["reset"])

        return response


# ============================================================================
# Request Logging Middleware
# ============================================================================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging all API requests.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Any:
        """Log request and response."""
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Log request
        print(
            f"[{datetime.now(timezone.utc).isoformat()}] "
            f"{request.method} {request.url.path} "
            f"- {response.status_code} - {duration*1000:.2f}ms"
        )

        return response


# ============================================================================
# Helper Functions
# ============================================================================

def get_client_identifier(request: Request) -> str:
    """
    Get unique client identifier from request.

    Tries in order:
    1. X-API-Key header
    2. X-Forwarded-For header (proxy)
    3. Client IP address
    """
    # Try API key first
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"key:{api_key}"

    # Try X-Forwarded-For (behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # Fallback to client IP
    if request.client:
        return request.client.host

    return "unknown"


def generate_api_key() -> str:
    """Generate a new API key."""
    import secrets

    return f"sk_{secrets.token_urlsafe(32)}"
