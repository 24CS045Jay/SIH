"""
Structured JSON logging for the KMRL backend.
Provides a request-ID middleware and a JSON log formatter.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import Request, Response
from pythonjsonlogger import json as json_logging
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


def configure_logging() -> None:
    """Call once at app startup to switch all logs to structured JSON."""
    handler = logging.StreamHandler()
    formatter = json_logging.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Attaches a unique X-Request-ID header to every response.
    The same ID is added to the logging context for request tracing.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        # Make request_id available to route handlers via request.state
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
