"""seidr_smidja.brunhand.models — Shared Pydantic v2 request/response models.

These models are used by BOTH the daemon (Horfunarþjónn) and the client (Hengilherðir).
They define the HTTP API contract as data structures; see daemon/INTERFACE.md for the
full endpoint contracts.

No GUI imports. No pyautogui. No platform-conditional code.
This module must be importable on any platform with only pydantic installed.

See: src/seidr_smidja/brunhand/daemon/INTERFACE.md
See: src/seidr_smidja/brunhand/client/INTERFACE.md
"""
from __future__ import annotations

import datetime as _dt
import uuid
from typing import Any

from pydantic import BaseModel, Field

# ─── Utility ────────────────────────────────────────────────────────────────


def _new_uuid() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


def _now_utc() -> str:
    """Return current UTC time as ISO 8601 string."""
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat()  # noqa: UP017


# ─── Shared Geometry ─────────────────────────────────────────────────────────


class ScreenRect(BaseModel):
    """A rectangular screen region."""

    left: int = 0
    top: int = 0
    width: int = 1920
    height: int = 1080
    monitor_index: int = 0


# ─── Request Envelope ────────────────────────────────────────────────────────


class BrunhandRequestEnvelope(BaseModel):
    """Universal fields present in every authenticated POST request.

    These fields are mandatory for Annáll correlation and session tracking.
    They are separate from (and included alongside) the primitive-specific fields.
    """

    request_id: str = Field(default_factory=_new_uuid, description="UUID per-request; echoed in response")
    session_id: str = Field(default="", description="Tengslastig session UUID")
    agent_id: str = Field(default="unknown", description="Agent identity string for Annáll")
    timeout_seconds: float | None = Field(
        default=None,
        description=(
            "Optional: per-request primitive timeout. When set, the client "
            "automatically extends its httpx request timeout to "
            "timeout_seconds + request_timeout_buffer (see D-010 tension #3)."
        ),
    )


# ─── Response Envelope ───────────────────────────────────────────────────────


class BrunhandErrorDetail(BaseModel):
    """Structured error detail included in failed responses.

    Present when BrunhandResponseEnvelope.success == False.
    """

    error_type: str = ""
    message: str = ""
    primitive: str = ""
    vroid_running: bool = True
    screen_accessible: bool = True
    permission_denied: bool = False
    platform: str = ""
    stack_summary: str | None = None


class BrunhandResponseEnvelope(BaseModel):
    """Universal response wrapper for all daemon endpoints."""

    request_id: str = ""
    session_id: str = ""
    success: bool = True
    payload: dict[str, Any] = Field(default_factory=dict)
    error: BrunhandErrorDetail | None = None
    daemon_timestamp: str = Field(default_factory=_now_utc)
    latency_ms: float = 0.0
    daemon_version: str = "0.1.0"


# ─── Health ───────────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    """Response for GET /v1/brunhand/health (no auth required)."""

    daemon_version: str = "0.1.0"
    os_name: str = ""
    uptime_seconds: float = 0.0
    status: str = "ok"


# ─── Capabilities ────────────────────────────────────────────────────────────


class PrimitiveStatus(BaseModel):
    """Availability and quality of a single primitive on the current platform."""

    available: bool = False
    library: str = ""
    degraded: bool = False
    degraded_reason: str | None = None
    notes: str | None = None


class CapabilitiesManifest(BaseModel):
    """Full platform capabilities manifest from Sjálfsmöguleiki."""

    daemon_version: str = "0.1.0"
    os_name: str = ""
    os_version: str = ""
    screen_geometry: list[ScreenRect] = Field(default_factory=list)
    primitives: dict[str, PrimitiveStatus] = Field(default_factory=dict)
    probed_at: str = Field(default_factory=_now_utc)


# ─── Screenshot ───────────────────────────────────────────────────────────────


