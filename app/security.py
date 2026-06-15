"""Security utilities and middleware for CarbonCompass.

This module provides inputs sanitization, session validation, client IP resolution,
rate limiting logic, and Starlette middleware classes.
"""

import logging
import re
import time
import unicodedata
import uuid
from typing import Any, cast

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.constants import (
    CHAT_RATE_LIMIT,
    DEFAULT_RATE_LIMIT,
    MAX_REPEAT_CHARS,
    MAX_REQUEST_SIZE_BYTES,
    RATE_LIMIT_WINDOW,
    SESSION_ID_PATTERN,
)
from app.state import rate_limit_store

logger = logging.getLogger("carboncompass")


def sanitize_input(text: str) -> str:
    """Strip dangerous characters and normalize user input.

    Removes script tags, HTML tags, null bytes, and normalizes Unicode representation
    to prevent script injection attacks.

    Args:
        text (str): The raw input text.

    Returns:
        str: The sanitized text.

    Raises:
        HTTPException: If the input contains null bytes or excessive repeated characters.
    """
    # Remove script tags and content
    text = re.sub(r"<script[\s\S]*?>[\s\S]*?</script>", "", text, flags=re.IGNORECASE)
    # Strip all HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Remove null bytes
    if "\x00" in text:
        raise HTTPException(status_code=400, detail="Invalid characters in input.")
    # Check for excessively repeated characters
    if re.search(r"(.)\1{" + str(MAX_REPEAT_CHARS - 1) + r",}", text):
        raise HTTPException(
            status_code=400, detail="Input contains excessively repeated characters."
        )
    # KFKC normalization handles visually identical unicode characters
    normalized_text = unicodedata.normalize("NFKC", text)
    return normalized_text.strip()


def validate_session_id(session_id: str) -> bool:
    """Ensure session ID matches alphanumeric pattern constraints.

    Args:
        session_id (str): The session ID to check.

    Returns:
        bool: True if valid.

    Raises:
        HTTPException: If the session ID fails validation.
    """
    if not SESSION_ID_PATTERN.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID format.")
    return True


def get_client_ip(request: Request) -> str:
    """Resolve the remote client IP from headers or connection state.

    Args:
        request (Request): The incoming request.

    Returns:
        str: The resolved client IP.
    """
    return request.client.host if request.client else "unknown"


def check_rate_limit(ip: str, endpoint: str) -> bool:
    """Check if the requesting IP is within rate limits for the endpoint.

    Args:
        ip (str): The client IP.
        endpoint (str): The requested endpoint suffix.

    Returns:
        bool: True if allowed, False if rate-limited.
    """
    now = time.time()
    bucket_key = f"{ip}:{endpoint}"
    max_requests = CHAT_RATE_LIMIT if endpoint == "chat" else DEFAULT_RATE_LIMIT

    if bucket_key not in rate_limit_store:
        rate_limit_store[bucket_key] = []

    # Purge old entries outside rate limit window
    rate_limit_store[bucket_key] = [
        t for t in rate_limit_store[bucket_key] if now - t < RATE_LIMIT_WINDOW
    ]

    if len(rate_limit_store[bucket_key]) >= max_requests:
        logger.warning(
            "rate_limit_exceeded",
            extra={
                "endpoint": f"/api/v1/{endpoint}",
                "request_id": "rate-limit",
                "ip": ip,
                "limit": max_requests,
            },
        )
        return False

    rate_limit_store[bucket_key].append(now)
    return True


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that injects standard security headers into all responses."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Inject security headers.

        Args:
            request (Request): Incoming request.
            call_next (Any): Next handler in ASGI chain.

        Returns:
            Response: Response with security headers.
        """
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(self), camera=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://www.googletagmanager.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://fonts.gstatic.com; "
            "font-src https://fonts.gstatic.com; "
            "connect-src 'self'; "
            "img-src 'self' data:;"
        )
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that limits the payload size of incoming requests."""

    def __init__(self, app: Any, max_size: int = MAX_REQUEST_SIZE_BYTES) -> None:
        """Initialize request size limiting middleware.

        Args:
            app (Any): The ASGI application.
            max_size (int): Max allowed body size in bytes.
        """
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Intercept and reject requests that exceed allowed size limit.

        Args:
            request (Request): Incoming request.
            call_next (Any): Next handler in ASGI chain.

        Returns:
            Response: Response from next handler or 413 error JSON.
        """
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_size:
            logger.warning(
                "request_too_large",
                extra={
                    "content_length": content_length,
                    "max_size": self.max_size,
                    "client_ip": get_client_ip(request),
                },
            )
            return JSONResponse(
                status_code=413,
                content={
                    "detail": f"Request body too large. Maximum size: {self.max_size} bytes."
                },
            )
        return cast(Response, await call_next(request))



class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that intercepts requests to enforce IP-based rate limiting."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Enforce rate limits per endpoint for API routes.

        Args:
            request (Request): Incoming request.
            call_next (Any): Next handler in ASGI chain.

        Returns:
            Response: Response from next handler or 429 error JSON.
        """
        path = request.url.path
        if path.startswith("/api/v1/"):
            endpoint = path.split("/")[-1]
            ip = get_client_ip(request)
            if not check_rate_limit(ip, endpoint):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Please try again later."},
                    headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
                )
        return cast(Response, await call_next(request))



class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware that injects a unique X-Request-ID into each request state and response header."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Assign correlation ID, log entry, and forward downstream.

        Args:
            request (Request): Incoming request.
            call_next (Any): Next handler.

        Returns:
            Response: Response with correlation headers.
        """
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        ip = get_client_ip(request)
        logger.info(
            "request_received",
            extra={
                "endpoint": request.url.path,
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "ip": ip,
            },
        )

        response = cast(Response, await call_next(request))
        response.headers["X-Request-ID"] = request_id
        return response
