"""Tests for seidr_smidja.brunhand.daemon.endpoints — endpoint handlers (no live daemon)."""
from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


def _make_req(model_class, **kwargs) -> Any:  # type: ignore[type-arg]
    """Build a minimal request model for the given class."""
    defaults = {
        "request_id": str(uuid.uuid4()),
        "session_id": "",
        "agent_id": "test",
    }
    defaults.update(kwargs)
    return model_class(**defaults)


class TestHandleScreenshot:
    def test_returns_envelope_on_success(self) -> None:
        from seidr_smidja.brunhand.daemon.endpoints.primitives import handle_screenshot
        from seidr_smidja.brunhand.models import BrunhandResponseEnvelope, ScreenshotRequest

        req = _make_req(ScreenshotRequest)
        with patch("seidr_smidja.brunhand.daemon.runtime.take_screenshot") as mock_cap, \
             patch("seidr_smidja.brunhand.daemon.capabilities.is_primitive_available", return_value=True):
            mock_cap.return_value = {
                "png_bytes_b64": "AAAA",
                "width": 1920, "height": 1080,
                "captured_at": "2026-01-01T00:00:00Z",
                "monitor_index": 0,
            }
            result = handle_screenshot(req)

        assert isinstance(result, BrunhandResponseEnvelope)

    def test_never_raises(self) -> None:
        from seidr_smidja.brunhand.daemon.endpoints.primitives import handle_screenshot
        from seidr_smidja.brunhand.models import ScreenshotRequest

        req = _make_req(ScreenshotRequest)
        with patch("seidr_smidja.brunhand.daemon.runtime.take_screenshot", side_effect=RuntimeError("boom")), \
             patch("seidr_smidja.brunhand.daemon.capabilities.is_primitive_available", return_value=True):
            result = handle_screenshot(req)
        # INVARIANT: never raises — returns error envelope
        assert result.success is False


class TestHandleClick:
    def test_returns_envelope_on_success(self) -> None:
        from seidr_smidja.brunhand.daemon.endpoints.primitives import handle_click
        from seidr_smidja.brunhand.models import ClickRequest

        req = _make_req(ClickRequest, x=100, y=200)
        with patch("seidr_smidja.brunhand.daemon.runtime.do_click") as mock_click, \
             patch("seidr_smidja.brunhand.daemon.capabilities.is_primitive_available", return_value=True):
            mock_click.return_value = {"x": 100, "y": 200, "clicks_delivered": 1, "button": "left"}
            result = handle_click(req)

        assert result.success is True

    def test_never_raises_on_error(self) -> None:
        from seidr_smidja.brunhand.daemon.endpoints.primitives import handle_click
        from seidr_smidja.brunhand.models import ClickRequest

        req = _make_req(ClickRequest, x=0, y=0)
        with patch("seidr_smidja.brunhand.daemon.runtime.do_click", side_effect=OSError("no access")), \
             patch("seidr_smidja.brunhand.daemon.capabilities.is_primitive_available", return_value=True):
            result = handle_click(req)

        assert result.success is False

    def test_returns_capabilities_error_when_unavailable(self) -> None:
        """B-006: capability_unavailable returns structured capabilities_error."""
        from seidr_smidja.brunhand.daemon.endpoints.primitives import handle_click
        from seidr_smidja.brunhand.models import ClickRequest

        req = _make_req(ClickRequest, x=0, y=0)
        with patch("seidr_smidja.brunhand.daemon.capabilities.is_primitive_available", return_value=False):
            result = handle_click(req)

        assert result.success is False
        assert result.error is not None
        assert result.error.error_type == "capabilities_error"


class TestHandleHotkey:
    def test_returns_envelope(self) -> None:
        from seidr_smidja.brunhand.daemon.endpoints.primitives import handle_hotkey
        from seidr_smidja.brunhand.models import HotkeyRequest

        req = _make_req(HotkeyRequest, keys=["ctrl", "s"])
        with patch("seidr_smidja.brunhand.daemon.runtime.do_hotkey") as mock_hk, \
             patch("seidr_smidja.brunhand.daemon.capabilities.is_primitive_available", return_value=True):
            mock_hk.return_value = {"keys": ["ctrl", "s"]}
            result = handle_hotkey(req)
        assert result.success is True


class TestHandleWaitForWindow:
    def test_returns_found_false_on_timeout(self) -> None:
        from seidr_smidja.brunhand.daemon.endpoints.primitives import handle_wait_for_window
        from seidr_smidja.brunhand.models import WaitForWindowRequest

        req = _make_req(WaitForWindowRequest, title_pattern="VRoid Studio", timeout_seconds=0.1)
        with patch("seidr_smidja.brunhand.daemon.runtime.do_wait_for_window") as mock_wfw, \
             patch("seidr_smidja.brunhand.daemon.capabilities.is_primitive_available", return_value=True):
            mock_wfw.return_value = {"found": False, "elapsed_seconds": 0.1}
            result = handle_wait_for_window(req)
        # Timeout = success=True, found=False (NOT an error)
        assert result.success is True


class TestHandleVroidExportVrm:
    def test_vroid_not_running_returns_structured_error(self) -> None:
        from seidr_smidja.brunhand.daemon.endpoints.vroid import handle_vroid_export_vrm
        from seidr_smidja.brunhand.models import VroidExportVrmRequest

        req = _make_req(VroidExportVrmRequest, output_path="out.vrm")
        with patch("seidr_smidja.brunhand.daemon.runtime.is_vroid_running", return_value=False):
            result = handle_vroid_export_vrm(req)

        assert result.success is False
        assert result.error is not None
        assert result.error.error_type == "VroidNotRunningError"
        assert result.error.vroid_running is False

    def test_never_raises(self) -> None:
        from seidr_smidja.brunhand.daemon.endpoints.vroid import handle_vroid_export_vrm
        from seidr_smidja.brunhand.models import VroidExportVrmRequest

        req = _make_req(VroidExportVrmRequest, output_path="out.vrm")
        with patch("seidr_smidja.brunhand.daemon.runtime.is_vroid_running", return_value=True), \
             patch("seidr_smidja.brunhand.daemon.runtime.vroid_export_vrm", side_effect=RuntimeError("disk full")):
            result = handle_vroid_export_vrm(req)
        assert result.success is False


class TestHandleHealth:
    def test_returns_health_data(self) -> None:
        from seidr_smidja.brunhand.daemon.endpoints.health import get_health_response
        result = get_health_response()
        assert isinstance(result, dict)
        assert "status" in result
        assert result["status"] == "ok"
        assert "daemon_version" in result
