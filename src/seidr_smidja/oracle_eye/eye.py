"""seidr_smidja.oracle_eye.eye — Oracle Eye render orchestration.

D-006: Render failure is soft — return the .vrm + structured warnings.
D-007: Separate Blender subprocess from Forge.
D-003: Uses _internal.blender_runner, does NOT import from forge.

The Oracle Eye calls the render script via the shared Blender runner.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from seidr_smidja._internal.blender_runner import BlenderNotFoundError, run_blender

logger = logging.getLogger(__name__)

_RENDER_SCRIPT = Path(__file__).parent / "scripts" / "render_avatar.py"


class RenderView(str, Enum):
    """Standard render view names.

    The enum is open-ended — keys do NOT embed renderer-specific names
    (e.g., not "blender_eevee_front") so a future renderer can use the same set.
    """

    FRONT = "front"
    THREE_QUARTER = "three_quarter"
    SIDE = "side"
    FACE_CLOSEUP = "face_closeup"
    T_POSE = "t_pose"
    EXPRESSION_SMILE = "expression_smile"
    EXPRESSION_SAD = "expression_sad"
    EXPRESSION_SURPRISED = "expression_surprised"


STANDARD_VIEWS: list[RenderView] = list(RenderView)


class RenderError(RuntimeError):
    """Raised only on non-recoverable Oracle Eye failure.

    A Blender subprocess failure → RenderResult(success=False).
    This exception is for infrastructure failures: renderer not found, output dir
    not writable, etc.
    """

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause


@dataclass
class RenderResult:
    """Result of an Oracle Eye render attempt.

    Attributes:
        success:          True if all requested views rendered successfully.
        render_paths:     Dict of {view_name_string: Path_to_png}.
        renderer_used:    E.g., "blender_eevee".
        resolution:       (width, height) in pixels.
        elapsed_seconds:  Wall-clock time.
        errors:           Human-readable error messages. Empty on full success.
    """

    success: bool
    render_paths: dict[str, Path] = field(default_factory=dict)
    renderer_used: str = "blender_eevee"
    resolution: tuple[int, int] = (1024, 1024)
    elapsed_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)


def list_standard_views() -> list[RenderView]:
    """Return the canonical list of standard render views."""
    return list(STANDARD_VIEWS)


def render(
    vrm_path: Path,
    output_dir: Path,
    views: list[str] | list[RenderView] | None = None,
    config: dict[str, Any] | None = None,
    annall: Any = None,
    session_id: Any = None,
) -> RenderResult:
    """Render preview PNGs from a .vrm file via headless Blender.

    Args:
        vrm_path:   Path to the .vrm file to render.
        output_dir: Directory to write rendered PNGs.
        views:      List of view names/RenderView values. None = full standard set.
        config:     Config dict for Blender path + resolution + view preferences.
        annall:     Optional AnnallPort for event logging.
        session_id: Session ID for Annáll events.

    Returns:
        RenderResult — always returned (D-006 soft failure: never raises for Blender failure).

    Raises:
        RenderError: Only on pre-launch failures (renderer not found, bad output dir).
    """
    start = time.monotonic()

    if not vrm_path.exists():
        raise RenderError(f"VRM file not found: {vrm_path}")

    if not output_dir.exists():
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise RenderError(
                f"Cannot create output directory {output_dir}: {exc}", cause=exc
            ) from exc

    if not _RENDER_SCRIPT.exists():
        raise RenderError(
            f"Oracle Eye render script not found at {_RENDER_SCRIPT}. "
            "This is an installation error."
        )

    # Resolve views list
    view_names: list[str]
    if views is None:
        view_names = [v.value for v in STANDARD_VIEWS]
    else:
        view_names = [
            v.value if isinstance(v, RenderView) else str(v)
            for v in views
        ]

    # Read resolution from config
    cfg_oracle = (config or {}).get("oracle_eye", {})
    resolution_cfg = cfg_oracle.get("resolution", [1024, 1024])
    resolution = (int(resolution_cfg[0]), int(resolution_cfg[1]))

    # Log oracle_eye.started
    _log_annall(
        annall,
        session_id,
        "oracle_eye.started",
        {
            "vrm_path": str(vrm_path),
            "views": view_names,
            "resolution": list(resolution),
            "output_dir": str(output_dir),
        },
    )

    # Build Blender args for the render script
    blender_args = [
        "--vrm",
        str(vrm_path),
        "--views",
        ",".join(view_names),
        "--output",
        str(output_dir),
        "--width",
        str(resolution[0]),
        "--height",
        str(resolution[1]),
    ]

    stdout_lines: list[str] = []

    def on_line(line: str) -> None:
        stdout_lines.append(line)

    try:
        runner_result = run_blender(
            script_path=_RENDER_SCRIPT,
            args=blender_args,
            config=config,
            on_line=on_line,
        )
    except BlenderNotFoundError as exc:
        raise RenderError(
            f"Blender not found — cannot run Oracle Eye: {exc}", cause=exc
        ) from exc
    except OSError as exc:
        raise RenderError(
            f"Failed to launch Blender subprocess for rendering: {exc}", cause=exc
        ) from exc

    elapsed = time.monotonic() - start

    # Collect rendered PNG paths (convention: <view_name>.png in output_dir)
    render_paths: dict[str, Path] = {}
    missing_views: list[str] = []

    for view in view_names:
        png_path = output_dir / f"{view}.png"
        if png_path.exists():
            render_paths[view] = png_path
        else:
            missing_views.append(view)

    success = runner_result.returncode == 0 and not missing_views

    errors: list[str] = []
    if runner_result.returncode != 0:
        errors.append(
            f"Blender render subprocess exited with code {runner_result.returncode}."
        )
    if missing_views:
        errors.append(f"Missing rendered views: {missing_views}")
    if runner_result.timed_out:
        errors.append("Blender render subprocess timed out.")

    event_type = "oracle_eye.completed" if success else "oracle_eye.failed"
    _log_annall(
        annall,
        session_id,
        event_type,
        {
            "success": success,
            "views_rendered": list(render_paths.keys()),
            "views_missing": missing_views,
            "exit_code": runner_result.returncode,
            "elapsed_seconds": elapsed,
            "errors": errors,
        },
    )

    if success:
        logger.info(
            "Oracle Eye: %d/%d views rendered (%.1fs)",
            len(render_paths),
            len(view_names),
            elapsed,
        )
    else:
        logger.warning(
            "Oracle Eye: render incomplete — %d/%d views, exit_code=%d (%.1fs)",
            len(render_paths),
            len(view_names),
            runner_result.returncode,
            elapsed,
        )

    return RenderResult(
        success=success,
        render_paths=render_paths,
        renderer_used="blender_eevee",
        resolution=resolution,
        elapsed_seconds=elapsed,
        errors=errors,
    )


def _log_annall(
    annall: Any, session_id: Any, event_type: str, payload: dict[str, Any]
) -> None:
    """Log to Annáll, swallowing all errors."""
    if annall is None or session_id is None:
        return
    try:
        from seidr_smidja.annall.port import AnnallEvent

        annall.log_event(session_id, AnnallEvent.info(event_type, payload))
    except Exception:
        pass


# ─── Brúarhönd External Render Integration (Additive — D-010) ───────────────
# These classes and the register_external_render() function extend Oracle Eye
# to accept externally-sourced PNG bytes (from Brúarhönd daemon screenshots).
# INVARIANT: They do NOT modify render(), RenderResult, RenderView, or any
# existing public surface. They are purely additive.
# See: docs/features/brunhand/ARCHITECTURE.md §VII Vision Integration (Ljósbrú)


@dataclass
class ExternalRenderMetadata:
    """Metadata for an externally-sourced render (e.g., a Brúarhönd screenshot).

    Attributes:
        host:            Tailscale host the screenshot came from.
        session_id:      Tengslastig session ID.
        agent_id:        Agent identity string.
        captured_at:     ISO 8601 UTC timestamp from the daemon.
        screen_geometry: Monitor geometry reported by the daemon (optional).
        source:          Source identifier, e.g. "brunhand".
    """

    host: str = ""
    session_id: str = ""
    agent_id: str = ""
    captured_at: str = ""
    source: str = "brunhand"
    screen_geometry: dict[str, Any] | None = None


@dataclass
class ExternalRenderResult:
    """Result of register_external_render().

    Attributes:
        view_path:   Path to the written PNG file. None if output_dir is not configured.
        view_name:   Canonical view name: "brunhand/live/<session_id>/<timestamp>".
        png_bytes:   The original PNG bytes (echoed back for immediate use).
        byte_count:  Size of the PNG data in bytes.
    """

    view_path: Path | None
    view_name: str
    png_bytes: bytes
    byte_count: int


def register_external_render(
    source: str,
    view: str,
    png_bytes: bytes,
    metadata: ExternalRenderMetadata | None = None,
    output_dir: Path | None = None,
    run_id: str | None = None,
    annall: Any = None,
    annall_session_id: Any = None,
) -> ExternalRenderResult:
    """Register an externally-sourced PNG as a named Oracle Eye render.

    Called by Ljósbrú (brunhand/client/oracle_channel.py) when the Brúarhönd
    client receives a screenshot response from the daemon. This ensures remote
    VRoid Studio screenshots arrive through the same Oracle Eye channel as
    headless Blender renders — agents see one unified vision stream.

    INVARIANT: This function never modifies render(), RenderResult, or any
    existing Oracle Eye behavior. It is purely additive.

    Args:
        source:           Source identifier, e.g. "brunhand".
        view:             View name, e.g. "live/<session_id>/<timestamp>".
        png_bytes:        Raw PNG bytes to register.
        metadata:         Optional ExternalRenderMetadata for Annáll context.
        output_dir:       Optional directory to write the PNG. If None, PNG is
                          in-memory only (view_path == None in result).
        run_id:           Optional run_id for Mode C cross-correlation.
        annall:           Optional AnnallPort for telemetry.
        annall_session_id: Session ID for the Annáll event.

    Returns:
        ExternalRenderResult with view_path, view_name, png_bytes, byte_count.

    Note:
        Screenshot bytes are NEVER logged to Annáll — only metadata
        (byte count, view_name, host) is recorded. This is an invariant.
    """
    meta = metadata or ExternalRenderMetadata()
    canonical_view_name = f"{source}/{view}"
    view_path: Path | None = None
    byte_count = len(png_bytes)

    # Write to disk if output_dir provided
    if output_dir is not None:
        try:
            # Build subdirectory: output_dir/external_renders/<source>/<safe_view>/
            # Replace slashes in view name with OS-safe underscores for directory structure
            safe_view = view.replace("/", "_").replace("\\", "_")
            render_subdir = output_dir / "external_renders" / source
            render_subdir.mkdir(parents=True, exist_ok=True)
            view_path = render_subdir / f"{safe_view}.png"
            view_path.write_bytes(png_bytes)
        except Exception as exc:
            logger.warning(
                "Oracle Eye: could not write external render to disk: %s", exc
            )
            view_path = None

    # Log to Annáll — metadata only, never raw bytes
    _log_annall(
        annall,
        annall_session_id,
        "oracle_eye.external_render.registered",
        {
            "source": source,
            "view": view,
            "canonical_view_name": canonical_view_name,
            "byte_count": byte_count,
            "host": meta.host,
            "session_id": meta.session_id,
            "agent_id": meta.agent_id,
            "captured_at": meta.captured_at,
            "view_path": str(view_path) if view_path else None,
            "run_id": run_id,
        },
    )

    logger.debug(
        "Oracle Eye: external render registered — %s (%d bytes)",
        canonical_view_name,
        byte_count,
    )

    return ExternalRenderResult(
        view_path=view_path,
        view_name=canonical_view_name,
        png_bytes=png_bytes,
        byte_count=byte_count,
    )
