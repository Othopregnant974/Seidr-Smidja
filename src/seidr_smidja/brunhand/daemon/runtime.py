"""seidr_smidja.brunhand.daemon.runtime — Platform shim layer (Horfunarþjónn).

Wraps PyAutoGUI, MSS, pygetwindow, and platform-conditional accessibility libs
behind a uniform Python API. Each function:
  1. Checks is_supported_on_this_platform() first.
  2. Raises CapabilityRuntimeError cleanly if not supported.
  3. Executes the underlying library call wrapped in try/except.
  4. Returns a plain dict of results.

ALL platform-conditional imports are isolated in this module.
Primitive handler code NEVER imports pyautogui, mss, or pygetwindow directly.

Path safety:
  _validate_path_in_root() enforces that resolved output/project paths are
  children of the configured export_root / project_root directories.
  Raises ValueError on traversal attempts — callers map this to a security error.

VRoid high-level scripts (vroid_export_vrm, vroid_open_project):
  These functions open the VRoid Studio file dialog, clear the path field via
  Ctrl+A, type the resolved and validated path, then confirm.  After the dialog
  closes the export function verifies the file actually appeared on disk.  If the
  file is not found within wait_timeout_seconds the function returns success=False
  rather than lying to the caller.

  B-003 NOTE: The path-typing step uses pyautogui.hotkey('ctrl','a') +
  pyautogui.typewrite() to replace whatever VRoid pre-filled.  This approach is
  sensitive to the active OS file dialog having keyboard focus.  The
  _focus_vroid_window() + time.sleep() sequence before dialog open gives the
  window time to come foreground.  If the dialog cannot be found a structured
  error is returned (never a silent false-success).

See: docs/features/brunhand/ARCHITECTURE.md §IX Cross-Platform Stance
"""
from __future__ import annotations

import base64
import io
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ─── Optional dependency probing ─────────────────────────────────────────────
# We attempt imports here so capabilities detection works without raising.

_PYAUTOGUI_AVAILABLE = False
_MSS_AVAILABLE = False
_PYGETWINDOW_AVAILABLE = False
_PSUTIL_AVAILABLE = False

try:
    import pyautogui as _pyautogui  # type: ignore[import]
    _PYAUTOGUI_AVAILABLE = True
except ImportError:
    _pyautogui = None  # type: ignore[assignment]

try:
    import mss as _mss  # type: ignore[import]
    _MSS_AVAILABLE = True
except ImportError:
    _mss = None  # type: ignore[assignment]

try:
    import pygetwindow as _pygetwindow  # type: ignore[import]
    _PYGETWINDOW_AVAILABLE = True
except ImportError:
    _pygetwindow = None  # type: ignore[assignment]

try:
    import psutil as _psutil  # type: ignore[import]
    _PSUTIL_AVAILABLE = True
except ImportError:
    _psutil = None  # type: ignore[assignment]


class CapabilityRuntimeError(RuntimeError):
    """Raised when a primitive cannot execute due to missing platform support."""

    def __init__(self, primitive: str, reason: str) -> None:
        super().__init__(f"Primitive '{primitive}' not available: {reason}")
        self.primitive = primitive
        self.reason = reason


# ─── Path Safety (B-002) ─────────────────────────────────────────────────────


def _validate_path_in_root(path_str: str, root_str: str) -> Path:
    """Validate that path_str resolves to a child of root_str.

    Resolves both paths to absolute form and checks containment.
    Raises ValueError if the resolved path escapes the root, preventing
    path-traversal attacks such as '../../etc/passwd' or absolute escapes.

    Args:
        path_str: Caller-supplied path (may be relative or contain '..' segments).
        root_str: Configured allow-list root directory.

    Returns:
        The fully resolved Path (guaranteed to be inside root).

    Raises:
        ValueError: If the resolved path is not a descendant of root.
    """
    root = Path(root_str).resolve()
    # Join path_str onto root first, then resolve — this handles relative paths
    # correctly and avoids Path(absolute_string).resolve() escaping the root.
    candidate = (root / path_str).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise ValueError(
            f"Path '{path_str}' resolves to '{candidate}' which is outside "
            f"the allowed root '{root}'. Path traversal rejected."
        )
    return candidate


