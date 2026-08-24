"""
Rate Limiter Middleware
=======================

In-memory rate limiting per user/IP with plan-based tiers.
Uses a token-bucket-like approach with sliding window.

For production, swap the in-memory store with Redis.
"""

from __future__ import annotations

from collections import defaultdict
import logging
import os
import time
from typing import Dict, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Default: 60 requests per minute
DEFAULT_RATE_LIMIT = int(os.getenv("RATE_LIMIT_RPM", "60"))
RATE_WINDOW_SECONDS = 60

# Plan-based rate limits (requests per minute)
PLAN_RATE_LIMITS: Dict[str, int] = {
    "free": 30,
    "pro": 120,
    "team": 300,
    "school": 600,
    "enterprise": 1200,
}

# In-memory sliding window store
# Key: (identifier) -> list of timestamps
_request_log: Dict[str, list] = defaultdict(list)


def _get_client_id(request: Request) -> str:
    """Extract a unique client identifier from the request."""
    # Try auth header first
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        try:
            from meridian.platform.auth.jwt import decode_token
            payload = decode_token(auth.split(" ", 1)[1])
            return f"user:{payload.get('sub', 'unknown')}"
        except Exception:
            pass

    # Fallback to IP
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"
    client = request.client
    return f"ip:{client.host if client else 'unknown'}"


def _get_plan_tier(request: Request) -> str:
    """Extract plan tier from JWT token if available."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        try:
            from meridian.platform.auth.jwt import decode_token
            payload = decode_token(auth.split(" ", 1)[1])
            return payload.get("plan_tier", "free")
        except Exception:
            pass
    return "free"


def _is_rate_limited(client_id: str, limit: int) -> Tuple[bool, int, int]:
    """
    Check if a client has exceeded their rate limit.
    Returns (is_limited, remaining, reset_in_seconds).
    """
    now = time.time()
    window_start = now - RATE_WINDOW_SECONDS

    # Clean old entries
    _request_log[client_id] = [
        ts for ts in _request_log[client_id] if ts > window_start
    ]

    current_count = len(_request_log[client_id])
    remaining = max(0, limit - current_count)

    if current_count >= limit:
        # Find when the oldest request in window expires
        oldest = min(_request_log[client_id]) if _request_log[client_id] else now
        reset_in = int(oldest + RATE_WINDOW_SECONDS - now)
        return True, 0, max(1, reset_in)

    _request_log[client_id].append(now)
    return False, remaining - 1, RATE_WINDOW_SECONDS


# Paths that skip rate limiting
SKIP_PATHS = {"/health", "/health/ready", "/health/info", "/api/v1/billing/webhooks/stripe"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    HTTP middleware that enforces per-user/IP rate limiting.
    Plan-aware: higher tiers get more requests.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip rate limiting for health checks and webhooks
        if path in SKIP_PATHS:
            return await call_next(request)

        client_id = _get_client_id(request)
        plan_tier = _get_plan_tier(request)
        limit = PLAN_RATE_LIMITS.get(plan_tier, DEFAULT_RATE_LIMIT)

        is_limited, remaining, reset_in = _is_rate_limited(client_id, limit)

        if is_limited:
            logger.warning("Rate limit exceeded: %s (plan=%s, limit=%d)", client_id, plan_tier, limit)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": reset_in,
                },
                headers={
                    "Retry-After": str(reset_in),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_in),
                },
            )

        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_in)

        return response
