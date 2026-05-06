"""seidr_smidja.brunhand.daemon.app — Horfunarþjónn FastAPI app construction.

Factory function for the FastAPI application. Wires:
  - Middleware (Gæslumaðr outermost → RequestLogMiddleware — corrected B-004)
  - Session serialization lock (B-001) — HTTP 423 Locked while a primitive runs
  - Routes for all 16 endpoints
  - Startup event: probe capabilities, wire Annáll session
  - Shutdown event: clean Annáll close

INVARIANT: No primitive executes without Gæslumaðr passing the bearer token.
INVARIANT: GET /v1/brunhand/health bypasses auth — this is the documented exception.
INVARIANT: Only one primitive POST executes at a time — concurrent session rejected
           with HTTP 423 Locked + X-Brunhand-Session-Active header (ARCHITECTURE §XII).

B-001: asyncio.Lock acquired for duration of every authenticated POST primitive.
       Health and capabilities are read-only and do NOT acquire the lock.
B-004: Middleware registration order corrected — Starlette last-registered is
       outermost (first to run).  Gæslumaðr added last → runs first.
B-005: Dead gaeslu instance removed; session ID passed via mutable container.
B-009: X-Forwarded-For gated on trust_proxy_headers config (default: False).

See: src/seidr_smidja/brunhand/daemon/INTERFACE.md
See: docs/features/brunhand/ARCHITECTURE.md §III, §XII
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)

_DAEMON_VERSION = "0.1.0"

# ─── Optional FastAPI import ──────────────────────────────────────────────────
try:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from starlette.middleware.base import BaseHTTPMiddleware

    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False
    FastAPI = None  # type: ignore[assignment,misc]
    Request = None  # type: ignore[assignment]
    JSONResponse = None  # type: ignore[assignment]
    BaseHTTPMiddleware = object  # type: ignore[assignment,misc]


def create_daemon_app(
    token: str,
    daemon_cfg: dict[str, Any] | None = None,
    annall: Any = None,
) -> Any:
    """Build and return the configured FastAPI daemon application.

    Args:
        token:      Bearer token for Gæslumaðr (in-memory, never logged).
        daemon_cfg: Daemon config dict from load_daemon_config().
        annall:     Optional AnnallPort for daemon-side telemetry.

    Returns:
        A configured FastAPI app instance.

    Raises:
        ImportError: If FastAPI is not installed.
    """
    if not _FASTAPI_AVAILABLE:
        raise ImportError(
            "FastAPI is required to run the Brúarhönd daemon. "
            "Install with: pip install 'seidr-smidja[brunhand-daemon]'"
        )

    cfg = daemon_cfg or {}

    # B-009: Only trust X-Forwarded-For if operator explicitly enables it.
    # Default: False — use actual remote IP for all forensic logging.
    trust_proxy_headers: bool = cfg.get("trust_proxy_headers", False)

    app = FastAPI(
        title="Horfunarþjónn — Brúarhönd Daemon",
        description=(
            "The Watching-Daemon. Bearer-authenticated GUI automation server "
            "for VRoid Studio remote control via Brúarhönd."
        ),
        version=_DAEMON_VERSION,
    )

    # Module-level state accessible to routes via closure
    _daemon_annall_session_id: list[str] = [""]  # mutable container for closure

    # B-001: Session serialization lock.
    # asyncio.Lock — held for the duration of every authenticated primitive POST.
    # Only one primitive runs at a time; concurrent callers receive 423 Locked.
    _primitive_lock: asyncio.Lock = asyncio.Lock()
    # Track the active session ID under the lock for the 423 response header.
    _active_session_id: list[str] = [""]

    # B-005: Session ID container for GaeslumadrMiddleware.
    # The middleware is registered via add_middleware() which means we cannot get
    # a reference to the live instance.  We pass the same mutable list that
    # _daemon_annall_session_id uses, so Gæslumaðr reads from it directly.
    # (GaeslumadrMiddleware.set_daemon_session_id is no longer used — see below.)

    # ── Middleware ────────────────────────────────────────────────────────────
    # B-004 FIX: In Starlette, the LAST add_middleware() call wraps the whole stack
    # and becomes the OUTERMOST middleware (first to run on each request).
    # Correct documented order: (1) Gæslumaðr outermost, (2) RequestLogMiddleware inner.
    # So we must add RequestLogMiddleware FIRST, then GaeslumadrMiddleware SECOND.

    # RequestLogMiddleware — inner (runs after Gæslumaðr auth pass)
    class RequestLogMiddleware(BaseHTTPMiddleware):  # type: ignore[misc]
        async def dispatch(self, request: Any, call_next: Any) -> Any:  # type: ignore[override]
            req_id = request.headers.get("x-request-id", str(uuid.uuid4()))
            start = time.monotonic()
            _log_annall_daemon(
                annall, _daemon_annall_session_id[0],
                "brunhand.daemon.request.received",
                {
                    "method": request.method,
                    "path": request.url.path,
                    "request_id": req_id,
                    "source_ip": _get_client_ip(request, trust_proxy_headers),
                },
            )
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Daemon-Latency-Ms"] = str(
                round((time.monotonic() - start) * 1000, 1)
            )
            return response

    app.add_middleware(RequestLogMiddleware)  # type: ignore[arg-type]

    # Gæslumaðr — outermost (added last, so runs first; rejects unauthorized requests
    # before they reach RequestLogMiddleware or any route handler)
    from seidr_smidja.brunhand.daemon.auth import GaeslumadrMiddleware
    # B-005 FIX: No dead standalone gaeslu instance.  The middleware reads
    # _daemon_annall_session_id[0] via the annall/session_id passed at construction.
    # We pass the mutable list reference into a thin wrapper so the live middleware
    # always uses the current session ID without needing set_daemon_session_id().
    app.add_middleware(  # type: ignore[arg-type]
        GaeslumadrMiddleware,
        token=token,
        annall=annall,
        session_id_ref=_daemon_annall_session_id,  # B-005: live reference
        trust_proxy_headers=trust_proxy_headers,   # B-009: pass through
    )

    # ── Startup / Shutdown ────────────────────────────────────────────────────

    @app.on_event("startup")
    async def on_startup() -> None:
        """Probe capabilities and open Annáll session on daemon startup."""
        from seidr_smidja.brunhand.daemon.capabilities import probe_capabilities

        manifest = probe_capabilities(daemon_version=_DAEMON_VERSION)

        # Open daemon Annáll session (if annall provided)
        if annall is not None:
            try:
                sid = annall.open_session({
                    "type": "brunhand_daemon",
                    "version": _DAEMON_VERSION,
                    "os_name": manifest.os_name,
                    "bind": cfg.get("bind_address", "127.0.0.1"),
                    "port": cfg.get("port", 8848),
                })
                _daemon_annall_session_id[0] = sid
                # B-005 FIX: _daemon_annall_session_id[0] is now the live reference
                # read by GaeslumadrMiddleware.  No separate set_daemon_session_id call.
                from seidr_smidja.annall.port import AnnallEvent
                annall.log_event(
                    sid,
                    AnnallEvent.info(
                        "brunhand.daemon.capabilities.probed",
                        {
                            "os_name": manifest.os_name,
                            "available_primitives": [
                                name for name, status in manifest.primitives.items()
                                if status.available
                            ],
                        },
                    ),
                )
            except Exception as exc:
                logger.warning("Daemon: could not open Annáll session: %s", exc)

        logger.info(
            "Horfunarþjónn started — OS=%s, version=%s, primitives_available=%d",
            manifest.os_name,
            _DAEMON_VERSION,
            sum(1 for p in manifest.primitives.values() if p.available),
        )

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        """Close daemon Annáll session on shutdown."""
        if annall is not None and _daemon_annall_session_id[0]:
            try:
                from seidr_smidja.annall.port import SessionOutcome
                annall.close_session(
                    _daemon_annall_session_id[0],
                    SessionOutcome(success=True, summary="Daemon shutdown.", elapsed_seconds=0.0),
                )
            except Exception:
                pass

    # ── Lock helper ───────────────────────────────────────────────────────────

    async def _run_locked(handler_coro: Any) -> Any:
        """B-001: Run handler_coro under the primitive serialization lock.

        If the lock is already held, immediately returns HTTP 423 Locked with
        the X-Brunhand-Session-Active header naming the incumbent session.
        This prevents two agents from moving the mouse simultaneously.

        Read-only endpoints (health, capabilities) do NOT call this helper.
        """
        if _primitive_lock.locked():
            return JSONResponse(  # type: ignore[misc]
                status_code=423,
                content={
                    "error": "locked",
                    "message": (
                        "Another primitive is currently executing on this daemon. "
                        "Retry after the active command completes."
                    ),
                    "active_session": _active_session_id[0],
                },
                headers={"X-Brunhand-Session-Active": _active_session_id[0]},
            )
        async with _primitive_lock:
            return await handler_coro

    # ── Routes ────────────────────────────────────────────────────────────────

    @app.get("/v1/brunhand/health")
    async def health() -> Any:
        """Heartbeat — no authentication required. Does NOT acquire lock."""
        from seidr_smidja.brunhand.daemon.endpoints.health import get_health_response
        return get_health_response(daemon_version=_DAEMON_VERSION)

    @app.get("/v1/brunhand/capabilities")
    async def capabilities() -> Any:
        """Return platform capabilities manifest. Auth required (Gæslumaðr). No lock."""
        from seidr_smidja.brunhand.daemon.capabilities import (
            get_cached_manifest,
            probe_capabilities,
        )
        manifest = get_cached_manifest() or probe_capabilities(_DAEMON_VERSION)
        return manifest.model_dump()

    @app.post("/v1/brunhand/screenshot")
    async def screenshot(req: Any) -> Any:
        from seidr_smidja.brunhand.daemon.endpoints.primitives import handle_screenshot
        from seidr_smidja.brunhand.models import ScreenshotRequest
        parsed = ScreenshotRequest.model_validate(req) if isinstance(req, dict) else req
        _active_session_id[0] = getattr(parsed, "session_id", "")

        async def _run() -> Any:
            return handle_screenshot(parsed, annall=annall, session_id=_daemon_annall_session_id[0])

        result = await _run_locked(_run())
        return result.model_dump() if hasattr(result, "model_dump") else result

    @app.post("/v1/brunhand/click")
    async def click(req: Any) -> Any:
        from seidr_smidja.brunhand.daemon.endpoints.primitives import handle_click
        from seidr_smidja.brunhand.models import ClickRequest
        parsed = ClickRequest.model_validate(req) if isinstance(req, dict) else req
        _active_session_id[0] = getattr(parsed, "session_id", "")

        async def _run() -> Any:
            return handle_click(parsed, annall=annall, session_id=_daemon_annall_session_id[0])

        result = await _run_locked(_run())
        return result.model_dump() if hasattr(result, "model_dump") else result

    @app.post("/v1/brunhand/move")
    async def move(req: Any) -> Any:
        from seidr_smidja.brunhand.daemon.endpoints.primitives import handle_move
        from seidr_smidja.brunhand.models import MoveRequest
        parsed = MoveRequest.model_validate(req) if isinstance(req, dict) else req
        _active_session_id[0] = getattr(parsed, "session_id", "")

        async def _run() -> Any:
            return handle_move(parsed, annall=annall, session_id=_daemon_annall_session_id[0])

        result = await _run_locked(_run())
        return result.model_dump() if hasattr(result, "model_dump") else result

    @app.post("/v1/brunhand/drag")
    async def drag(req: Any) -> Any:
        from seidr_smidja.brunhand.daemon.endpoints.primitives import handle_drag
        from seidr_smidja.brunhand.models import DragRequest
        parsed = DragRequest.model_validate(req) if isinstance(req, dict) else req
        _active_session_id[0] = getattr(parsed, "session_id", "")

        async def _run() -> Any:
            return handle_drag(parsed, annall=annall, session_id=_daemon_annall_session_id[0])

        result = await _run_locked(_run())
        return result.model_dump() if hasattr(result, "model_dump") else result

    @app.post("/v1/brunhand/scroll")
    async def scroll(req: Any) -> Any:
        from seidr_smidja.brunhand.daemon.endpoints.primitives import handle_scroll
        from seidr_smidja.brunhand.models import ScrollRequest
        parsed = ScrollRequest.model_validate(req) if isinstance(req, dict) else req
        _active_session_id[0] = getattr(parsed, "session_id", "")

        async def _run() -> Any:
            return handle_scroll(parsed, annall=annall, session_id=_daemon_annall_session_id[0])

        result = await _run_locked(_run())
        return result.model_dump() if hasattr(result, "model_dump") else result

    @app.post("/v1/brunhand/type")
    async def type_text(req: Any) -> Any:
        from seidr_smidja.brunhand.daemon.endpoints.primitives import handle_type_text
        from seidr_smidja.brunhand.models import TypeTextRequest
        parsed = TypeTextRequest.model_validate(req) if isinstance(req, dict) else req
        _active_session_id[0] = getattr(parsed, "session_id", "")

        async def _run() -> Any:
            return handle_type_text(parsed, annall=annall, session_id=_daemon_annall_session_id[0])

        result = await _run_locked(_run())
        return result.model_dump() if hasattr(result, "model_dump") else result

    @app.post("/v1/brunhand/hotkey")
    async def hotkey(req: Any) -> Any:
        from seidr_smidja.brunhand.daemon.endpoints.primitives import handle_hotkey
        from seidr_smidja.brunhand.models import HotkeyRequest
        parsed = HotkeyRequest.model_validate(req) if isinstance(req, dict) else req
        _active_session_id[0] = getattr(parsed, "session_id", "")

        async def _run() -> Any:
            return handle_hotkey(parsed, annall=annall, session_id=_daemon_annall_session_id[0])

        result = await _run_locked(_run())
        return result.model_dump() if hasattr(result, "model_dump") else result

    @app.post("/v1/brunhand/find_window")
    async def find_window(req: Any) -> Any:
        from seidr_smidja.brunhand.daemon.endpoints.primitives import handle_find_window
        from seidr_smidja.brunhand.models import FindWindowRequest
        parsed = FindWindowRequest.model_validate(req) if isinstance(req, dict) else req
        _active_session_id[0] = getattr(parsed, "session_id", "")

        async def _run() -> Any:
            return handle_find_window(parsed, annall=annall, session_id=_daemon_annall_session_id[0])

        result = await _run_locked(_run())
        return result.model_dump() if hasattr(result, "model_dump") else result

    @app.post("/v1/brunhand/wait_for_window")
    async def wait_for_window(req: Any) -> Any:
        from seidr_smidja.brunhand.daemon.endpoints.primitives import handle_wait_for_window
        from seidr_smidja.brunhand.models import WaitForWindowRequest
        parsed = WaitForWindowRequest.model_validate(req) if isinstance(req, dict) else req
        _active_session_id[0] = getattr(parsed, "session_id", "")

        async def _run() -> Any:
            return handle_wait_for_window(parsed, annall=annall, session_id=_daemon_annall_session_id[0])

        result = await _run_locked(_run())
        return result.model_dump() if hasattr(result, "model_dump") else result

    @app.post("/v1/brunhand/vroid/export_vrm")
    async def vroid_export_vrm(req: Any) -> Any:
        from seidr_smidja.brunhand.daemon.endpoints.vroid import handle_vroid_export_vrm
        from seidr_smidja.brunhand.models import VroidExportVrmRequest
        parsed = VroidExportVrmRequest.model_validate(req) if isinstance(req, dict) else req
        _active_session_id[0] = getattr(parsed, "session_id", "")

        async def _run() -> Any:
            return handle_vroid_export_vrm(
                parsed, annall=annall, session_id=_daemon_annall_session_id[0], daemon_cfg=cfg
            )

        result = await _run_locked(_run())
        return result.model_dump() if hasattr(result, "model_dump") else result

    @app.post("/v1/brunhand/vroid/save_project")
    async def vroid_save_project(req: Any) -> Any:
        from seidr_smidja.brunhand.daemon.endpoints.vroid import handle_vroid_save_project
        from seidr_smidja.brunhand.models import VroidSaveProjectRequest
        parsed = VroidSaveProjectRequest.model_validate(req) if isinstance(req, dict) else req
        _active_session_id[0] = getattr(parsed, "session_id", "")

        async def _run() -> Any:
            return handle_vroid_save_project(
                parsed, annall=annall, session_id=_daemon_annall_session_id[0], daemon_cfg=cfg
            )

        result = await _run_locked(_run())
        return result.model_dump() if hasattr(result, "model_dump") else result

    @app.post("/v1/brunhand/vroid/open_project")
    async def vroid_open_project(req: Any) -> Any:
        from seidr_smidja.brunhand.daemon.endpoints.vroid import handle_vroid_open_project
        from seidr_smidja.brunhand.models import VroidOpenProjectRequest
        parsed = VroidOpenProjectRequest.model_validate(req) if isinstance(req, dict) else req
        _active_session_id[0] = getattr(parsed, "session_id", "")

        async def _run() -> Any:
            return handle_vroid_open_project(
                parsed, annall=annall, session_id=_daemon_annall_session_id[0], daemon_cfg=cfg
            )

        result = await _run_locked(_run())
        return result.model_dump() if hasattr(result, "model_dump") else result

    return app


def _get_client_ip(request: Any, trust_proxy_headers: bool = False) -> str:
    """Extract the client IP from the request.

    B-009: X-Forwarded-For is only trusted when trust_proxy_headers=True
    (config: brunhand.daemon.trust_proxy_headers).  In the default Tailscale
    deployment there is no legitimate reverse proxy, so we use the actual
    request.client.host which reflects the real Tailscale peer IP.
    """
    try:
        if trust_proxy_headers:
            forwarded = request.headers.get("x-forwarded-for", "")
            if forwarded:
                return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
    except Exception:
        pass
    return "unknown"


def _log_annall_daemon(
    annall: Any, session_id: str, event_type: str, payload: dict[str, Any]
) -> None:
    if annall is None:
        return
    try:
        from seidr_smidja.annall.port import AnnallEvent
        annall.log_event(session_id, AnnallEvent.info(event_type, payload))
    except Exception:
        pass
