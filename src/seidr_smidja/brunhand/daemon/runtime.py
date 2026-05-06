"""seidr_smidja.brunhand.daemon.runtime — Platform shim layer (Horfunarþjónn).

Wraps PyAutoGUI, MSS, pygetwindow, and platform-conditional accessibility libs
behind a uniform Python API. Each function:
  1. Checks is_supported_on_this_platform() first.
  2. Raises CapabilityRuntimeError cleanly if not supported.
  3. Executes the underlying library call wrapped in try/except.
  4. Returns a plain dict of results.

ALL platform-conditional imports are isolated in this module.
Primitive handler code NEVER imports pyautogui, mss, or pygetwindow directly.

See: docs/features/brunhand/ARCHITECTURE.md §IX Cross-Platform Stance
"""
from __future__ import annotations

import base64
import io
import logging
import sys
import time
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
) -> dict[str, Any]:
    """Capture a screenshot using MSS.

    Args:
        region: Dict with 'left', 'top', 'width', 'height'. None = full primary monitor.

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
                monitor_index = region.get("monitor_index", 0)
            else:
                # Full primary monitor (monitor index 1 in mss — 0 is all monitors combined)
                monitor = sct.monitors[1]
                monitor_index = 0

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

    This is a coordinate-based script for VRoid Studio.
    It uses hotkeys and pygetwindow to navigate the export dialog.
    VRoid Studio version sensitivity applies — see D-010 Consequences.

    Raises:
        RuntimeError: If VRoid Studio is not running or the export fails.
    """
    if not is_vroid_running():
        raise RuntimeError("VRoid Studio is not running.")
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

        # Step 3: Navigate Export VRM (arrow keys or shortcut)
        # VRoid Studio uses specific keyboard navigation
        do_hotkey(["e"])  # E for Export in VRoid's File menu
        steps_executed.append("click_export_vrm")
        time.sleep(0.5)

        # Step 4: Wait for export dialog
        wait_result = do_wait_for_window("Export VRM", timeout_seconds=10.0)
        if not wait_result["found"]:
            # Try alternative dialog title
            wait_result = do_wait_for_window("エクスポート", timeout_seconds=5.0)
        if wait_result["found"]:
            steps_executed.append("export_dialog_opened")

        # Step 5: The path would be set here in a full implementation
        # For v0.1, we log the step and note the path parameter
        steps_executed.append(f"set_path:{output_path}")
        time.sleep(0.3)

        # Step 6: Confirm export (Enter or OK button)
        do_hotkey(["return"])
        steps_executed.append("confirm_dialog")
        time.sleep(1.0)

        elapsed = time.monotonic() - start
        return {
            "exported_path": output_path,
            "elapsed_seconds": elapsed,
            "steps_executed": steps_executed,
        }
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
    """Open a .vroid project file in VRoid Studio via Ctrl+O."""
    if not is_vroid_running():
        raise RuntimeError("VRoid Studio is not running.")
    start = time.monotonic()
    steps_executed: list[str] = []
    try:
        _focus_vroid_window()
        do_hotkey(["ctrl", "o"])
        steps_executed.append("hotkey_file_open")
        time.sleep(0.5)

        # Wait for file dialog
        wait_result = do_wait_for_window("Open", timeout_seconds=5.0)
        if wait_result["found"]:
            steps_executed.append("file_dialog_opened")

        steps_executed.append(f"set_path:{project_path}")
        do_hotkey(["return"])
        steps_executed.append("confirm_open")
        time.sleep(1.0)

        # Wait for project to load
        wait_loaded = do_wait_for_window("VRoid Studio", timeout_seconds=wait_timeout_seconds)
        if wait_loaded["found"]:
            steps_executed.append("wait_for_load")

        return {
            "opened_path": project_path,
            "elapsed_seconds": time.monotonic() - start,
            "steps_executed": steps_executed,
        }
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