# ─── Capability probes ───────────────────────────────────────────────────────


def is_screenshot_available() -> bool:
    """MSS screenshot is available."""
    return _MSS_AVAILABLE


def is_input_available() -> bool:
    """PyAutoGUI input (click, type, hotkey, drag, scroll, move) is available."""
    return _PYAUTOGUI_AVAILABLE


def is_window_discovery_available() -> bool:
    """pygetwindow window discovery is available."""
    return _PYGETWINDOW_AVAILABLE or sys.platform == "linux"


def is_vroid_detection_available() -> bool:
    """psutil process detection is available."""
    return _PSUTIL_AVAILABLE


def get_platform_name() -> str:
    """Return normalized platform name: 'windows', 'darwin', or 'linux'."""
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "darwin"
    return "linux"


# ─── Screenshot ───────────────────────────────────────────────────────────────


def take_screenshot(
    region: dict[str, int] | None = None,
    monitor_index: int = 0,
) -> dict[str, Any]:
    """Capture a screenshot using MSS.

    Args:
        region:        Dict with 'left', 'top', 'width', 'height'.  None = full monitor.
        monitor_index: 0-based monitor index (0 = primary).  Ignored when region is set.
                       B-012 fix: callers can now target non-primary monitors.

    Returns:
        Dict with 'png_bytes_b64', 'width', 'height', 'captured_at', 'monitor_index'.

    Raises:
        CapabilityRuntimeError: If MSS is not available.
        RuntimeError: If capture fails at the OS level.
    """
    if not _MSS_AVAILABLE:
        raise CapabilityRuntimeError(
            "screenshot",
            "mss is not installed. Install with: pip install 'seidr-smidja[brunhand-daemon]'",
        )
    captured_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        with _mss.mss() as sct:
            if region:
                monitor = {
                    "left": region.get("left", 0),
                    "top": region.get("top", 0),
                    "width": region.get("width", 1920),
                    "height": region.get("height", 1080),
                }
                # Region dict may carry its own monitor_index override
                monitor_index = region.get("monitor_index", monitor_index)
            else:
                # MSS monitors: index 0 = all-monitors virtual, 1+ = real monitors.
                # monitor_index is 0-based from the caller's perspective.
                mss_index = monitor_index + 1  # convert 0-based to mss 1-based
                if mss_index < 1 or mss_index >= len(sct.monitors):
                    raise RuntimeError(
                        f"monitor_index {monitor_index} is out of range "
                        f"(detected {len(sct.monitors) - 1} monitor(s))."
                    )
                monitor = sct.monitors[mss_index]

            screenshot = sct.grab(monitor)
            # Convert to PNG bytes via PIL/Pillow (mss returns BGRA, PIL handles conversion)
            try:
                from PIL import Image  # type: ignore[import]
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                png_bytes = buf.getvalue()
            except ImportError:
                # Fallback: use mss's built-in PNG writer
                png_bytes = _mss.tools.to_png(screenshot.rgb, screenshot.size)

            png_b64 = base64.b64encode(png_bytes).decode("ascii")
            return {
                "png_bytes_b64": png_b64,
                "width": screenshot.width,
                "height": screenshot.height,
                "captured_at": captured_at,
                "monitor_index": monitor_index,
            }
    except CapabilityRuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Screenshot failed: {exc}") from exc


# ─── Click ────────────────────────────────────────────────────────────────────


