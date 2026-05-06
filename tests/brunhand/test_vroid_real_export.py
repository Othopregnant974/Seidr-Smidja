"""Tests for B-003: vroid_export_vrm and vroid_open_project path-typing.

Verifies that:
- The runtime functions call pyautogui to type the resolved path into the dialog.
- When the export dialog does not appear, the function returns structured failure.
- When the file appears on disk after confirm, success=True is returned.
- When the file does NOT appear after confirm, success=False is returned (honest failure).
- Agents receive a clear BrunhandCapabilityError when pyautogui is absent.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest


class TestVroidExportVrmPathTyping:
    """B-003: vroid_export_vrm actually types the path into the dialog."""

    def test_path_typed_into_dialog_when_dialog_opens(self, tmp_path: Path) -> None:
        """Verify Ctrl+A + typewrite sequence is called with resolved path."""
        import seidr_smidja.brunhand.daemon.runtime as rt

        # Create the export root
        export_root = str(tmp_path)
        output_path = "test_avatar.vrm"
        expected_full_path = str((tmp_path / output_path).resolve())

        # The file we'll "create" after confirm to simulate VRoid writing it
        target_file = tmp_path / output_path

        mock_pyautogui = MagicMock()
        mock_psutil = MagicMock()
        # Simulate VRoid process running
        proc_mock = MagicMock()
        proc_mock.info = {"name": "vroid_studio.exe"}
        mock_psutil.process_iter.return_value = [proc_mock]

        # Simulate: dialog appears, file appears after confirm
        dialog_found_result = {"found": True, "elapsed_seconds": 0.5, "window": {"title": "Export VRM"}}
        dialog_not_found = {"found": False, "elapsed_seconds": 10.0, "window": None}

        def create_file_side_effect(*args: object, **kwargs: object) -> None:
            target_file.write_bytes(b"fake vrm content")

        with (
            patch.object(rt, "_pyautogui", mock_pyautogui),
            patch.object(rt, "_PYAUTOGUI_AVAILABLE", True),
            patch.object(rt, "_PSUTIL_AVAILABLE", True),
            patch.object(rt, "_psutil", mock_psutil),
            patch.object(rt, "do_wait_for_window", return_value=dialog_found_result),
            patch.object(rt, "do_hotkey") as mock_hotkey,
            patch("time.sleep"),
        ):
            # Simulate file appearing after the confirm hotkey
            original_wait = rt._wait_for_file

            def mock_wait_for_file(path: Path, timeout: float, poll_interval: float = 0.5) -> bool:
                # Create the file to simulate VRoid exporting it
                path.write_bytes(b"fake vrm")
                return True

            with patch.object(rt, "_wait_for_file", side_effect=mock_wait_for_file):
                result = rt.vroid_export_vrm(
                    output_path=output_path,
                    export_root=export_root,
                )

        # Check Ctrl+A was called (select all in dialog field)
        mock_pyautogui.hotkey.assert_any_call("ctrl", "a")
        # Check typewrite was called with the resolved path
        mock_pyautogui.typewrite.assert_called_once_with(expected_full_path, interval=0.03)
        # Check success
        assert result.get("success") is True
        assert result.get("exported_path") == expected_full_path

    def test_export_returns_failure_when_dialog_does_not_appear(self, tmp_path: Path) -> None:
        """When the export dialog never appears, return structured failure."""
        import seidr_smidja.brunhand.daemon.runtime as rt

        mock_pyautogui = MagicMock()
        mock_psutil = MagicMock()
        proc_mock = MagicMock()
        proc_mock.info = {"name": "vroid_studio.exe"}
        mock_psutil.process_iter.return_value = [proc_mock]

        dialog_not_found = {"found": False, "elapsed_seconds": 15.0, "window": None}

        with (
            patch.object(rt, "_pyautogui", mock_pyautogui),
            patch.object(rt, "_PYAUTOGUI_AVAILABLE", True),
            patch.object(rt, "_PSUTIL_AVAILABLE", True),
            patch.object(rt, "_psutil", mock_psutil),
            patch.object(rt, "do_wait_for_window", return_value=dialog_not_found),
            patch.object(rt, "do_hotkey"),
            patch("time.sleep"),
        ):
            result = rt.vroid_export_vrm(
                output_path="avatar.vrm",
                export_root=str(tmp_path),
            )

        assert result.get("success") is False
        assert "dialog" in result.get("error", "").lower()

    def test_export_returns_failure_when_file_not_created(self, tmp_path: Path) -> None:
        """When dialog confirmed but file not found on disk, return honest failure."""
        import seidr_smidja.brunhand.daemon.runtime as rt

        mock_pyautogui = MagicMock()
        mock_psutil = MagicMock()
        proc_mock = MagicMock()
        proc_mock.info = {"name": "vroid_studio.exe"}
        mock_psutil.process_iter.return_value = [proc_mock]

        dialog_found = {"found": True, "elapsed_seconds": 0.5, "window": {"title": "Export VRM"}}

        with (
            patch.object(rt, "_pyautogui", mock_pyautogui),
            patch.object(rt, "_PYAUTOGUI_AVAILABLE", True),
            patch.object(rt, "_PSUTIL_AVAILABLE", True),
            patch.object(rt, "_psutil", mock_psutil),
            patch.object(rt, "do_wait_for_window", return_value=dialog_found),
            patch.object(rt, "do_hotkey"),
            patch.object(rt, "_wait_for_file", return_value=False),  # file never appeared
            patch("time.sleep"),
        ):
            result = rt.vroid_export_vrm(
                output_path="avatar.vrm",
                export_root=str(tmp_path),
            )

        assert result.get("success") is False
        assert result.get("exported_path") is None
        assert "not found" in result.get("error", "").lower() or "not appear" in result.get("error", "").lower()

    def test_export_raises_capability_error_when_pyautogui_absent(self, tmp_path: Path) -> None:
        """When pyautogui is not installed, raises CapabilityRuntimeError."""
        import seidr_smidja.brunhand.daemon.runtime as rt

        mock_psutil = MagicMock()
        proc_mock = MagicMock()
        proc_mock.info = {"name": "vroid_studio.exe"}
        mock_psutil.process_iter.return_value = [proc_mock]

        with (
            patch.object(rt, "_PYAUTOGUI_AVAILABLE", False),
            patch.object(rt, "_PSUTIL_AVAILABLE", True),
            patch.object(rt, "_psutil", mock_psutil),
        ):
            with pytest.raises(rt.CapabilityRuntimeError, match="vroid_export_vrm"):
                rt.vroid_export_vrm(
                    output_path="avatar.vrm",
                    export_root=str(tmp_path),
                )


class TestVroidOpenProjectPathTyping:
    """B-003: vroid_open_project actually types the path into the dialog."""

    def test_path_typed_into_open_dialog(self, tmp_path: Path) -> None:
        """Verify Ctrl+A + typewrite is called with the resolved project path."""
        import seidr_smidja.brunhand.daemon.runtime as rt

        project_root = str(tmp_path)
        project_path = "my_character.vroid"
        # Create the file so the pre-flight existence check passes
        source_file = tmp_path / project_path
        source_file.write_bytes(b"fake vroid project")
        expected_full_path = str(source_file.resolve())

        mock_pyautogui = MagicMock()
        mock_psutil = MagicMock()
        proc_mock = MagicMock()
        proc_mock.info = {"name": "vroid_studio.exe"}
        mock_psutil.process_iter.return_value = [proc_mock]

        dialog_found = {"found": True, "elapsed_seconds": 0.3, "window": {"title": "Open"}}
        vroid_loaded = {"found": True, "elapsed_seconds": 2.0, "window": {"title": "VRoid Studio"}}

        wait_results = iter([dialog_found, vroid_loaded])

        with (
            patch.object(rt, "_pyautogui", mock_pyautogui),
            patch.object(rt, "_PYAUTOGUI_AVAILABLE", True),
            patch.object(rt, "_PSUTIL_AVAILABLE", True),
            patch.object(rt, "_psutil", mock_psutil),
            patch.object(rt, "do_wait_for_window", side_effect=list(wait_results)),
            patch.object(rt, "do_hotkey"),
            patch("time.sleep"),
        ):
            result = rt.vroid_open_project(
                project_path=project_path,
                project_root=project_root,
            )

        mock_pyautogui.hotkey.assert_any_call("ctrl", "a")
        mock_pyautogui.typewrite.assert_called_once_with(expected_full_path, interval=0.03)
        assert result.get("success") is True
        assert result.get("opened_path") == expected_full_path

    def test_open_nonexistent_file_raises_runtime_error(self, tmp_path: Path) -> None:
        """Opening a non-existent file raises RuntimeError before GUI interaction."""
        import seidr_smidja.brunhand.daemon.runtime as rt

        mock_psutil = MagicMock()
        proc_mock = MagicMock()
        proc_mock.info = {"name": "vroid_studio.exe"}
        mock_psutil.process_iter.return_value = [proc_mock]

        with (
            patch.object(rt, "_PYAUTOGUI_AVAILABLE", True),
            patch.object(rt, "_PSUTIL_AVAILABLE", True),
            patch.object(rt, "_psutil", mock_psutil),
        ):
            with pytest.raises(RuntimeError, match="does not exist"):
                rt.vroid_open_project(
                    project_path="nonexistent.vroid",
                    project_root=str(tmp_path),
                )

    def test_open_raises_capability_error_when_pyautogui_absent(self, tmp_path: Path) -> None:
        """When pyautogui absent, raises CapabilityRuntimeError."""
        import seidr_smidja.brunhand.daemon.runtime as rt

        mock_psutil = MagicMock()
        proc_mock = MagicMock()
        proc_mock.info = {"name": "vroid_studio.exe"}
        mock_psutil.process_iter.return_value = [proc_mock]

        with (
            patch.object(rt, "_PYAUTOGUI_AVAILABLE", False),
            patch.object(rt, "_PSUTIL_AVAILABLE", True),
            patch.object(rt, "_psutil", mock_psutil),
        ):
            with pytest.raises(rt.CapabilityRuntimeError, match="vroid_open_project"):
                rt.vroid_open_project(
                    project_path="test.vroid",
                    project_root=str(tmp_path),
                )