class ScreenshotRequest(BrunhandRequestEnvelope):
    """POST /v1/brunhand/screenshot — capture full screen or region.

    B-012: monitor_index selects which physical monitor to capture when region
    is not specified.  0 = primary monitor (default).  Ignored if region is set.
    """

    region: ScreenRect | None = Field(
        default=None,
        description="Capture region. If null, captures the full selected monitor.",
    )
    monitor_index: int = Field(
        default=0,
        ge=0,
        description=(
            "0-based monitor index. 0 = primary monitor. "
            "Ignored when region is specified. B-012 multi-monitor support."
        ),
    )


class ScreenshotPayload(BaseModel):
    """Payload inside BrunhandResponseEnvelope for a screenshot."""

    png_bytes_b64: str = Field(description="Base64-encoded PNG bytes")
    width: int = 0
    height: int = 0
    captured_at: str = Field(default_factory=_now_utc)
    monitor_index: int = 0


# ─── Click ────────────────────────────────────────────────────────────────────


class ClickRequest(BrunhandRequestEnvelope):
    """POST /v1/brunhand/click — mouse click at coordinates."""

    x: int
    y: int
    button: str = "left"
    clicks: int = 1
    interval: float = 0.0
    modifiers: list[str] = Field(default_factory=list)


class ClickPayload(BaseModel):
    """Payload for a successful click."""

    x: int = 0
    y: int = 0
    button: str = "left"
    clicks_delivered: int = 1


# ─── Move ─────────────────────────────────────────────────────────────────────


class MoveRequest(BrunhandRequestEnvelope):
    """POST /v1/brunhand/move — mouse move to coordinates."""

    x: int
    y: int
    duration: float = 0.25
    tween: str = "linear"


class MovePayload(BaseModel):
    x: int = 0
    y: int = 0


# ─── Drag ─────────────────────────────────────────────────────────────────────


class DragRequest(BrunhandRequestEnvelope):
    """POST /v1/brunhand/drag — mouse drag from one point to another."""

    x1: int
    y1: int
    x2: int
    y2: int
    button: str = "left"
    duration: float = 0.5


class DragPayload(BaseModel):
    from_pos: list[int] = Field(default_factory=list)
    to_pos: list[int] = Field(default_factory=list)


# ─── Scroll ───────────────────────────────────────────────────────────────────


class ScrollRequest(BrunhandRequestEnvelope):
    """POST /v1/brunhand/scroll — mouse wheel scroll."""

    x: int
    y: int
    clicks: int
    direction: str = "down"


class ScrollPayload(BaseModel):
    x: int = 0
    y: int = 0
    clicks: int = 0
    direction: str = "down"


# ─── Type Text ────────────────────────────────────────────────────────────────


class TypeTextRequest(BrunhandRequestEnvelope):
    """POST /v1/brunhand/type — type a text string.

    B-015: text is capped at 10,000 characters to prevent runaway typewrite() calls
    that would block the daemon's thread pool for extended periods.  For longer
    sequences split the text across multiple type_text calls.
    """

    text: str = Field(
        max_length=10000,
        description=(
            "Text to type. Maximum 10,000 characters per call. "
            "Split longer sequences across multiple type_text requests."
        ),
    )
    interval: float = 0.05


class TypeTextPayload(BaseModel):
    characters_typed: int = 0


# ─── Hotkey ───────────────────────────────────────────────────────────────────


class HotkeyRequest(BrunhandRequestEnvelope):
    """POST /v1/brunhand/hotkey — press a key combination."""

    keys: list[str]


class HotkeyPayload(BaseModel):
    keys: list[str] = Field(default_factory=list)


# ─── Find Window ─────────────────────────────────────────────────────────────


class FindWindowRequest(BrunhandRequestEnvelope):
    """POST /v1/brunhand/find_window — find window geometry by title pattern."""

    title_pattern: str
    exact: bool = False


class WindowInfo(BaseModel):
    """Geometry and state of a single window."""

    title: str = ""
    left: int = 0
    top: int = 0
    width: int = 0
    height: int = 0
    is_foreground: bool = False


class FindWindowPayload(BaseModel):
    found: bool = False
    windows: list[WindowInfo] = Field(default_factory=list)