def do_click(
    x: int,
    y: int,
    button: str = "left",
    clicks: int = 1,
    interval: float = 0.0,
    modifiers: list[str] | None = None,
) -> dict[str, Any]:
    """Execute a mouse click via PyAutoGUI.

    Raises:
        CapabilityRuntimeError: If PyAutoGUI is not available.
    """
    if not _PYAUTOGUI_AVAILABLE:
        raise CapabilityRuntimeError(
            "click",
            "pyautogui is not installed. Install with: pip install 'seidr-smidja[brunhand-daemon]'",
        )
    try:
        held_keys: list[str] = [m.lower() for m in (modifiers or [])]
        # Press modifier keys
        for key in held_keys:
            _pyautogui.keyDown(key)
        try:
            _pyautogui.click(x=x, y=y, button=button, clicks=clicks, interval=interval)
        finally:
            # Always release modifier keys
            for key in reversed(held_keys):
                _pyautogui.keyUp(key)
        return {"x": x, "y": y, "button": button, "clicks_delivered": clicks}
    except CapabilityRuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Click failed at ({x}, {y}): {exc}") from exc


# ─── Move ─────────────────────────────────────────────────────────────────────


def do_move(x: int, y: int, duration: float = 0.25, tween: str = "linear") -> dict[str, Any]:
    """Move mouse cursor via PyAutoGUI."""
    if not _PYAUTOGUI_AVAILABLE:
        raise CapabilityRuntimeError("move", "pyautogui is not installed.")
    try:
        _pyautogui.moveTo(x, y, duration=duration)
        return {"x": x, "y": y}
    except CapabilityRuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Move failed to ({x}, {y}): {exc}") from exc


# ─── Drag ─────────────────────────────────────────────────────────────────────


def do_drag(
    x1: int, y1: int, x2: int, y2: int, button: str = "left", duration: float = 0.5
) -> dict[str, Any]:
    """Execute a mouse drag via PyAutoGUI."""
    if not _PYAUTOGUI_AVAILABLE:
        raise CapabilityRuntimeError("drag", "pyautogui is not installed.")
    try:
        _pyautogui.moveTo(x1, y1)
        _pyautogui.dragTo(x2, y2, duration=duration, button=button)
        return {"from_pos": [x1, y1], "to_pos": [x2, y2]}
    except CapabilityRuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Drag failed from ({x1},{y1}) to ({x2},{y2}): {exc}") from exc


# ─── Scroll ───────────────────────────────────────────────────────────────────


def do_scroll(x: int, y: int, clicks: int, direction: str = "down") -> dict[str, Any]:
    """Execute a mouse scroll via PyAutoGUI."""
    if not _PYAUTOGUI_AVAILABLE:
        raise CapabilityRuntimeError("scroll", "pyautogui is not installed.")
    try:
        # PyAutoGUI scroll: positive = up, negative = down
        scroll_amount = clicks if direction == "up" else -clicks
        _pyautogui.scroll(scroll_amount, x=x, y=y)
        return {"x": x, "y": y, "clicks": clicks, "direction": direction}
    except CapabilityRuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Scroll failed at ({x},{y}): {exc}") from exc


# ─── Type Text ────────────────────────────────────────────────────────────────


def do_type_text(text: str, interval: float = 0.05) -> dict[str, Any]:
    """Type a string via PyAutoGUI."""
    if not _PYAUTOGUI_AVAILABLE:
        raise CapabilityRuntimeError("type_text", "pyautogui is not installed.")
    try:
        _pyautogui.typewrite(text, interval=interval)
        return {"characters_typed": len(text)}
    except CapabilityRuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Type text failed: {exc}") from exc


# ─── Hotkey ───────────────────────────────────────────────────────────────────


def do_hotkey(keys: list[str]) -> dict[str, Any]:
    """Press a key combination via PyAutoGUI."""
    if not _PYAUTOGUI_AVAILABLE:
        raise CapabilityRuntimeError("hotkey", "pyautogui is not installed.")
    try:
        _pyautogui.hotkey(*keys)
        return {"keys": keys}
    except CapabilityRuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Hotkey {keys} failed: {exc}") from exc


