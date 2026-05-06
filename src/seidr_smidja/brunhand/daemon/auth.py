"""seidr_smidja.brunhand.daemon.auth — Gæslumaðr, the Bearer-Token Guard.

Every authenticated endpoint in Horfunarþjónn passes through Gæslumaðr before
executing. Gæslumaðr validates the Authorization: Bearer <token> header using
constant-time comparison to prevent timing-based token inference.

INVARIANTS:
  - Bearer token is NEVER logged, returned in response bodies, or included in
    Annáll event payloads. Only 'missing', 'malformed', or 'rejected' status is logged.
  - GET /v1/brunhand/health is the only documented exception that bypasses auth.
    All primitives and /capabilities require a valid token.
  - Comparison uses hmac.compare_digest() — constant time regardless of where
    the first differing byte appears.

See: docs/features/brunhand/ARCHITECTURE.md §V Authentication Architecture
See: docs/features/brunhand/DATA_FLOW.md §VI Authentication Wiring
"""
from __future__ import annotations

import hmac
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Attempt FastAPI import — graceful degradation if unavailable
try:
    from fastapi import Request
    from fastapi.responses import JSONResponse
    from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
    from starlette.responses import Response

    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False
    BaseHTTPMiddleware = object  # type: ignore[assignment,misc]
    Request = None  # type: ignore[assignment]
    Response = None  # type: ignore[assignment]
    RequestResponseEndpoint = None  # type: ignore[assignment]
    JSONResponse = None  # type: ignore[assignment]

# The single path that does NOT require authentication
_HEALTH_PATH = "/v1/brunhand/health"


class GaeslumadrMiddleware(BaseHTTPMiddleware):  # type: ignore[misc]
    """Gæslumaðr — the Bearer-Token Guard middleware.

    Validates Authorization: Bearer <token> header on every request except
    GET /v1/brunhand/health (the documented bounded exception).

    The token is loaded at daemon startup and held in memory.
    It is NEVER written to any log, trace, or Annáll event.
    """

    def __init__(self, app: Any, token: str, annall: Any = None) -> None:
        """Construct Gæslumaðr.

        Args:
            app:    The ASGI app to wrap.
            token:  The configured bearer token (held in memory, never logged).
            annall: Optional AnnallPort for logging rejection events.
        """
        super().__init__(app)  # type: ignore[call-arg]
        self._token = token
        self._annall = annall
        self._daemon_session_id: str = ""  # Set after daemon startup

    def set_daemon_session_id(self, session_id: str) -> None:
        """Bind the daemon's Annáll session ID for event logging."""
        self._daemon_session_id = session_id

    async def dispatch(  # type: ignore[override]
        self, request: Any, call_next: Any
    ) -> Any:
        """Gate every request through the bearer token check."""
        # The health endpoint is the documented, bounded exception — no auth required
        if request.url.path == _HEALTH_PATH:
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        presented_token, status = _extract_token(auth_header)

        if status == "accepted" and _tokens_match(presented_token, self._token):
            # Token valid — pass to next handler
            return await call_next(request)

        # Token rejected — log the rejection and return 401
        request_id = request.headers.get("x-request-id", "")
        source_ip = _get_client_ip(request)

        logger.warning(
            "Gæslumaðr: bearer token %s from %s (request_id=%s path=%s)",
            status,
            source_ip,
            request_id,
            request.url.path,
        )

        _log_rejection(self._annall, self._daemon_session_id, request_id, source_ip)

        return JSONResponse(  # type: ignore[misc]
            status_code=401,
            content={
                "error": "unauthorized",
                "message": "Bearer token is missing or invalid.",
                "request_id": request_id,
            },
        )


def _extract_token(auth_header: str) -> tuple[str, str]:
    """Extract bearer token from Authorization header.

    Returns:
        Tuple of (token_value, status) where status is one of:
        'accepted' (header present and correctly formatted),
        'missing'  (no Authorization header),
        'malformed' (header present but not in Bearer scheme).
    """
    if not auth_header:
        return "", "missing"
    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return "", "malformed"
    return parts[1].strip(), "accepted"


def _tokens_match(presented: str, configured: str) -> bool:
    """Constant-time comparison of two token strings.

    Uses hmac.compare_digest() to prevent timing attacks.
    Returns False (not raises) if either value is empty.
    """
    if not presented or not configured:
        return False
    try:
        return hmac.compare_digest(presented.encode(), configured.encode())
    except Exception:
        return False


def _get_client_ip(request: Any) -> str:
    """Extract client IP from request, handling proxy headers."""
    try:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
    except Exception:
        pass
    return "unknown"


def _log_rejection(
    annall: Any, session_id: str, request_id: str, source_ip: str
) -> None:
    """Log a rejection event to the daemon-side Annáll.

    TOKEN INVARIANT: The header value is logged as '[REDACTED]' — never the token.
    """
    if annall is None:
        return
    try:
        from seidr_smidja.annall.port import AnnallEvent

        annall.log_event(
            session_id or "daemon",
            AnnallEvent.warning(
                "brunhand.daemon.auth.rejected",
                {
                    "request_id": request_id,
                    "source_ip": source_ip,
                    "authorization_header": "[REDACTED]",
                    "timestamp": time.time(),
                },
            ),
        )
    except Exception:
        pass  # Annáll failure never disrupts the middleware
