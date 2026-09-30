from __future__ import annotations

import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Context variables belong to one request only. Clear any values that
        # could have been left by a previous request before binding this one.
        clear_contextvars()

        # Preserve a caller-provided request ID when available; otherwise make
        # an easy-to-search ID with the required req-<8-hex> format.
        correlation_id = request.headers.get("x-request-id", "").strip()
        if not correlation_id:
            correlation_id = f"req-{uuid.uuid4().hex[:8]}"

        bind_contextvars(correlation_id=correlation_id)
        request.state.correlation_id = correlation_id

        start = time.perf_counter()
        try:
            response = await call_next(request)
            response.headers["x-request-id"] = correlation_id
            response.headers["x-response-time-ms"] = str(
                int((time.perf_counter() - start) * 1000)
            )
            return response
        finally:
            # Do not retain this request's metadata for the next request.
            clear_contextvars()
