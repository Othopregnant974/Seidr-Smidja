"""Tests for H-001 (temp dir leak), H-002 (post-kill timeout), H-006 (assert→RuntimeError)."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ─── H-001: Temp directory cleanup on OSError ────────────────────────────────


class TestForgeTmpDirCleanup:
    """H-001: tmp_dir must be cleaned up even when spec-file write raises OSError."""

    def test_tmp_dir_cleaned_up_on_write_failure(self, tmp_path: Path) -> None:
        """Simulate a disk-full OSError on spec write — temp dir must not survive."""
        from seidr_smidja.forge.exceptions import ForgeBuildError
        from seidr_smidja.forge.runner import build
        from seidr_smidja.loom.schema import AvatarSpec

        # Create a fake base asset file
        base_asset = tmp_path / "base.vrm"
        base_asset.write_bytes(b"\x00" * 16)

        spec = AvatarSpec.model_validate({
            "spec_version": "1.0",
            "avatar_id": "test_h001",
            "display_name": "H001 Test",
            "base_asset_id": "vroid/sample_a",
            "metadata": {"author": "Test", "license": "CC0-1.0"},
        })

        created_tmp_dirs: list[Path] = []

        original_mkdtemp = __import__("tempfile").mkdtemp

        def tracking_mkdtemp(**kwargs):
            d = original_mkdtemp(**kwargs)
            created_tmp_dirs.append(Path(d))
            return d

        # Patch write_text to raise OSError after mkdtemp succeeds
        with (
            patch("tempfile.mkdtemp", side_effect=tracking_mkdtemp),
            patch.object(Path, "write_text", side_effect=OSError("disk full")),
            pytest.raises(ForgeBuildError, match="Failed to write temporary spec file"),
        ):
            build(spec, base_asset, tmp_path / "output")

        # All created temp dirs should have been cleaned up
        for td in created_tmp_dirs:
            assert not td.exists(), f"Temp dir leaked: {td}"

    def test_tmp_dir_cleaned_up_on_blender_not_found(self, tmp_path: Path) -> None:
        """Temp dir must be cleaned up when BlenderNotFoundError is raised."""
        from seidr_smidja._internal.blender_runner import BlenderNotFoundError
        from seidr_smidja.forge.exceptions import ForgeBuildError
        from seidr_smidja.forge.runner import build
        from seidr_smidja.loom.schema import AvatarSpec

        base_asset = tmp_path / "base.vrm"
        base_asset.write_bytes(b"\x00" * 16)

        spec = AvatarSpec.model_validate({
            "spec_version": "1.0",
            "avatar_id": "test_h001b",
            "display_name": "H001b Test",
            "base_asset_id": "vroid/sample_a",
            "metadata": {"author": "Test", "license": "CC0-1.0"},
        })

        created_tmp_dirs: list[Path] = []
        original_mkdtemp = __import__("tempfile").mkdtemp

        def tracking_mkdtemp(**kwargs):
            d = original_mkdtemp(**kwargs)
            created_tmp_dirs.append(Path(d))
            return d

        with patch("tempfile.mkdtemp", side_effect=tracking_mkdtemp), patch(
            "seidr_smidja._internal.blender_runner.resolve_blender_executable",
            side_effect=BlenderNotFoundError("not found", []),
        ), pytest.raises(ForgeBuildError):
            build(spec, base_asset, tmp_path / "output")

        for td in created_tmp_dirs:
            assert not td.exists(), f"Temp dir leaked: {td}"


# ─── H-006: assert replaced by RuntimeError guards ───────────────────────────


class TestBlenderRunnerNullHandles:
    """H-006: run_blender must emit a RuntimeError log (not crash with cryptic TypeError)
    when stdout/stderr are None. The outer except handler catches it so run_blender
    still returns a result — it never crashes the forge on bad PIPE state."""

    def test_null_stdout_logs_error_not_type_error(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """If process.stdout is None, the H-006 guard raises RuntimeError with a clear
        message. The outer except handler catches it and logs it. No cryptic TypeError
        from 'for line in None'."""
        import logging

        from seidr_smidja._internal.blender_runner import run_blender

        fake_script = tmp_path / "fake.py"
        fake_script.write_text("pass")

        mock_process = MagicMock()
        mock_process.stdout = None  # Trigger the H-006 guard
        mock_process.stderr = None
        mock_process.returncode = 0

        fake_blender = tmp_path / "blender.exe"
        fake_blender.write_bytes(b"")

        resolve_path = (
            "seidr_smidja._internal.blender_runner.resolve_blender_executable"
        )
        with (
            caplog.at_level(
                logging.ERROR, logger="seidr_smidja._internal.blender_runner"
            ),
            patch(resolve_path, return_value=fake_blender),
            patch("subprocess.Popen", return_value=mock_process),
        ):
            # run_blender should return (not raise) — the error is logged
            run_blender(fake_script, [], config={})

        # The error must be logged with the H-006 message, not a cryptic TypeError
        error_messages = [r.message for r in caplog.records if r.levelno >= logging.ERROR]
        assert any("stdout/stderr are None" in str(m) for m in error_messages), (
            f"Expected H-006 guard message in logs. Got: {error_messages}"
        )


# ─── H-002: Post-kill communicate timeout ────────────────────────────────────


class TestBlenderPostKillTimeout:
    """H-002: communicate() after process.kill() must have a timeout."""

    def test_post_kill_communicate_has_timeout(self, tmp_path: Path) -> None:
        """When TimeoutExpired fires, communicate() in the except branch uses timeout."""
        from seidr_smidja._internal.blender_runner import run_blender

        fake_script = tmp_path / "fake.py"
        fake_script.write_text("pass")
        fake_blender = tmp_path / "blender.exe"
        fake_blender.write_bytes(b"")

        communicate_call_kwargs: list[dict] = []

        # First communicate raises TimeoutExpired, second succeeds
        call_count = 0

        def mock_communicate(timeout=None):
            nonlocal call_count
            communicate_call_kwargs.append({"timeout": timeout})
            call_count += 1
            if call_count == 1:
                raise subprocess.TimeoutExpired(cmd="blender", timeout=1)
            return (None, "")  # post-kill drain

        mock_process = MagicMock()
        mock_process.stdout = iter([])  # empty stdout
        mock_process.stderr = MagicMock()
        mock_process.returncode = -9
        mock_process.communicate.side_effect = mock_communicate

        resolve_path = (
            "seidr_smidja._internal.blender_runner.resolve_blender_executable"
        )
        with (
            patch(resolve_path, return_value=fake_blender),
            patch("subprocess.Popen", return_value=mock_process),
        ):
            result = run_blender(fake_script, [], timeout=1, config={})

        # The second communicate call (post-kill) must have a timeout set
        assert len(communicate_call_kwargs) >= 2, "Expected at least two communicate() calls"
        post_kill_kwargs = communicate_call_kwargs[1]
        assert post_kill_kwargs["timeout"] is not None, (
            "Post-kill communicate() must have a timeout — H-002 guard missing"
        )
        assert result.timed_out is True
