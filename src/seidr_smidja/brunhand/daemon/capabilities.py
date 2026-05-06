"""seidr_smidja.brunhand.daemon.capabilities — Sjálfsmöguleiki, the Capabilities Registry.

On daemon startup, probes the current runtime environment and assembles a
CapabilitiesManifest describing which primitives are available on this platform.

The manifest is:
  - Served at GET /v1/brunhand/capabilities (auth required)
  - Consulted internally before every primitive execution
  - Cached by Tengslastig on session open (client-side)

INVARIANT: The registry never raises — it returns availability=False with a
clear reason for unavailable primitives.

See: docs/features/brunhand/ARCHITECTURE.md §VI Capabilities Probe (Sjálfsmöguleiki)
"""
from __future__ import annotations

import logging
import platform
import sys

from seidr_smidja.brunhand.models import CapabilitiesManifest, PrimitiveStatus, ScreenRect

logger = logging.getLogger(__name__)

# ─── Singleton manifest (refreshed on startup, queryable during operation) ───

_manifest: CapabilitiesManifest | None = None


def probe_capabilities(daemon_version: str = "0.1.0") -> CapabilitiesManifest:
    """Probe the current platform and build a CapabilitiesManifest.

    Safe to call multiple times — returns a freshly probed manifest each time.
    The result is cached in the module-level singleton after the first call.

    Args:
        daemon_version: Version string to embed in the manifest.

    Returns:
        A fully populated CapabilitiesManifest.
    """
    global _manifest

    from seidr_smidja.brunhand.daemon.runtime import (
        _MSS_AVAILABLE,
        _PYAUTOGUI_AVAILABLE,
        _PYGETWINDOW_AVAILABLE,
        get_platform_name,
    )

    os_name = get_platform_name()
    os_version = platform.version()

    # ── Screen geometry probe ────────────────────────────────────────────────
    screen_geometry = _probe_screen_geometry()

    # ── Primitive availability ────────────────────────────────────────────────
    primitives: dict[str, PrimitiveStatus] = {}

    # screenshot — provided by MSS
    primitives["screenshot"] = PrimitiveStatus(
        available=_MSS_AVAILABLE,
        library="mss",
        degraded=_is_linux_wayland(),
        degraded_reason="Wayland session detected — screenshot may be limited" if _is_linux_wayland() else None,
        notes="Install with: pip install 'seidr-smidja[brunhand-daemon]'" if not _MSS_AVAILABLE else None,
    )

    # Input primitives — provided by PyAutoGUI
    _input_note = (
        "Install with: pip install 'seidr-smidja[brunhand-daemon]'" if not _PYAUTOGUI_AVAILABLE else None
    )
    _wayland_degraded = _is_linux_wayland()
    _wayland_note = "Wayland session: input automation may not work (X11 only)" if _wayland_degraded else None

    for prim_name in ["click", "move", "drag", "scroll", "type_text", "hotkey"]:
        primitives[prim_name] = PrimitiveStatus(
            available=_PYAUTOGUI_AVAILABLE,
            library="pyautogui",
            degraded=_wayland_degraded,
            degraded_reason=_wayland_note,
            notes=_input_note,
        )

    # Window discovery — pygetwindow (or wmctrl on Linux)
    window_available = _PYGETWINDOW_AVAILABLE or sys.platform == "linux"
    window_lib = "pygetwindow" if _PYGETWINDOW_AVAILABLE else ("wmctrl" if sys.platform == "linux" else "")
    window_note: str | None = None
    if not window_available:
        window_note = "Install pygetwindow with: pip install 'seidr-smidja[brunhand-daemon]'"
    elif sys.platform == "linux" and not _PYGETWINDOW_AVAILABLE:
        window_note = "Using wmctrl fallback (limited geometry info). Install wmctrl for full support."
    elif sys.platform == "darwin" and _PYGETWINDOW_AVAILABLE:
        window_note = "macOS pygetwindow support is limited — consider accessibility lib for full control"

    primitives["find_window"] = PrimitiveStatus(
        available=window_available,
        library=window_lib,
        degraded=sys.platform == "linux" and not _PYGETWINDOW_AVAILABLE,
        degraded_reason="wmctrl fallback provides limited geometry" if (sys.platform == "linux" and not _PYGETWINDOW_AVAILABLE) else None,
        notes=window_note,
    )
    primitives["wait_for_window"] = PrimitiveStatus(
        available=window_available,
        library=window_lib,
        degraded=primitives["find_window"].degraded,
        degraded_reason=primitives["find_window"].degraded_reason,
        notes=window_note,
    )

    # VRoid high-level primitives — require input + window + vroid detection
    _vroid_available = _PYAUTOGUI_AVAILABLE  # Minimum requirement
    _vroid_note: str | None = None
    if not _vroid_available:
        _vroid_note = "Requires pyautogui. Install with: pip install 'seidr-smidja[brunhand-daemon]'"
    primitives["vroid_export_vrm"] = PrimitiveStatus(
        available=_vroid_available,
        library="pyautogui+pygetwindow",
        degraded=False,
        degraded_reason=None,
        notes=_vroid_note,
    )
    primitives["vroid_save_project"] = PrimitiveStatus(
        available=_vroid_available,
        library="pyautogui",
        degraded=False,
        degraded_reason=None,
        notes=_vroid_note,
    )
    primitives["vroid_open_project"] = PrimitiveStatus(
        available=_vroid_available,
        library="pyautogui+pygetwindow",
        degraded=False,
        degraded_reason=None,
        notes=_vroid_note,
    )

    import time as _time
    manifest = CapabilitiesManifest(
        daemon_version=daemon_version,
        os_name=os_name,
        os_version=os_version,
        screen_geometry=screen_geometry,
        primitives=primitives,
        probed_at=_time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
    )

    _manifest = manifest
    logger.info(
        "Sjálfsmöguleiki: capabilities probed — OS=%s, available_primitives=%d/%d",
        os_name,
        sum(1 for p in primitives.values() if p.available),
        len(primitives),
    )
    return manifest


def get_cached_manifest() -> CapabilitiesManifest | None:
    """Return the last probed manifest, or None if probe_capabilities() hasn't been called."""
    return _manifest


def is_primitive_available(primitive_name: str) -> bool:
    """Quick availability check for a primitive name.

    Uses the cached manifest. Returns False if not yet probed or unknown primitive.
    """
    if _manifest is None:
        return False
    status = _manifest.primitives.get(primitive_name)
    if status is None:
        return False
    return status.available and not status.degraded


def _probe_screen_geometry() -> list[ScreenRect]:
    """Probe monitor geometry using MSS."""
    try:
        import mss  # type: ignore[import]
        with mss.mss() as sct:
            rects: list[ScreenRect] = []
            # mss.monitors[0] is the virtual combined screen; [1..N] are real monitors
            for idx, mon in enumerate(sct.monitors[1:], start=0):
                rects.append(ScreenRect(
                    left=mon.get("left", 0),
                    top=mon.get("top", 0),
                    width=mon.get("width", 1920),
                    height=mon.get("height", 1080),
                    monitor_index=idx,
                ))
            return rects if rects else [ScreenRect()]
    except Exception:
        return [ScreenRect()]


def _is_linux_wayland() -> bool:
    """Detect Wayland session on Linux."""
    if sys.platform != "linux":
        return False
    import os
    return bool(os.environ.get("WAYLAND_DISPLAY") or
                os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland")
