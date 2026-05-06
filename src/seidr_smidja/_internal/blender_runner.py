"""seidr_smidja._internal.blender_runner — Shared Blender Subprocess Runner

Decision D-003: This module lives in _internal/ and is the single source of
truth for Blender subprocess mechanics. Both Forge and Oracle Eye import from
here — neither owns this logic and neither imports from the other.

The runner knows nothing about WHAT the script does. It provides:
    - Blender executable path resolution (priority chain per ARCHITECTURE.md §V)
    - Subprocess launch with timeout, stdout/stderr capture
    - Optional line-streaming callback for Annáll telemetry
    - Structured RunnerResult return

Cross-platform: Windows, Linux, macOS — pathlib.Path everywhere.
Never hardcodes any path. Never uses shell=True unless explicitly necessary.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# AUDIT-004: Platform-specific well-known Blender locations have been moved to
# config/defaults.yaml under blender.platform_hints.
# This constant is kept as a DEPRECATED fallback for one release cycle (v0.1.x)
# and will be removed in v0.2 once the config-driven path is proven in production.
# DO NOT add new paths here — extend config/defaults.yaml instead.
_PLATFORM_HINTS: dict[str, list[str]] = {
    "win32": [
        r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
    ],
    "linux": ["/usr/bin/blender", "/usr/local/bin/blender"],
    "darwin": [
        "/Applications/Blender.app/Contents/MacOS/Blender",
        "/opt/homebrew/bin/blender",
    ],
}
# DEPRECATED: The above constant will be removed in v0.2.
# Prefer blender.platform_hints in config/defaults.yaml or config/user.yaml.


class BlenderNotFoundError(RuntimeError):
    """Raised when the Blender executable cannot be located.

    Carries a list of all locations that were checked so the operator
    can diagnose the issue quickly.
    """

    def __init__(self, message: str, locations_checked: list[str]) -> None:
        super().__init__(message)
        self.locations_checked = locations_checked


@dataclass
class RunnerResult:
    """Structured result from a Blender subprocess invocation.

    Attributes:
        returncode:       The subprocess exit code. 0 = success.
        stdout:           Full captured stdout from the Blender process.
        stderr:           Full captured stderr from the Blender process.
        duration_seconds: Wall-clock seconds the process ran.
        timed_out:        True if the process was killed due to timeout.
    """

    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False


def resolve_blender_executable(config: dict[str, Any] | None = None) -> Path:
    """Resolve the path to the Blender executable.

    Priority chain (first match wins):
        1. Environment variable SEIDR_BLENDER_PATH (explicit override)
        2. config["blender"]["executable"] if provided and resolvable
        3. PATH lookup via shutil.which("blender")
        4. Platform-specific well-known locations

    Args:
        config: Optional config dict from load_config(). Used for step 2.

    Returns:
        A Path to the Blender executable.

    Raises:
        BlenderNotFoundError: If no executable can be found at any location.
    """
    checked: list[str] = []

    # Step 1: Environment variable
    env_path = os.environ.get("SEIDR_BLENDER_PATH") or os.environ.get("BLENDER_PATH")
    if env_path:
        p = Path(env_path)
        checked.append(f"env:SEIDR_BLENDER_PATH={env_path}")
        if p.is_file():
            logger.debug("Blender resolved via env var: %s", p)
            return p

    # Step 2: Config dict
    if config:
        config_exe = config.get("blender", {}).get("executable")
        if config_exe and config_exe != "blender":
            p = Path(config_exe)
            checked.append(f"config:blender.executable={config_exe}")
            if p.is_file():
                logger.debug("Blender resolved via config: %s", p)
                return p

    # Step 3: PATH lookup
    which_result = shutil.which("blender")
    checked.append("PATH:blender")
    if which_result:
        logger.debug("Blender resolved via PATH: %s", which_result)
        return Path(which_result)

    # Also try config value "blender" as a PATH lookup (when config_exe == "blender")
    if config:
        config_exe = config.get("blender", {}).get("executable", "blender")
        if config_exe:
            which_result = shutil.which(config_exe)
            checked.append(f"PATH:{config_exe}")
            if which_result:
                logger.debug("Blender resolved via config+PATH: %s", which_result)
                return Path(which_result)

    # Step 4: Platform-specific hints.
    # AUDIT-004: Read hints from config/defaults.yaml (blender.platform_hints) first.
    # Falls back to the _PLATFORM_HINTS constant if the config key is absent.
    import sys

    config_hints: list[str] = []
    if config:
        platform_hints_cfg = config.get("blender", {}).get("platform_hints", {})
        if isinstance(platform_hints_cfg, dict):
            config_hints = platform_hints_cfg.get(sys.platform, [])

    # Use config-driven hints if present; otherwise fall back to the deprecated constant.
    if config_hints:
        hints = config_hints
        hint_source = "config"
    else:
        hints = _PLATFORM_HINTS.get(sys.platform, [])
        hint_source = "deprecated-constant"

    for hint in hints:
        checked.append(f"platform-hint({hint_source}):{hint}")
        p = Path(hint)
        if p.is_file():
            logger.debug("Blender resolved via platform hint (%s): %s", hint_source, p)
            return p

    raise BlenderNotFoundError(
        "Blender executable not found. "
        "Set the SEIDR_BLENDER_PATH environment variable to the full path of your "
        "blender executable, or set blender.executable in config/user.yaml.",
        locations_checked=checked,
    )


def run_blender(
    script_path: Path,
    args: list[str],
    config: dict[str, Any] | None = None,
    timeout: int | None = None,
    on_line: Callable[[str], None] | None = None,
) -> RunnerResult:
    """Launch a Blender subprocess in background mode with the given script.

    The invocation is:
        blender --background --python <script_path> -- <args...>

    Args:
        script_path:  Path to the Blender Python script to inject.
        args:         List of argument strings passed after '--' to the script.
        config:       Optional config dict (used for executable resolution and timeout).
        timeout:      Max seconds to wait. Overrides config if given. Default: 300.
        on_line:      Optional callback called with each stdout line as it arrives.
                      Used by Annáll telemetry to stream Blender progress.

    Returns:
        RunnerResult with returncode, stdout, stderr, duration, timed_out flag.

    Raises:
        BlenderNotFoundError: If the Blender executable cannot be located.
        OSError: If the subprocess cannot be launched (permissions, etc.)
    """
    blender_exe = resolve_blender_executable(config)

    # Resolve timeout: explicit arg > config > default 300s
    if timeout is None:
        timeout = int((config or {}).get("blender", {}).get("timeout_seconds", 300))

    cmd: list[str] = [
        str(blender_exe),
        "--background",
        "--python",
        str(script_path),
        "--",  # Blender stops parsing args here; remainder goes to the script
        *args,
    ]

    logger.debug("Launching Blender subprocess: %s", " ".join(cmd))
    start_time = time.monotonic()

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    timed_out = False

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        # Stream stdout line by line for the on_line callback; capture all output.
        try:
            # H-006: Replace assert statements with explicit RuntimeError guards.
            # assert is silently stripped under python -O, giving a cryptic TypeError
            # when the loop tries to iterate over None.
            if process.stdout is None or process.stderr is None:
                raise RuntimeError(
                    "Blender subprocess stdout/stderr are None despite PIPE flag. "
                    "This is a platform or Python version bug — cannot stream output."
                )

            # Collect stdout with optional line streaming
            for line in process.stdout:
                line_stripped = line.rstrip("\n")
                stdout_lines.append(line_stripped)
                if on_line is not None:
                    try:
                        on_line(line_stripped)
                    except Exception:
                        pass  # Never let a callback kill the subprocess reader

            # Wait for process and collect remaining stderr.
            # H-015 note: stdout EOF is reached first (process closes stdout before
            # exiting). communicate() then drains any remaining stderr buffer.
            # H-002: Add a hard timeout to the post-kill communicate() path so a
            # wedged Windows process (e.g. AV hold, open handles) cannot hang the
            # forge indefinitely. The post-kill window is 30 s — generous for normal
            # TerminateProcess() but bounded for pathological cases.
            _POST_KILL_TIMEOUT = 30
            try:
                _, stderr_raw = process.communicate(timeout=timeout)
                stderr_lines.extend(stderr_raw.splitlines() if stderr_raw else [])
            except subprocess.TimeoutExpired:
                process.kill()
                try:
                    _, stderr_raw = process.communicate(timeout=_POST_KILL_TIMEOUT)
                    stderr_lines.extend(stderr_raw.splitlines() if stderr_raw else [])
                except subprocess.TimeoutExpired:
                    # H-002: Process did not die within post-kill window.
                    # Log clearly and continue — we cannot block forever.
                    logger.error(
                        "Blender process did not terminate after kill "
                        "(post-kill timeout=%ds, script=%s). "
                        "Continuing without further stderr collection.",
                        _POST_KILL_TIMEOUT,
                        script_path,
                    )
                timed_out = True
                logger.warning(
                    "Blender subprocess timed out after %d seconds (script: %s)",
                    timeout,
                    script_path,
                )
        except Exception as exc:
            logger.error("Error reading Blender subprocess output: %s", exc)
            process.kill()
            process.wait()

    except OSError as exc:
        raise OSError(
            f"Failed to launch Blender subprocess. "
            f"Executable: {blender_exe}. Error: {exc}"
        ) from exc

    duration = time.monotonic() - start_time
    returncode = process.returncode if process.returncode is not None else -1

    result = RunnerResult(
        returncode=returncode,
        stdout="\n".join(stdout_lines),
        stderr="\n".join(stderr_lines),
        duration_seconds=duration,
        timed_out=timed_out,
    )

    logger.debug(
        "Blender subprocess finished: returncode=%d, duration=%.1fs, timed_out=%s",
        returncode,
        duration,
        timed_out,
    )
    return result
