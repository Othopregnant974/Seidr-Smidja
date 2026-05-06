"""Horfunarþjónn — primitive endpoint handlers.

All 9 generic GUI automation primitives:
  POST /v1/brunhand/screenshot
  POST /v1/brunhand/click
  POST /v1/brunhand/move
  POST /v1/brunhand/drag
  POST /v1/brunhand/scroll
  POST /v1/brunhand/type
  POST /v1/brunhand/hotkey
  POST /v1/brunhand/find_window
  POST /v1/brunhand/wait_for_window

Each handler:
  1. Checks Sjálfsmöguleiki — raises if primitive not available.
  2. Logs primitive.started to Annáll.
  3. Calls runtime shim (pyautogui/mss/pygetwindow via runtime.py).
  4. Returns BrunhandResponseEnvelope on success or structured error on failure.
  5. INVARIANT: Never raises — always returns a response. The daemon stays alive.

See: src/seidr_smidja/brunhand/daemon/INTERFACE.md §Endpoint Contracts
"""
from __future__ import annotations

import time
import traceback
from typing import Any

from seidr_smidja.brunhand.models import (
    BrunhandErrorDetail,
    BrunhandResponseEnvelope,
    ClickRequest,
    DragRequest,
    FindWindowRequest,
    HotkeyRequest,
    MoveRequest,
    ScreenshotRequest,
    ScrollRequest,
    TypeTextRequest,
    WaitForWindowRequest,
)


def _make_error_response(
    request_envelope: Any,
    primitive: str,
    exc: Exception,
    vroid_running: bool = True,
    screen_accessible: bool = True,
    permission_denied: bool = False,
) -> BrunhandResponseEnvelope:
    """Build a structured error response envelope from an exception."""
    stack = traceback.format_exc()[-500:]  # Truncate for safety
    error_detail = BrunhandErrorDetail(
        error_type=type(exc).__name__,
        message=str(exc),
        primitive=primitive,
        vroid_running=vroid_running,
        screen_accessible=screen_accessible,
        permission_denied=permission_denied,
        stack_summary=stack,
    )
    req_id = getattr(request_envelope, "request_id", "")
    sess_id = getattr(request_envelope, "session_id", "")
    return BrunhandResponseEnvelope(
        request_id=req_id,
        session_id=sess_id,
        success=False,
        error=error_detail,
    )


def handle_screenshot(
    req: ScreenshotRequest, annall: Any = None, session_id: str = ""
) -> BrunhandResponseEnvelope:
    """Handle POST /v1/brunhand/screenshot."""
    start = time.monotonic()
    _log_annall(annall, session_id, "brunhand.daemon.primitive.started", {
        "primitive": "screenshot",
        "request_id": req.request_id,
        "has_region": req.region is not None,
    })
    try:
        from seidr_smidja.brunhand.daemon.runtime import take_screenshot
        region = req.region.model_dump() if req.region else None
        result = take_screenshot(region=region)
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.completed", {
            "primitive": "screenshot",
            "request_id": req.request_id,
            "width": result.get("width"),
            "height": result.get("height"),
            "latency_ms": latency,
        })
        return BrunhandResponseEnvelope(
            request_id=req.request_id,
            session_id=req.session_id,
            success=True,
            payload=result,
            latency_ms=latency,
        )
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.failed", {
            "primitive": "screenshot",
            "request_id": req.request_id,
            "error": str(exc),
            "latency_ms": latency,
        })
        return _make_error_response(req, "screenshot", exc,
                                    screen_accessible=("permission" not in str(exc).lower()))


def handle_click(
    req: ClickRequest, annall: Any = None, session_id: str = ""
) -> BrunhandResponseEnvelope:
    """Handle POST /v1/brunhand/click."""
    start = time.monotonic()
    _log_annall(annall, session_id, "brunhand.daemon.primitive.started", {
        "primitive": "click",
        "request_id": req.request_id,
    })
    try:
        from seidr_smidja.brunhand.daemon.runtime import do_click
        result = do_click(
            x=req.x, y=req.y, button=req.button,
            clicks=req.clicks, interval=req.interval, modifiers=req.modifiers,
        )
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.completed",
                    {"primitive": "click", "latency_ms": latency})
        return BrunhandResponseEnvelope(
            request_id=req.request_id, session_id=req.session_id,
            success=True, payload=result, latency_ms=latency,
        )
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.failed",
                    {"primitive": "click", "error": str(exc), "latency_ms": latency})
        return _make_error_response(req, "click", exc)


