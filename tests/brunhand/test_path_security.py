"""Tests for B-002: Path traversal protection on vroid endpoints.

Verifies that _validate_path_in_root rejects paths that escape the configured
export_root / project_root, and that the endpoint handlers return structured
path_security_error responses for traversal payloads.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


# ─── Unit tests for _validate_path_in_root ───────────────────────────────────


class TestValidatePathInRoot:
    """Direct unit tests for the path-validation helper."""

    def _validate(self, path_str: str, root_str: str) -> Path:
        from seidr_smidja.brunhand.daemon.runtime import _validate_path_in_root
        return _validate_path_in_root(path_str, root_str)

    def test_valid_relative_path_accepted(self, tmp_path: Path) -> None:
        result = self._validate("my_avatar.vrm", str(tmp_path))
        assert result == (tmp_path / "my_avatar.vrm").resolve()

    def test_valid_subdirectory_path_accepted(self, tmp_path: Path) -> None:
        result = self._validate("subdir/my_avatar.vrm", str(tmp_path))
        assert str(result).startswith(str(tmp_path.resolve()))

    def test_dotdot_traversal_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="outside the allowed root"):
            self._validate("../../etc/passwd", str(tmp_path))

    def test_absolute_escape_rejected(self, tmp_path: Path) -> None:
        """Absolute path outside root is rejected."""
        outside = str(Path(tmp_path).parent.parent / "sensitive")
        with pytest.raises(ValueError, match="outside the allowed root"):
            self._validate(outside, str(tmp_path))

    def test_tilde_path_rejected(self, tmp_path: Path) -> None:
        """Tilde-expanded path that escapes root is rejected."""
        home = Path("~").expanduser()
        if not str(home).startswith(str(tmp_path)):
            with pytest.raises(ValueError, match="outside the allowed root"):
                self._validate(str(home / "secrets.vroid"), str(tmp_path))

    def test_dotdot_embedded_in_filename_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="outside the allowed root"):
            self._validate("avatars/../../../etc/shadow", str(tmp_path))

    def test_path_exactly_at_root_accepted(self, tmp_path: Path) -> None:
        """A path that resolves exactly to a file directly in root is accepted."""
        result = self._validate("avatar.vrm", str(tmp_path))
        assert result.parent.resolve() == tmp_path.resolve()


# ─── Integration tests: vroid endpoint handlers ──────────────────────────────


def _make_export_req(output_path: str) -> "VroidExportVrmRequest":  # type: ignore[name-defined]
    from seidr_smidja.brunhand.models import VroidExportVrmRequest
    return VroidExportVrmRequest(
        request_id="test-id",
        session_id="",
        agent_id="test",
        output_path=output_path,
    )


def _make_open_req(project_path: str) -> "VroidOpenProjectRequest":  # type: ignore[name-defined]
    from seidr_smidja.brunhand.models import VroidOpenProjectRequest
    return VroidOpenProjectRequest(
        request_id="test-id",
        session_id="",
        agent_id="test",
        project_path=project_path,
    )


class TestVroidEndpointPathSecurity:
    """Path-traversal payloads against the vroid endpoint handlers."""

    def test_export_traversal_returns_path_security_error(self, tmp_path: Path) -> None:
        from seidr_smidja.brunhand.daemon.endpoints.vroid import handle_vroid_export_vrm

        req = _make_export_req("../../etc/passwd")
        with patch("seidr_smidja.brunhand.daemon.runtime.is_vroid_running", return_value=True):
            result = handle_vroid_export_vrm(
                req,
                daemon_cfg={"export_root": str(tmp_path)},
            )

        assert result.success is False
        assert result.error is not None
        assert result.error.error_type == "path_security_error"

    def test_open_traversal_returns_path_security_error(self, tmp_path: Path) -> None:
        from seidr_smidja.brunhand.daemon.endpoints.vroid import handle_vroid_open_project

        req = _make_open_req("../../sensitive.vroid")
        with patch("seidr_smidja.brunhand.daemon.runtime.is_vroid_running", return_value=True):
            result = handle_vroid_open_project(
                req,
                daemon_cfg={"project_root": str(tmp_path)},
            )

        assert result.success is False
        assert result.error is not None
        assert result.error.error_type == "path_security_error"

    def test_absolute_escape_on_export_rejected(self, tmp_path: Path) -> None:
        from seidr_smidja.brunhand.daemon.endpoints.vroid import handle_vroid_export_vrm

        # Absolute path outside export_root
        outside = str(tmp_path.parent / "evil.vrm")
        req = _make_export_req(outside)
        with patch("seidr_smidja.brunhand.daemon.runtime.is_vroid_running", return_value=True):
            result = handle_vroid_export_vrm(
                req,
                daemon_cfg={"export_root": str(tmp_path)},
            )

        assert result.success is False
        assert result.error is not None
        assert result.error.error_type == "path_security_error"

    def test_valid_path_passes_security_check(self, tmp_path: Path) -> None:
        """A valid relative path should not be rejected by security check."""
        from seidr_smidja.brunhand.daemon.endpoints.vroid import handle_vroid_export_vrm

        req = _make_export_req("avatar.vrm")
        # Patch runtime to simulate VRoid not running (stops after security check)
        with patch("seidr_smidja.brunhand.daemon.runtime.is_vroid_running", return_value=False):
            result = handle_vroid_export_vrm(
                req,
                daemon_cfg={"export_root": str(tmp_path)},
            )

        # Should fail because VRoid is not running, NOT because of path security
        assert result.success is False
        assert result.error is not None
        assert result.error.error_type != "path_security_error"

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific drive-letter test")
    def test_windows_drive_letter_escape_rejected(self, tmp_path: Path) -> None:
        """C:\\Windows\\System32 should be rejected even on Windows."""
        from seidr_smidja.brunhand.daemon.endpoints.vroid import handle_vroid_export_vrm

        req = _make_export_req("C:\\Windows\\System32\\evil.vrm")
        with patch("seidr_smidja.brunhand.daemon.runtime.is_vroid_running", return_value=True):
            result = handle_vroid_export_vrm(
                req,
                daemon_cfg={"export_root": str(tmp_path)},
            )

        assert result.success is False
        assert result.error is not None
        assert result.error.error_type == "path_security_error"

    def test_dotdot_embedded_export_rejected(self, tmp_path: Path) -> None:
        from seidr_smidja.brunhand.daemon.endpoints.vroid import handle_vroid_export_vrm

        req = _make_export_req("sub/../../../evil.vrm")
        with patch("seidr_smidja.brunhand.daemon.runtime.is_vroid_running", return_value=True):
            result = handle_vroid_export_vrm(
                req,
                daemon_cfg={"export_root": str(tmp_path)},
            )

        assert result.success is False
        assert result.error is not None
        assert result.error.error_type == "path_security_error"
