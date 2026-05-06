"""Horfunarþjónn — VRoid-specific high-level endpoint handlers.

  POST /v1/brunhand/vroid/export_vrm
  POST /v1/brunhand/vroid/save_project
  POST /v1/brunhand/vroid/open_project

These are thin coordinate-and-hotkey sequences targeting VRoid Studio's GUI.
They depend on VRoid Studio being running and in the foreground.
VRoid Studio version sensitivity applies — see D-010 Consequences.

B-002: Path traversal is rejected at the runtime layer via _validate_path_in_root().
       ValueError from that function is caught here and returned as a structured
       'path_security_error' response (never propagates to the caller as a crash).

B-003: vroid_export_vrm and vroid_open_project now type the validated path into the
       OS file dialog (see runtime.py).  The runtime returns success=False if the
       file did not appear after the dialog was confirmed.

INVARIANT: Never raises — always returns a structured response.
See: docs/features/brunhand/ARCHITECTURE.md §III Endpoint Groups
"""
from __future__ import annotations

import time
import traceback
from typing import Any

from seidr_smidja.brunhand.models import (
    BrunhandErrorDetail,
    BrunhandResponseEnvelope,
    VroidExportVrmRequest,
    VroidOpenProjectRequest,
    VroidSaveProjectRequest,
)


def handle_vroid_export_vrm(
    req: VroidExportVrmRequest, annall: Any = None, session_id: str = "", daemon_cfg: dict[str, Any] | None = None
) -> BrunhandResponseEnvelope:
    """Handle POST /v1/brunhand/vroid/export_vrm."""
    start = time.monotonic()
    cfg = daemon_cfg or {}
    export_root = cfg.get("export_root", "exports")

    # B-002: Validate path BEFORE any runtime/VRoid interaction.
    # Done at the endpoint layer so traversal is rejected even when pyautogui is absent.
    try:
        from seidr_smidja.brunhand.daemon.runtime import _validate_path_in_root
        _validate_path_in_root(req.output_path, export_root)
    except ValueError as exc:
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.failed", {
            "primitive": "vroid_export_vrm", "error": "path_security_error",
            "latency_ms": latency,
        })
        return BrunhandResponseEnvelope(
            request_id=req.request_id, session_id=req.session_id,
            success=False,
            error=BrunhandErrorDetail(
                error_type="path_security_error",
                message=str(exc),
                primitive="vroid_export_vrm",
            ),
            latency_ms=latency,
        )

    _log_annall(annall, session_id, "brunhand.daemon.primitive.started", {
        "primitive": "vroid_export_vrm",
        "request_id": req.request_id,
        "output_path": req.output_path,
    })
    try:
        from seidr_smidja.brunhand.daemon.runtime import is_vroid_running, vroid_export_vrm
        if not is_vroid_running():
            raise VroidNotRunningRuntimeError("VRoid Studio is not running.")
        result = vroid_export_vrm(
            output_path=req.output_path,
            overwrite=req.overwrite,
            wait_timeout_seconds=req.wait_timeout_seconds,
            export_root=export_root,
        )
        latency = (time.monotonic() - start) * 1000
        # B-003: runtime may return success=False if file did not appear on disk.
        # Propagate that as a failure envelope rather than claiming success.
        if not result.get("success", True):
            _log_annall(annall, session_id, "brunhand.daemon.primitive.failed", {
                "primitive": "vroid_export_vrm", "latency_ms": latency,
                "reason": result.get("error", "file not verified"),
                "steps": result.get("steps_executed"),
            })
            return BrunhandResponseEnvelope(
                request_id=req.request_id, session_id=req.session_id,
                success=False,
                error=BrunhandErrorDetail(
                    error_type="VroidExportUnverified",
                    message=result.get("error", "Export dialog confirmed but file not found on disk."),
                    primitive="vroid_export_vrm",
                ),
                latency_ms=latency,
            )
        _log_annall(annall, session_id, "brunhand.daemon.primitive.completed", {
            "primitive": "vroid_export_vrm", "latency_ms": latency,
            "steps": result.get("steps_executed"),
        })
        return BrunhandResponseEnvelope(
            request_id=req.request_id, session_id=req.session_id,
            success=True, payload=result, latency_ms=latency,
        )
    except ValueError as exc:
        # B-002: path traversal — _validate_path_in_root raised ValueError
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.failed", {
            "primitive": "vroid_export_vrm", "error": "path_security_error",
            "latency_ms": latency,
        })
        return BrunhandResponseEnvelope(
            request_id=req.request_id, session_id=req.session_id,
            success=False,
            error=BrunhandErrorDetail(
                error_type="path_security_error",
                message=str(exc),
                primitive="vroid_export_vrm",
            ),
            latency_ms=latency,
        )
    except VroidNotRunningRuntimeError as exc:
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.failed", {
            "primitive": "vroid_export_vrm", "vroid_running": False,
            "error": str(exc), "latency_ms": latency,
        })
        return BrunhandResponseEnvelope(
            request_id=req.request_id, session_id=req.session_id,
            success=False,
            error=BrunhandErrorDetail(
                error_type="VroidNotRunningError",
                message=str(exc),
                primitive="vroid_export_vrm",
                vroid_running=False,
            ),
            latency_ms=latency,
        )
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        stack = traceback.format_exc()[-500:]
        _log_annall(annall, session_id, "brunhand.daemon.primitive.failed", {
            "primitive": "vroid_export_vrm", "error": str(exc), "latency_ms": latency,
        })
        return BrunhandResponseEnvelope(
            request_id=req.request_id, session_id=req.session_id,
            success=False,
            error=BrunhandErrorDetail(
                error_type=type(exc).__name__,
                message=str(exc),
                primitive="vroid_export_vrm",
                stack_summary=stack,
            ),
            latency_ms=latency,
        )