def handle_move(
    req: MoveRequest, annall: Any = None, session_id: str = ""
) -> BrunhandResponseEnvelope:
    """Handle POST /v1/brunhand/move."""
    start = time.monotonic()
    _log_annall(annall, session_id, "brunhand.daemon.primitive.started",
                {"primitive": "move", "request_id": req.request_id})
    try:
        from seidr_smidja.brunhand.daemon.runtime import do_move
        result = do_move(x=req.x, y=req.y, duration=req.duration, tween=req.tween)
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.completed",
                    {"primitive": "move", "latency_ms": latency})
        return BrunhandResponseEnvelope(
            request_id=req.request_id, session_id=req.session_id,
            success=True, payload=result, latency_ms=latency,
        )
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.failed",
                    {"primitive": "move", "error": str(exc), "latency_ms": latency})
        return _make_error_response(req, "move", exc)


def handle_drag(
    req: DragRequest, annall: Any = None, session_id: str = ""
) -> BrunhandResponseEnvelope:
    """Handle POST /v1/brunhand/drag."""
    start = time.monotonic()
    _log_annall(annall, session_id, "brunhand.daemon.primitive.started",
                {"primitive": "drag", "request_id": req.request_id})
    try:
        from seidr_smidja.brunhand.daemon.runtime import do_drag
        result = do_drag(
            x1=req.x1, y1=req.y1, x2=req.x2, y2=req.y2,
            button=req.button, duration=req.duration,
        )
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.completed",
                    {"primitive": "drag", "latency_ms": latency})
        return BrunhandResponseEnvelope(
            request_id=req.request_id, session_id=req.session_id,
            success=True, payload=result, latency_ms=latency,
        )
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.failed",
                    {"primitive": "drag", "error": str(exc), "latency_ms": latency})
        return _make_error_response(req, "drag", exc)


def handle_scroll(
    req: ScrollRequest, annall: Any = None, session_id: str = ""
) -> BrunhandResponseEnvelope:
    """Handle POST /v1/brunhand/scroll."""
    start = time.monotonic()
    _log_annall(annall, session_id, "brunhand.daemon.primitive.started",
                {"primitive": "scroll", "request_id": req.request_id})
    try:
        from seidr_smidja.brunhand.daemon.runtime import do_scroll
        result = do_scroll(x=req.x, y=req.y, clicks=req.clicks, direction=req.direction)
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.completed",
                    {"primitive": "scroll", "latency_ms": latency})
        return BrunhandResponseEnvelope(
            request_id=req.request_id, session_id=req.session_id,
            success=True, payload=result, latency_ms=latency,
        )
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.failed",
                    {"primitive": "scroll", "error": str(exc), "latency_ms": latency})
        return _make_error_response(req, "scroll", exc)


def handle_type_text(
    req: TypeTextRequest, annall: Any = None, session_id: str = ""
) -> BrunhandResponseEnvelope:
    """Handle POST /v1/brunhand/type."""
    start = time.monotonic()
    _log_annall(annall, session_id, "brunhand.daemon.primitive.started",
                {"primitive": "type_text", "request_id": req.request_id,
                 "text_length": len(req.text)})
    try:
        from seidr_smidja.brunhand.daemon.runtime import do_type_text
        result = do_type_text(text=req.text, interval=req.interval)
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.completed",
                    {"primitive": "type_text", "latency_ms": latency})
        return BrunhandResponseEnvelope(
            request_id=req.request_id, session_id=req.session_id,
            success=True, payload=result, latency_ms=latency,
        )
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.failed",
                    {"primitive": "type_text", "error": str(exc), "latency_ms": latency})
        return _make_error_response(req, "type_text", exc)