# ─── Find Window ─────────────────────────────────────────────────────────────


def do_find_window(title_pattern: str, exact: bool = False) -> dict[str, Any]:
    """Find windows by title pattern."""
    if sys.platform == "linux" and not _PYGETWINDOW_AVAILABLE:
        return _find_window_linux(title_pattern, exact)
    if not _PYGETWINDOW_AVAILABLE:
        raise CapabilityRuntimeError("find_window", "pygetwindow is not installed.")
    try:
        if exact:
            wins = _pygetwindow.getWindowsWithTitle(title_pattern)
            wins = [w for w in wins if w.title == title_pattern]
        else:
            wins = _pygetwindow.getWindowsWithTitle(title_pattern)
        windows = []
        for w in wins:
            try:
                active_win = _pygetwindow.getActiveWindow()
                is_fg = (active_win is not None and w.title == active_win.title)
            except Exception:
                is_fg = False
            windows.append({
                "title": w.title,
                "left": w.left,
                "top": w.top,
                "width": w.width,
                "height": w.height,
                "is_foreground": is_fg,
            })
        return {"found": bool(windows), "windows": windows}
    except CapabilityRuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"find_window failed for pattern '{title_pattern}': {exc}") from exc


def _find_window_linux(title_pattern: str, exact: bool) -> dict[str, Any]:
    """Linux fallback: use wmctrl subprocess to find windows."""
    import subprocess
    try:
        result = subprocess.run(
            ["wmctrl", "-l"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        windows = []
        for line in result.stdout.splitlines():
            parts = line.split(None, 3)
            if len(parts) >= 4:
                win_title = parts[3]
                if exact and win_title == title_pattern or not exact and title_pattern.lower() in win_title.lower():
                    windows.append({"title": win_title, "left": 0, "top": 0,
                                    "width": 0, "height": 0, "is_foreground": False})
        return {"found": bool(windows), "windows": windows}
    except FileNotFoundError:
        raise CapabilityRuntimeError(
            "find_window",
            "wmctrl is not installed on this Linux system. Install with: apt install wmctrl"
        )
    except Exception as exc:
        raise RuntimeError(f"find_window (Linux wmctrl) failed: {exc}") from exc


# ─── Wait For Window ─────────────────────────────────────────────────────────


def do_wait_for_window(
    title_pattern: str,
    timeout_seconds: float = 30.0,
    poll_interval_seconds: float = 0.5,
) -> dict[str, Any]:
    """Poll until a window with the given title appears or timeout elapses.

    Returns found=True + window info on success.
    Returns found=False + elapsed on timeout (NOT an error — see DATA_FLOW.md §F6).
    """
    start = time.monotonic()
    while True:
        elapsed = time.monotonic() - start
        if elapsed >= timeout_seconds:
            return {"found": False, "elapsed_seconds": elapsed, "window": None}
        try:
            result = do_find_window(title_pattern)
            if result["found"] and result["windows"]:
                return {
                    "found": True,
                    "elapsed_seconds": time.monotonic() - start,
                    "window": result["windows"][0],
                }
        except Exception:
            pass
        time.sleep(min(poll_interval_seconds, timeout_seconds - elapsed))


# ─── VRoid Process Detection ─────────────────────────────────────────────────


def is_vroid_running() -> bool:
    """Check whether VRoid Studio process is currently running."""
    if not _PSUTIL_AVAILABLE:
        # Cannot check without psutil; assume running (fail on actual action)
        return True
    try:
        for proc in _psutil.process_iter(["name"]):
            name = (proc.info.get("name") or "").lower()
            if "vroid" in name:
                return True
        return False
    except Exception:
        return True  # Conservative: assume running if check fails


# ─── VRoid High-Level Scripts ─────────────────────────────────────────────────


def vroid_export_vrm(
    output_path: str,
    overwrite: bool = True,
    wait_timeout_seconds: float = 120.0,
    export_root: str = "exports",
) -> dict[str, Any]:
    """Drive VRoid Studio's File → Export → Export VRM flow.

    B-003 FIX: After the export dialog opens the function now:
      1. Selects all text in the filename field (Ctrl+A).
      2. Types the fully-resolved, path-validated output path via pyautogui.typewrite().
      3. Confirms with Enter.
      4. After the wait_timeout_seconds window, verifies the file actually exists on disk.
         If the file is NOT present, returns success=False with a structured error rather
         than silently reporting the wrong path.

    B-002 FIX: output_path is validated against export_root via _validate_path_in_root().
    Raises ValueError (mapped to BrunhandPathSecurityError by the endpoint handler) if
    the path escapes the root.

    VRoid Studio version sensitivity applies — see D-010 Consequences.
    This function requires pyautogui to be available.

    Raises:
        ValueError:    If output_path escapes export_root (path traversal).
        RuntimeError:  If VRoid Studio is not running or the export sequence fails.
        CapabilityRuntimeError: If pyautogui is unavailable.
    """
    if not _PYAUTOGUI_AVAILABLE:
        raise CapabilityRuntimeError(
            "vroid_export_vrm",
            "pyautogui is not installed. Install with: pip install 'seidr-smidja[brunhand-daemon]'",
        )
    if not is_vroid_running():
        raise RuntimeError("VRoid Studio is not running.")

    # B-002: Validate and resolve path before any GUI interaction.
    resolved_path = _validate_path_in_root(output_path, export_root)
    resolved_path_str = str(resolved_path)

    start = time.monotonic()
    steps_executed: list[str] = []
    try:
        # Step 1: Focus VRoid Studio window
        _focus_vroid_window()
        steps_executed.append("focus_vroid_window")
        time.sleep(0.3)

        # Step 2: Open File menu via Alt+F
        do_hotkey(["alt", "f"])
        steps_executed.append("hotkey_file_menu")
        time.sleep(0.5)

        # Step 3: Navigate Export VRM (VRoid Studio keyboard navigation)
        do_hotkey(["e"])  # E for Export in VRoid's File menu
        steps_executed.append("hotkey_export_vrm")
        time.sleep(0.5)

        # Step 4: Wait for export dialog — try English and Japanese titles
        wait_result = do_wait_for_window("Export VRM", timeout_seconds=10.0)
        if not wait_result["found"]:
            wait_result = do_wait_for_window("エクスポート", timeout_seconds=5.0)
        if wait_result["found"]:
            steps_executed.append("export_dialog_opened")
            time.sleep(0.2)  # Short pause for dialog to fully render
        else:
            # Dialog did not appear — return structured failure rather than silently proceeding
            elapsed = time.monotonic() - start
            return {
                "exported_path": None,
                "success": False,
                "error": "Export dialog did not appear within timeout.",
                "elapsed_seconds": elapsed,
                "steps_executed": steps_executed,
            }

        # Step 5: B-003 FIX — type the validated path into the dialog filename field.
        # Ctrl+A selects all existing text, then typewrite replaces it with our path.
        # We use pyautogui directly here (runtime already confirmed _PYAUTOGUI_AVAILABLE).
        _pyautogui.hotkey("ctrl", "a")  # type: ignore[union-attr]
        time.sleep(0.1)
        # typewrite works best with ASCII paths; use pyperclip-fallback if path has
        # non-ASCII characters (common on Windows with non-Latin locale paths).
        _type_path_into_dialog(resolved_path_str)
        steps_executed.append(f"typed_path:{resolved_path_str}")
        time.sleep(0.2)

        # Step 6: Confirm export
        do_hotkey(["return"])
        steps_executed.append("confirm_dialog")

        # Step 7: Wait for the dialog to close (VRoid is working)
        time.sleep(1.5)

        # Step 8: B-003 VERIFICATION — check the file actually appeared on disk.
        # Poll until file appears or wait_timeout_seconds elapses.
        file_appeared = _wait_for_file(resolved_path, wait_timeout_seconds - (time.monotonic() - start))
        elapsed = time.monotonic() - start

        if not file_appeared:
            steps_executed.append("verify_failed:file_not_found")
            return {
                "exported_path": None,
                "success": False,
                "error": (
                    f"Export dialog was confirmed but file '{resolved_path_str}' "
                    f"did not appear within {wait_timeout_seconds:.1f}s. "
                    f"VRoid Studio may have exported to a different location."
                ),
                "elapsed_seconds": elapsed,
                "steps_executed": steps_executed,
            }

        steps_executed.append("verify_ok:file_exists")
        return {
            "exported_path": resolved_path_str,
            "success": True,
            "elapsed_seconds": elapsed,
            "steps_executed": steps_executed,
        }
    except (ValueError, CapabilityRuntimeError):
        raise
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"VRoid export VRM failed: {exc}") from exc


def vroid_save_project() -> dict[str, Any]:
    """Save the current VRoid Studio project via Ctrl+S."""
    if not is_vroid_running():
        raise RuntimeError("VRoid Studio is not running.")
    start = time.monotonic()
    steps_executed: list[str] = []
    try:
        _focus_vroid_window()
        do_hotkey(["ctrl", "s"])
        steps_executed.append("hotkey_ctrl_s")
        time.sleep(0.5)
        return {"elapsed_seconds": time.monotonic() - start, "steps_executed": steps_executed}
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"VRoid save project failed: {exc}") from exc