def handle_vroid_save_project(
    req: VroidSaveProjectRequest, annall: Any = None, session_id: str = "", daemon_cfg: dict[str, Any] | None = None
) -> BrunhandResponseEnvelope:
    """Handle POST /v1/brunhand/vroid/save_project."""
    start = time.monotonic()
    _log_annall(annall, session_id, "brunhand.daemon.primitive.started", {
        "primitive": "vroid_save_project", "request_id": req.request_id,
    })
    try:
        from seidr_smidja.brunhand.daemon.runtime import is_vroid_running, vroid_save_project
        if not is_vroid_running():
            raise VroidNotRunningRuntimeError("VRoid Studio is not running.")
        result = vroid_save_project()
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.completed",
                    {"primitive": "vroid_save_project", "latency_ms": latency})
        return BrunhandResponseEnvelope(
            request_id=req.request_id, session_id=req.session_id,
            success=True, payload=result, latency_ms=latency,
        )
    except VroidNotRunningRuntimeError as exc:
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.failed",
                    {"primitive": "vroid_save_project", "vroid_running": False, "error": str(exc)})
        return BrunhandResponseEnvelope(
            request_id=req.request_id, session_id=req.session_id, success=False,
            error=BrunhandErrorDetail(
                error_type="VroidNotRunningError", message=str(exc),
                primitive="vroid_save_project", vroid_running=False,
            ),
            latency_ms=latency,
        )
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        stack = traceback.format_exc()[-500:]
        _log_annall(annall, session_id, "brunhand.daemon.primitive.failed",
                    {"primitive": "vroid_save_project", "error": str(exc)})
        return BrunhandResponseEnvelope(
            request_id=req.request_id, session_id=req.session_id, success=False,
            error=BrunhandErrorDetail(
                error_type=type(exc).__name__, message=str(exc),
                primitive="vroid_save_project", stack_summary=stack,
            ),
            latency_ms=latency,
        )