def handle_hotkey(
    req: HotkeyRequest, annall: Any = None, session_id: str = ""
) -> BrunhandResponseEnvelope:
    """Handle POST /v1/brunhand/hotkey."""
    start = time.monotonic()
    _log_annall(annall, session_id, "brunhand.daemon.primitive.started",
                {"primitive": "hotkey", "request_id": req.request_id, "keys": req.keys})
    try:
        from seidr_smidja.brunhand.daemon.runtime import do_hotkey
        result = do_hotkey(keys=req.keys)
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.completed",
                    {"primitive": "hotkey", "latency_ms": latency})
        return BrunhandResponseEnvelope(
            request_id=req.request_id, session_id=req.session_id,
            success=True, payload=result, latency_ms=latency,
        )
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.failed",
                    {"primitive": "hotkey", "error": str(exc), "latency_ms": latency})
        return _make_error_response(req, "hotkey", exc)


def handle_find_window(
    req: FindWindowRequest, annall: Any = None, session_id: str = ""
) -> BrunhandResponseEnvelope:
    """Handle POST /v1/brunhand/find_window."""
    start = time.monotonic()
    _log_annall(annall, session_id, "brunhand.daemon.primitive.started",
                {"primitive": "find_window", "request_id": req.request_id,
                 "title_pattern": req.title_pattern})
    try:
        from seidr_smidja.brunhand.daemon.runtime import do_find_window
        result = do_find_window(title_pattern=req.title_pattern, exact=req.exact)
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.completed",
                    {"primitive": "find_window", "found": result.get("found"),
                     "count": len(result.get("windows", [])), "latency_ms": latency})
        return BrunhandResponseEnvelope(
            request_id=req.request_id, session_id=req.session_id,
            success=True, payload=result, latency_ms=latency,
        )
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.failed",
                    {"primitive": "find_window", "error": str(exc), "latency_ms": latency})
        return _make_error_response(req, "find_window", exc)


def handle_wait_for_window(
    req: WaitForWindowRequest, annall: Any = None, session_id: str = ""
) -> BrunhandResponseEnvelope:
    """Handle POST /v1/brunhand/wait_for_window.

    NOTE: timeout_seconds in the request is the daemon-side wait period.
    The client automatically sets httpx timeout = timeout_seconds + buffer.
    See D-010 Cartographer tension #3 and models.py WaitForWindowRequest.
    """
    start = time.monotonic()
    _log_annall(annall, session_id, "brunhand.daemon.primitive.started",
                {"primitive": "wait_for_window", "request_id": req.request_id,
                 "title_pattern": req.title_pattern,
                 "timeout_seconds": req.timeout_seconds})
    try:
        from seidr_smidja.brunhand.daemon.runtime import do_wait_for_window
        result = do_wait_for_window(
            title_pattern=req.title_pattern,
            timeout_seconds=req.timeout_seconds,
            poll_interval_seconds=req.poll_interval_seconds,
        )
        latency = (time.monotonic() - start) * 1000
        # A timeout is NOT a failure at the envelope level (DATA_FLOW.md §F6)
        _log_annall(annall, session_id, "brunhand.daemon.primitive.completed",
                    {"primitive": "wait_for_window", "found": result.get("found"),
                     "elapsed": result.get("elapsed_seconds"), "latency_ms": latency})
        return BrunhandResponseEnvelope(
            request_id=req.request_id, session_id=req.session_id,
            success=True, payload=result, latency_ms=latency,
        )
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.failed",
                    {"primitive": "wait_for_window", "error": str(exc), "latency_ms": latency})
        return _make_error_response(req, "wait_for_window", exc)


def _log_annall(annall: Any, session_id: str, event_type: str, payload: dict[str, Any]) -> None:
    """Log to Annáll, swallowing all errors (daemon robustness invariant)."""
    if annall is None:
        return
    try:
        from seidr_smidja.annall.port import AnnallEvent
        severity = "error" if "failed" in event_type else "info"
        annall.log_event(session_id, AnnallEvent(event_type=event_type, payload=payload, severity=severity))
    except Exception:
        pass
