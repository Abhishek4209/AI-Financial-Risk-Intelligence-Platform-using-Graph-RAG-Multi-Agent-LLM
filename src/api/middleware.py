"""Request-ID tracing and safe error handling, per architecture.md's trust boundaries."""

from __future__ import annotations

import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.llm.guardrails import redact_internal_errors
from src.utils.logger import get_logger

logger = get_logger(__name__)



class RequestIDMiddleware(BaseHTTPMiddleware):
        """Attach a unique X-Request-ID to every response for traceability."""

        def __init__(self, app: ASGIApp) -> None:
                super().__init__(app)

        async def dispatch(self, request: Request, call_next) -> Response:
                request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
                request.state.request_id = request_id
                try:
                        response = await call_next(request)
                except Exception as exc:
                        logger.exception("Unhandled error for request %s", request_id)
                        raise exc
                response.headers["X-Request-ID"] = request_id
                return response



def safe_error_detail(exc: Exception) -> str:
        """Return a client-safe error message; never a stack trace or credential."""
        return redact_internal_errors(str(exc))
