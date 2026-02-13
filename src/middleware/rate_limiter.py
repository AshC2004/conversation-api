"""In-memory sliding window rate limiter keyed by user_id."""

import time
from collections import defaultdict

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.config.settings import get_settings

# Paths that use the stricter AI generation limit
AI_PATHS = {"/api/v1/conversations/{id}/messages", "/api/v1/conversations/{id}/messages/stream"}


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        # user_id -> list of request timestamps
        self._standard_windows: dict[str, list[float]] = defaultdict(list)
        self._ai_windows: dict[str, list[float]] = defaultdict(list)

    def _is_ai_path(self, path: str) -> bool:
        parts = path.rstrip("/").split("/")
        # Match /api/v1/conversations/<uuid>/messages[/stream]
        if len(parts) >= 6 and parts[1] == "api" and parts[2] == "v1" and parts[3] == "conversations" and parts[5] == "messages":
            return True
        return False

    def _check_limit(self, window: list[float], limit: int, now: float) -> tuple[bool, int]:
        """Remove expired entries, check if under limit. Returns (allowed, retry_after_seconds)."""
        cutoff = now - 60.0
        while window and window[0] < cutoff:
            window.pop(0)

        if len(window) >= limit:
            retry_after = int(window[0] - cutoff) + 1
            return False, retry_after

        window.append(now)
        return True, 0

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for non-authed routes and health checks
        if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        # Extract user_id from request state (set by auth dependency, or absent)
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            # If no user_id yet, let the request through—auth will reject if needed
            return await call_next(request)

        settings = get_settings()
        now = time.time()

        # Check AI-specific rate limit
        if self._is_ai_path(request.url.path) and request.method == "POST":
            allowed, retry_after = self._check_limit(self._ai_windows[user_id], settings.RATE_LIMIT_AI, now)
            if not allowed:
                return Response(
                    content=f'{{"status":"error","error":{{"type":"rate_limit","message":"AI generation rate limit exceeded"}}}}',
                    status_code=429,
                    headers={"Retry-After": str(retry_after), "Content-Type": "application/json"},
                )

        # Check standard rate limit
        allowed, retry_after = self._check_limit(self._standard_windows[user_id], settings.RATE_LIMIT_STANDARD, now)
        if not allowed:
            return Response(
                content=f'{{"status":"error","error":{{"type":"rate_limit","message":"Rate limit exceeded"}}}}',
                status_code=429,
                headers={"Retry-After": str(retry_after), "Content-Type": "application/json"},
            )

        return await call_next(request)