def handle_vroid_open_project(
    req: VroidOpenProjectRequest, annall: Any = None, session_id: str = "", daemon_cfg: dict[str, Any] | None = None
) -> BrunhandResponseEnvelope:
    """Handle POST /v1/brunhand/vroid/open_project."""
    start = time.monotonic()
    cfg = daemon_cfg or {}
    project_root = cfg.get("project_root", "projects")

    # B-002: Validate path BEFORE any runtime/VRoid interaction.
    try:
        from seidr_smidja.brunhand.daemon.runtime import _validate_path_in_root
        _validate_path_in_root(req.project_path, project_root)
    except ValueError as exc:
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.failed",
                    {"primitive": "vroid_open_project", "error": "path_security_error",
                     "latency_ms": latency})
        return BrunhandResponseEnvelope(
            request_id=req.request_id, session_id=req.session_id, success=False,
            error=BrunhandErrorDetail(
                error_type="path_security_error", message=str(exc),
                primitive="vroid_open_project",
            ),
            latency_ms=latency,
        )

    _log_annall(annall, session_id, "brunhand.daemon.primitive.started", {
        "primitive": "vroid_open_project", "request_id": req.request_id,
        "project_path": req.project_path,
    })
    try:
        from seidr_smidja.brunhand.daemon.runtime import is_vroid_running, vroid_open_project
        if not is_vroid_running():
            raise VroidNotRunningRuntimeError("VRoid Studio is not running.")
        result = vroid_open_project(
            project_path=req.project_path,
            wait_timeout_seconds=req.wait_timeout_seconds,
            project_root=project_root,
        )
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.completed",
                    {"primitive": "vroid_open_project", "latency_ms": latency})
        return BrunhandResponseEnvelope(
            request_id=req.request_id, session_id=req.session_id,
            success=True, payload=result, latency_ms=latency,
        )
    except ValueError as exc:
        # B-002: path traversal — _validate_path_in_root raised ValueError
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.failed",
                    {"primitive": "vroid_open_project", "error": "path_security_error",
                     "latency_ms": latency})
        return BrunhandResponseEnvelope(
            request_id=req.request_id, session_id=req.session_id, success=False,
            error=BrunhandErrorDetail(
                error_type="path_security_error", message=str(exc),
                primitive="vroid_open_project",
            ),
            latency_ms=latency,
        )
    except VroidNotRunningRuntimeError as exc:
        latency = (time.monotonic() - start) * 1000
        _log_annall(annall, session_id, "brunhand.daemon.primitive.failed",
                    {"primitive": "vroid_open_project", "vroid_running": False, "error": str(exc)})
        return BrunhandResponseEnvelope(
            request_id=req.request_id, session_id=req.session_id, success=False,
            error=BrunhandErrorDetail(
                error_type="VroidNotRunningError", message=str(exc),
                primitive="vroid_open_project", vroid_running=False,
            ),
            latency_ms=latency,
        )
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        stack = traceback.format_exc()[-500:]
        _log_annall(annall, session_id, "brunhand.daemon.primitive.failed",
                    {"primitive": "vroid_open_project", "error": str(exc)})
        return BrunhandResponseEnvelope(
            request_id=req.request_id, session_id=req.session_id, success=False,
            error=BrunhandErrorDetail(
                error_type=type(exc).__name__, message=str(exc),
                primitive="vroid_open_project", stack_summary=stack,
            ),
            latency_ms=latency,
        )


class VroidNotRunningRuntimeError(RuntimeError):
    """Internal: VRoid Studio not detected on this daemon host."""


def _log_annall(annall: Any, session_id: str, event_type: str, payload: dict[str, Any]) -> None:
    """Log to Annáll, swallowing all errors."""
    if annall is None:
        return
    try:
        from seidr_smidja.annall.port import AnnallEvent
        severity = "error" if "failed" in event_type else "info"
        annall.log_event(session_id, AnnallEvent(event_type=event_type, payload=payload, severity=severity))
    except Exception:
        pass