# ─── Wait For Window ─────────────────────────────────────────────────────────


class WaitForWindowRequest(BrunhandRequestEnvelope):
    """POST /v1/brunhand/wait_for_window — block until a window appears.

    IMPORTANT: The client automatically sets httpx timeout = timeout_seconds + buffer
    so the HTTP connection never times out before the primitive finishes waiting.
    This is the D-010 Cartographer tension #3 resolution.
    """

    title_pattern: str
    timeout_seconds: float = 30.0  # type: ignore[assignment]
    poll_interval_seconds: float = 0.5


class WaitForWindowPayload(BaseModel):
    found: bool = False
    elapsed_seconds: float = 0.0
    window: WindowInfo | None = None


# ─── VRoid High-Level Primitives ─────────────────────────────────────────────


class VroidExportVrmRequest(BrunhandRequestEnvelope):
    """POST /v1/brunhand/vroid/export_vrm — drive VRoid Studio export flow."""

    output_path: str
    overwrite: bool = True
    wait_timeout_seconds: float = 120.0


class VroidExportPayload(BaseModel):
    exported_path: str = ""
    elapsed_seconds: float = 0.0
    steps_executed: list[str] = Field(default_factory=list)


class VroidSaveProjectRequest(BrunhandRequestEnvelope):
    """POST /v1/brunhand/vroid/save_project — save current .vroid project."""


class VroidSavePayload(BaseModel):
    elapsed_seconds: float = 0.0
    steps_executed: list[str] = Field(default_factory=list)


class VroidOpenProjectRequest(BrunhandRequestEnvelope):
    """POST /v1/brunhand/vroid/open_project — open a .vroid project file."""

    project_path: str
    wait_timeout_seconds: float = 60.0


class VroidOpenPayload(BaseModel):
    opened_path: str = ""
    elapsed_seconds: float = 0.0
    steps_executed: list[str] = Field(default_factory=list)


# ─── Bridge-Level Dispatch Models ────────────────────────────────────────────
# These are used by bridges.core.brunhand_dispatch() and the Bridge sub-modules.
# They are NOT the daemon's HTTP models — they are the forge-internal dispatch contract.


class PrimitiveCall(BaseModel):
    """A single primitive invocation within a BrunhandDispatchRequest."""

    primitive: str = Field(description="Primitive name e.g. 'screenshot', 'click'")
    params: dict[str, Any] = Field(default_factory=dict, description="Primitive-specific parameters")


class PrimitiveResult(BaseModel):
    """Result of a single primitive call in a dispatch sequence."""

    primitive: str = ""
    success: bool = True
    payload: dict[str, Any] = Field(default_factory=dict)
    error: BrunhandErrorDetail | None = None
    latency_ms: float = 0.0
    oracle_view_name: str | None = None  # Set for screenshot primitives that were fed to Oracle Eye


class BrunhandDispatchRequest(BaseModel):
    """Bridge-level dispatch request for brunhand_dispatch()."""

    host: str = Field(description="Tailscale host name or 'localhost'")
    primitives: list[PrimitiveCall] = Field(
        default_factory=list,
        description="Ordered sequence of primitives to execute",
    )
    session_id: str | None = Field(default=None, description="Resume existing session (optional)")
    agent_id: str = Field(default="unknown", description="Agent identity for Annáll")
    request_id: str = Field(default_factory=_new_uuid)
    run_id: str | None = Field(
        default=None,
        description="Shared run_id for Mode C (combined Blender + Brúarhönd dispatch)",
    )


class BrunhandDispatchResponse(BaseModel):
    """Bridge-level response from brunhand_dispatch()."""

    request_id: str = ""
    success: bool = True
    results: list[PrimitiveResult] = Field(default_factory=list)
    annall_session_id: str = ""
    elapsed_seconds: float = 0.0
    errors: list[BrunhandErrorDetail] = Field(default_factory=list)
    oracle_view_names: list[str] = Field(
        default_factory=list,
        description="All Oracle Eye view names registered during this dispatch",
    )
