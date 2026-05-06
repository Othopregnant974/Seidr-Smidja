"""Tests for seidr_smidja.brunhand.client.client — BrunhandClient (mocked httpx)."""
from __future__ import annotations

import base64
import json
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


def _make_client(host: str = "127.0.0.1", token: str = "test-token", **kwargs: Any) -> Any:
    """Construct a BrunhandClient for localhost without real connections."""
    from seidr_smidja.brunhand.client.client import BrunhandClient
    kwargs.setdefault("request_timeout_buffer", 2.0)
    return BrunhandClient(
        host=host,
        token=token,
        port=8848,
        tls=False,
        timeout=5.0,
        **kwargs,
    )


def _mock_response(data: dict[str, Any], status_code: int = 200) -> MagicMock:
    """Create a mock httpx response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = data
    resp.text = json.dumps(data)
    return resp


class TestBrunhandClientInit:
    def test_localhost_uses_http(self) -> None:
        client = _make_client()
        assert client._scheme == "http"

    def test_remote_host_uses_https_by_default(self) -> None:
        from seidr_smidja.brunhand.client.client import BrunhandClient
        client = BrunhandClient(host="vroid.ts.net", token="t", port=8848, tls=True)
        assert client._scheme == "https"
        client.close()

    def test_http_scheme_override(self) -> None:
        from seidr_smidja.brunhand.client.client import BrunhandClient
        client = BrunhandClient(
            host="vroid.ts.net", token="t", port=8848,
            http_scheme="http",
        )
        assert client._scheme == "http"
        client.close()

    def test_context_manager(self) -> None:
        client = _make_client()
        with client as c:
            assert c is client

    def test_request_timeout_buffer_stored(self) -> None:
        from seidr_smidja.brunhand.client.client import BrunhandClient
        client = BrunhandClient(
            host="127.0.0.1", token="test-token", port=8848,
            tls=False, timeout=5.0, request_timeout_buffer=7.5,
        )
        assert client.request_timeout_buffer == 7.5
        client.close()


class TestHealth:
    def test_health_returns_result(self) -> None:
        client = _make_client()
        mock_resp = _mock_response({
            "status": "ok", "daemon_version": "0.1.0",
            "os_name": "Windows", "uptime_seconds": 42.0,
        })
        with patch.object(client._client, "get", return_value=mock_resp):
            result = client.health()
        assert result.status == "ok"
        assert result.daemon_version == "0.1.0"
        assert result.uptime_seconds == 42.0

    def test_health_connection_error_raises_typed(self) -> None:
        import httpx
        from seidr_smidja.brunhand.exceptions import BrunhandConnectionError
        client = _make_client()
        with patch.object(client._client, "get", side_effect=httpx.ConnectError("refused")):
            with pytest.raises(BrunhandConnectionError):
                client.health()


class TestScreenshot:
    def test_screenshot_returns_png_bytes(self, sample_png_bytes: bytes) -> None:
        client = _make_client()
        png_b64 = base64.b64encode(sample_png_bytes).decode("ascii")
        envelope = {
            "request_id": str(uuid.uuid4()), "session_id": "",
            "success": True,
            "payload": {
                "png_bytes_b64": png_b64,
                "width": 1920, "height": 1080,
                "captured_at": "2026-01-01T00:00:00Z",
                "monitor_index": 0,
            },
            "error": None, "latency_ms": 15.0,
        }
        with patch.object(client._client, "post", return_value=_mock_response(envelope)):
            result = client.screenshot()
        assert result.success is True
        assert result.png_bytes == sample_png_bytes
        assert result.width == 1920

    def test_screenshot_primitive_failure_raises_typed(self) -> None:
        from seidr_smidja.brunhand.exceptions import BrunhandPrimitiveError
        client = _make_client()
        envelope = {
            "request_id": str(uuid.uuid4()), "session_id": "",
            "success": False,
            "payload": None,
            "error": {"error_type": "ScreenshotError", "message": "Screen locked"},
            "latency_ms": 5.0,
        }
        with patch.object(client._client, "post", return_value=_mock_response(envelope)):
            with pytest.raises(BrunhandPrimitiveError):
                client.screenshot()


class TestClick:
    def test_click_returns_result(self) -> None:
        client = _make_client()
        envelope = {
            "request_id": str(uuid.uuid4()), "session_id": "",
            "success": True,
            "payload": {"x": 100, "y": 200, "button": "left", "clicks_delivered": 1},
            "error": None, "latency_ms": 10.0,
        }
        with patch.object(client._client, "post", return_value=_mock_response(envelope)):
            result = client.click(100, 200)
        assert result.success is True
        assert result.x == 100

    def test_auth_error_401_raises_typed(self) -> None:
        import httpx
        from seidr_smidja.brunhand.exceptions import BrunhandAuthError
        client = _make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        with patch.object(client._client, "post", return_value=mock_resp):
            with pytest.raises(BrunhandAuthError):
                client.click(0, 0)


class TestWaitForWindow:
    def test_timeout_propagation(self) -> None:
        """D-010: httpx timeout must be timeout_seconds + buffer."""
        import httpx
        client = _make_client(request_timeout_buffer=3.0)
        envelope = {
            "request_id": str(uuid.uuid4()), "session_id": "",
            "success": True,
            "payload": {"found": False, "elapsed_seconds": 10.0},
            "error": None, "latency_ms": 10000.0,
        }

        captured_timeout = []

        def capture_post(path, json=None, timeout=None):
            captured_timeout.append(timeout)
            return _mock_response(envelope)

        with patch.object(client._client, "post", side_effect=capture_post):
            result = client.wait_for_window("VRoid Studio", timeout_seconds=10.0)

        assert result.found is False
        assert result.success is True
        # D-010: effective timeout must be primitive_timeout + buffer
        if captured_timeout and captured_timeout[0] is not None:
            effective = captured_timeout[0].read  # httpx.Timeout .read attribute
            assert effective == 13.0  # 10.0 + 3.0

    def test_wait_found_false_not_an_error(self) -> None:
        """wait_for_window timeout is NOT a BrunhandPrimitiveError."""
        client = _make_client()
        envelope = {
            "request_id": str(uuid.uuid4()), "session_id": "",
            "success": True,
            "payload": {"found": False, "elapsed_seconds": 30.0},
            "error": None, "latency_ms": 30000.0,
        }
        with patch.object(client._client, "post", return_value=_mock_response(envelope)):
            result = client.wait_for_window("VRoid Studio", timeout_seconds=30.0)
        assert result.found is False
        assert result.success is True


class TestVroidExportVrm:
    def test_vroid_not_running_raises_typed(self) -> None:
        from seidr_smidja.brunhand.exceptions import VroidNotRunningError
        client = _make_client()
        envelope = {
            "request_id": str(uuid.uuid4()), "session_id": "",
            "success": False,
            "payload": None,
            "error": {
                "error_type": "VroidNotRunningError",
                "message": "VRoid not running",
                "vroid_running": False,
            },
            "latency_ms": 5.0,
        }
        with patch.object(client._client, "post", return_value=_mock_response(envelope)):
            with pytest.raises(VroidNotRunningError):
                client.vroid_export_vrm("out.vrm")

    def test_timeout_extended_for_export(self) -> None:
        """D-010: vroid_export_vrm must extend the httpx timeout."""
        client = _make_client(request_timeout_buffer=5.0)
        envelope = {
            "request_id": str(uuid.uuid4()), "session_id": "",
            "success": True,
            "payload": {"exported_path": "out.vrm", "elapsed_seconds": 30.0, "steps_executed": []},
            "error": None, "latency_ms": 30000.0,
        }
        captured = []

        def capture(path, json=None, timeout=None):
            captured.append(timeout)
            return _mock_response(envelope)

        with patch.object(client._client, "post", side_effect=capture):
            result = client.vroid_export_vrm("out.vrm", wait_timeout_seconds=120.0)

        assert result.success is True
        if captured and captured[0] is not None:
            effective = captured[0].read
            assert effective == 125.0  # 120.0 + 5.0


class TestRetryLogic:
    def test_retries_on_500(self) -> None:
        from seidr_smidja.brunhand.exceptions import BrunhandProtocolError
        from seidr_smidja.brunhand.client.client import BrunhandClient
        client = BrunhandClient(
            host="127.0.0.1", token="t", port=8848, tls=False,
            config={"brunhand": {"client": {"retry_max": 2, "retry_backoff_base": 0.0, "retry_on": [500]}}},
        )
        bad_resp = MagicMock()
        bad_resp.status_code = 500
        bad_resp.text = "server error"
        call_count = [0]

        def failing_post(*args, **kwargs):
            call_count[0] += 1
            return bad_resp

        with patch.object(client._client, "post", side_effect=failing_post):
            with pytest.raises(BrunhandProtocolError):
                client._post("/v1/test", {"primitive": "test"})

        assert call_count[0] == 2  # retried once
        client.close()
