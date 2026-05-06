"""seidr_smidja.forge.runner — Forge build orchestration.

Translates an AvatarSpec + base asset path → ForgeResult by:
    1. Serializing the spec to a temporary JSON file (Blender reads it)
    2. Calling _internal.blender_runner.run_blender() with the build script
    3. Checking the result, locating the output .vrm, returning ForgeResult

Per D-003: the Forge imports from _internal.blender_runner for the low-level
subprocess mechanics. The Forge only owns the orchestration and argument
construction.

Per D-007: Forge and Oracle Eye use separate Blender subprocess invocations.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from seidr_smidja._internal.blender_runner import (
    BlenderNotFoundError,
    RunnerResult,
    run_blender,
)
from seidr_smidja.forge.exceptions import ForgeBuildError
from seidr_smidja.loom.schema import AvatarSpec

logger = logging.getLogger(__name__)

# Path to the Blender build script (relative to this file)
_BUILD_SCRIPT = Path(__file__).parent / "scripts" / "build_avatar.py"


@dataclass
class ForgeResult:
    """Result of a Forge build attempt.

    Attributes:
        success:            True if Blender exited 0 and output .vrm was created.
        vrm_path:           Path to the produced .vrm file. None if success=False.
        exit_code:          Blender subprocess exit code.
        stderr_capture:     Full captured stderr.
        stdout_capture:     Full captured stdout.
        blender_script_path: The injected build script path.
        elapsed_seconds:    Wall-clock time for the build.
    """

    success: bool
    vrm_path: Path | None
    exit_code: int
    stderr_capture: str
    stdout_capture: str
    blender_script_path: Path
    elapsed_seconds: float


def build(
    spec: AvatarSpec,
    base_asset: Path,
    output_dir: Path,
    config: dict[str, Any] | None = None,
    annall: Any = None,
    session_id: Any = None,
) -> ForgeResult:
    """Build a .vrm avatar from spec + base asset using Blender.

    Args:
        spec:        Validated AvatarSpec from the Loom.
        base_asset:  Path to the base .vrm file from the Hoard.
        output_dir:  Directory to write the output .vrm into. Must exist.
        config:      Config dict for Blender path resolution + timeout.
        annall:      Optional AnnallPort for event logging (D-005).
        session_id:  Session ID for Annáll events.

    Returns:
        ForgeResult — always returned (success or failure). Only raises
        ForgeBuildError on pre-launch failure (not on Blender subprocess failure).

    Raises:
        ForgeBuildError: If Blender can't be found or output_dir is not writable.
    """
    start = time.monotonic()

    # Validate pre-conditions
    if not output_dir.exists():
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ForgeBuildError(
                f"Cannot create output directory {output_dir}: {exc}", cause=exc
            ) from exc

    if not base_asset.exists():
        raise ForgeBuildError(f"Base asset not found: {base_asset}")

    if not _BUILD_SCRIPT.exists():
        raise ForgeBuildError(
            f"Forge build script not found at {_BUILD_SCRIPT}. "
            "This is an installation error — the build script should ship with the package."
        )

    # Serialize spec to a temp JSON file (Blender reads it via argv)
    try:
        spec_dict = spec.to_dict()
        # Convert Path objects in the dict to strings (JSON serializable)
        spec_json = json.dumps(spec_dict, default=str, indent=2)
    except Exception as exc:
        raise ForgeBuildError(
            f"Failed to serialize AvatarSpec to JSON: {exc}", cause=exc
        ) from exc

    # Log forge.started to Annáll
    if annall is not None and session_id is not None:
        _log_annall(
            annall,
            session_id,
            "forge.started",
            {
                "avatar_id": spec.avatar_id,
                "base_asset": str(base_asset),
                "output_dir": str(output_dir),
                "build_script": str(_BUILD_SCRIPT),
            },
        )

    # H-001 fix: Single outer try/finally wraps the full block from mkdtemp through
    # subprocess completion, so temp dir is always cleaned up — even if the spec
    # write itself raises OSError before we ever enter the run_blender() try-block.
    import shutil
    import tempfile as _tempfile

    tmp_dir = None
    try:
        tmp_dir = Path(_tempfile.mkdtemp())
        spec_path: Path = tmp_dir / "spec.json"
        try:
            spec_path.write_text(spec_json, encoding="utf-8")
        except OSError as exc:
            raise ForgeBuildError(
                f"Failed to write temporary spec file: {exc}", cause=exc
            ) from exc

        output_vrm = output_dir / f"{spec.avatar_id}.vrm"

        # Build Blender args (these are passed after '--' to the script)
        blender_args = [
            "--spec",
            str(spec_path),
            "--base",
            str(base_asset),
            "--output",
            str(output_vrm),
        ]

        # Collect output lines for Annáll streaming
        stdout_lines: list[str] = []

        def on_line(line: str) -> None:
            stdout_lines.append(line)

        try:
            runner_result: RunnerResult = run_blender(
                script_path=_BUILD_SCRIPT,
                args=blender_args,
                config=config,
                on_line=on_line,
            )
        except BlenderNotFoundError as exc:
            raise ForgeBuildError(
                f"Blender not found — cannot run Forge build: {exc}",
                cause=exc,
            ) from exc
        except OSError as exc:
            raise ForgeBuildError(
                f"Failed to launch Blender subprocess: {exc}", cause=exc
            ) from exc

    finally:
        # H-001: Always clean up temp dir — covers spec write failure AND subprocess
        # failure paths. This finally runs even if ForgeBuildError is raised above.
        if tmp_dir is not None and tmp_dir.exists():
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass

    elapsed = time.monotonic() - start
    success = runner_result.returncode == 0 and output_vrm.exists()

    if success:
        logger.info(
            "Forge: build complete — %s (%.1fs)", output_vrm.name, elapsed
        )
        event_type = "forge.completed"
    else:
        logger.warning(
            "Forge: build failed — exit_code=%d, vrm_exists=%s (%.1fs)",
            runner_result.returncode,
            output_vrm.exists(),
            elapsed,
        )
        event_type = "forge.failed"

    # Log completion to Annáll
    if annall is not None and session_id is not None:
        _log_annall(
            annall,
            session_id,
            event_type,
            {
                "exit_code": runner_result.returncode,
                "success": success,
                "vrm_path": str(output_vrm) if output_vrm.exists() else None,
                "elapsed_seconds": elapsed,
                "timed_out": runner_result.timed_out,
                "stderr_tail": runner_result.stderr[-500:] if runner_result.stderr else "",
            },
        )

    return ForgeResult(
        success=success,
        vrm_path=output_vrm if output_vrm.exists() else None,
        exit_code=runner_result.returncode,
        stderr_capture=runner_result.stderr,
        stdout_capture="\n".join(stdout_lines),
        blender_script_path=_BUILD_SCRIPT,
        elapsed_seconds=elapsed,
    )


def _log_annall(
    annall: Any, session_id: Any, event_type: str, payload: dict[str, Any]
) -> None:
    """Log an event to Annáll, swallowing any errors."""
    try:
        from seidr_smidja.annall.port import AnnallEvent

        annall.log_event(session_id, AnnallEvent.info(event_type, payload))
    except Exception:
        pass
