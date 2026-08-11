from __future__ import annotations

import re
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars

from .logging_config import get_logger

REQUEST_ID_HEADER = "x-request-id"
RESPONSE_TIME_HEADER = "x-response-time-ms"

# Chỉ nhận lại correlation ID của client khi nó an toàn cho log (tránh log injection).
SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

log = get_logger()


def new_correlation_id() -> str:
    """Sinh correlation ID theo format req-<8-char-hex>."""
    return f"req-{uuid.uuid4().hex[:8]}"


def resolve_correlation_id(raw: str | None) -> str:
    """Dùng lại x-request-id hợp lệ từ upstream, ngược lại sinh ID mới."""
    if raw and SAFE_REQUEST_ID.match(raw):
        return raw
    return new_correlation_id()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Xoá contextvars để không rò rỉ context giữa các request.
        clear_contextvars()

        correlation_id = resolve_correlation_id(request.headers.get(REQUEST_ID_HEADER))

        # Bind một lần ở đây, mọi log phát sinh trong request đều có correlation_id.
        bind_contextvars(correlation_id=correlation_id)
        request.state.correlation_id = correlation_id

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            log.error(
                "http_request_failed",
                service="http",
                latency_ms=elapsed_ms,
                error_type=type(exc).__name__,
                payload={
                    "method": request.method,
                    "path": request.url.path,
                    "detail": str(exc),
                },
            )
            clear_contextvars()
            raise

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        response.headers[REQUEST_ID_HEADER] = correlation_id
        response.headers[RESPONSE_TIME_HEADER] = str(elapsed_ms)

        log.info(
            "http_request_completed",
            service="http",
            latency_ms=elapsed_ms,
            payload={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
            },
        )

        clear_contextvars()
        return response