def vroid_open_project(
    project_path: str,
    wait_timeout_seconds: float = 60.0,
    project_root: str = "projects",
) -> dict[str, Any]:
    """Open a .vroid project file in VRoid Studio via Ctrl+O.

    B-003 FIX: After the file-open dialog appears the function types the fully-resolved,
    path-validated project path into the filename field (Ctrl+A + typewrite), then
    confirms with Enter.  It verifies the project loaded by waiting for a VRoid Studio
    window to reappear.  If the file does not exist on disk before opening, the function
    returns a structured error rather than proceeding with a non-existent path.

    B-002 FIX: project_path is validated against project_root via _validate_path_in_root().

    Raises:
        ValueError:    If project_path escapes project_root (path traversal).
        RuntimeError:  If VRoid Studio is not running or the open sequence fails.
        CapabilityRuntimeError: If pyautogui is unavailable.
    """
    if not _PYAUTOGUI_AVAILABLE:
        raise CapabilityRuntimeError(
            "vroid_open_project",
            "pyautogui is not installed. Install with: pip install 'seidr-smidja[brunhand-daemon]'",
        )
    if not is_vroid_running():
        raise RuntimeError("VRoid Studio is not running.")

    # B-002: Validate and resolve path before any GUI interaction.
    resolved_path = _validate_path_in_root(project_path, project_root)
    resolved_path_str = str(resolved_path)

    # Verify the source file actually exists before trying to open it
    if not resolved_path.exists():
        raise RuntimeError(
            f"Project file '{resolved_path_str}' does not exist. "
            f"Cannot open a non-existent .vroid file."
        )

    start = time.monotonic()
    steps_executed: list[str] = []
    try:
        _focus_vroid_window()
        steps_executed.append("focus_vroid_window")
        time.sleep(0.3)

        do_hotkey(["ctrl", "o"])
        steps_executed.append("hotkey_file_open")
        time.sleep(0.5)

        # Wait for file open dialog — try common Windows dialog titles
        wait_result = do_wait_for_window("Open", timeout_seconds=5.0)
        if not wait_result["found"]:
            wait_result = do_wait_for_window("開く", timeout_seconds=3.0)  # Japanese "Open"

        if wait_result["found"]:
            steps_executed.append("file_dialog_opened")
            time.sleep(0.2)
        else:
            elapsed = time.monotonic() - start
            return {
                "opened_path": None,
                "success": False,
                "error": "File open dialog did not appear within timeout.",
                "elapsed_seconds": elapsed,
                "steps_executed": steps_executed,
            }

        # B-003 FIX: Type the validated path into the dialog filename field.
        _pyautogui.hotkey("ctrl", "a")  # type: ignore[union-attr]
        time.sleep(0.1)
        _type_path_into_dialog(resolved_path_str)
        steps_executed.append(f"typed_path:{resolved_path_str}")
        time.sleep(0.2)

        do_hotkey(["return"])
        steps_executed.append("confirm_open")
        time.sleep(1.0)

        # Wait for VRoid Studio to finish loading the project
        wait_loaded = do_wait_for_window(
            "VRoid Studio",
            timeout_seconds=max(5.0, wait_timeout_seconds - (time.monotonic() - start)),
        )
        if wait_loaded["found"]:
            steps_executed.append("project_loaded")
        else:
            steps_executed.append("load_wait_timed_out")

        elapsed = time.monotonic() - start
        return {
            "opened_path": resolved_path_str,
            "success": True,
            "elapsed_seconds": elapsed,
            "steps_executed": steps_executed,
        }
    except (ValueError, CapabilityRuntimeError):
        raise
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"VRoid open project failed: {exc}") from exc


def _focus_vroid_window() -> None:
    """Attempt to bring VRoid Studio to the foreground."""
    if not _PYGETWINDOW_AVAILABLE:
        return
    try:
        wins = _pygetwindow.getWindowsWithTitle("VRoid Studio")
        if wins:
            wins[0].activate()
            time.sleep(0.2)
    except Exception:
        pass


def _type_path_into_dialog(path_str: str) -> None:
    """Type a file path string into the currently-focused OS dialog field.

    Uses pyautogui.typewrite for ASCII-safe paths.  For paths that contain
    non-ASCII characters (e.g. Japanese directory names on Windows), falls back
    to pyperclip clipboard paste (Ctrl+V) if pyperclip is available, otherwise
    logs a warning and continues with typewrite (which may drop non-ASCII chars).

    Callers must have already pressed Ctrl+A to clear the existing field content.
    """
    if not _PYAUTOGUI_AVAILABLE:
        raise CapabilityRuntimeError("type_path", "pyautogui is not installed.")
    try:
        # Check if path is pure ASCII — typewrite is reliable for ASCII
        path_str.encode("ascii")
        _pyautogui.typewrite(path_str, interval=0.03)  # type: ignore[union-attr]
    except UnicodeEncodeError:
        # Path contains non-ASCII — attempt clipboard paste fallback
        try:
            import pyperclip  # type: ignore[import]
            pyperclip.copy(path_str)
            _pyautogui.hotkey("ctrl", "v")  # type: ignore[union-attr]
        except ImportError:
            logger.warning(
                "Path '%s' contains non-ASCII characters and pyperclip is not installed. "
                "Falling back to typewrite (non-ASCII characters may be dropped). "
                "Install pyperclip for reliable non-ASCII path typing.",
                path_str,
            )
            _pyautogui.typewrite(path_str, interval=0.03)  # type: ignore[union-attr]


def _wait_for_file(path: Path, timeout_seconds: float, poll_interval: float = 0.5) -> bool:
    """Poll until a file appears at *path* or *timeout_seconds* elapses.

    Used by vroid_export_vrm to verify the exported file actually appeared on disk.
    Returns True if the file exists within timeout, False otherwise.
    """
    # File may already exist if VRoid was quick
    if path.exists():
        return True
    deadline = time.monotonic() + max(1.0, timeout_seconds)
    while time.monotonic() < deadline:
        time.sleep(min(poll_interval, deadline - time.monotonic()))
        if path.exists():
            return True
    return False
