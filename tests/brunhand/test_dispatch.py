"""Tests for brunhand_dispatch() in bridges/core/dispatch.py."""
from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


def _make_request(
    primitive: str = "screenshot",
    host_name: str = "test-host",
    primitive_args: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
    token_override: str = "test-token",
) -> Any:
    from seidr_smidja.bridges.core.dispatch import BrunhandDispatchRequest
    cfg = config or {
        "brunhand": {
            "hosts": [{"name": "test-host", "host": "127.0.0.1", "port": 8848, "tls": False, "token": "test-token"}],
            "client": {"timeout_seconds": 5.0, "request_timeout_buffer": 1.0, "retry_max": 1},
        }
    }
    return BrunhandDispatchRequest(
        host_name=host_name,
        primitive=primitive,
        primitive_args=primitive_args or {},
        agent_id="test",
        config=cfg,
        token_override=token_override,
    )


class TestBrunhandDispatchRequest:
    def test_defaults(self) -> None:
        from seidr_smidja.bridges.core.dispatch import BrunhandDispatchRequest
        req = BrunhandDispatchRequest(host_name="h", primitive="click")
        assert req.primitive_args == {}
        assert req.run_id is None
        uuid.UUID(req.request_id)

    def test_unique_request_ids(self) -> None:
        from seidr_smidja.bridges.core.dispatch import BrunhandDispatchRequest
        r1 = BrunhandDispatchRequest(host_name="h", primitive="click")
        r2 = BrunhandDispatchRequest(host_name="h", primitive="click")
        assert r1.request_id != r2.request_id


class TestBrunhandDispatchResponse:
    def test_success_response(self) -> None:
        from seidr_smidja.bridges.core.dispatch import BrunhandDispatchResponse
        resp = BrunhandDispatchResponse(
            request_id="abc", success=True, primitive="screenshot", result=None
        )
        assert resp.success is True
        assert resp.error_type == ""

    def test_failure_response(self) -> None:
        from seidr_smidja.bridges.core.dispatch import BrunhandDispatchResponse
        resp = BrunhandDispatchResponse(
            request_id="abc", success=False, primitive="click",
            error_type="BrunhandConnectionError", error_message="refused",
        )
        assert resp.success is False
        assert resp.error_type == "BrunhandConnectionError"


class TestBrunhandDispatch:
    def test_always_returns_response(self, null_annall: Any) -> None:
        """brunhand_dispatch() NEVER propagates exceptions."""
        from seidr_smidja.bridges.core.dispatch import BrunhandDispatchResponse, brunhand_dispatch

        req = _make_request(host_name="nonexistent-host", config={})
        result = brunhand_dispatch(req, null_annall)
        assert isinstance(result, BrunhandDispatchResponse)
        assert result.success is False  # host not found

    def test_success_with_mocked_client(self, null_annall: Any) -> None:
        from seidr_smidja.bridges.core.dispatch import brunhand_dispatch
        from seidr_smidja.brunhand.client.client import ScreenshotResult

        mock_result = ScreenshotResult(success=True, png_bytes=b"png", width=1920, height=1080, captured_at="")
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.screenshot.return_value = mock_result
        mock_client.host = "127.0.0.1"

        req = _make_request(primitive="screenshot")
        with patch("seidr_smidja.brunhand.client.factory.make_client_from_config", return_value=mock_client):
            result = brunhand_dispatch(req, null_annall)

        assert result.success is True
        assert result.primitive == "screenshot"

    def test_connection_error_returns_failure(self, null_annall: Any) -> None:
        from seidr_smidja.bridges.core.dispatch import brunhand_dispatch
        from seidr_smidja.brunhand.exceptions import BrunhandConnectionError

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.screenshot.side_effect = BrunhandConnectionError("daemon unreachable")
        mock_client.host = "127.0.0.1"

        req = _make_request(primitive="screenshot")
        with patch("seidr_smidja.brunhand.client.factory.make_client_from_config", return_value=mock_client):
            result = brunhand_dispatch(req, null_annall)

        assert result.success is False
        assert "BrunhandConnectionError" in result.error_type

    def test_unknown_primitive_returns_failure(self, null_annall: Any) -> None:
        from seidr_smidja.bridges.core.dispatch import brunhand_dispatch

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.host = "127.0.0.1"

        req = _make_request(primitive="nonexistent_primitive_xyz")
        with patch("seidr_smidja.brunhand.client.factory.make_client_from_config", return_value=mock_client):
            result = brunhand_dispatch(req, null_annall)

        assert result.success is False

    def test_run_id_propagated(self, null_annall: Any) -> None:
        from seidr_smidja.bridges.core.dispatch import BrunhandDispatchRequest, brunhand_dispatch
        from seidr_smidja.brunhand.client.client import ScreenshotResult

        mock_result = ScreenshotResult(success=True, png_bytes=b"", width=1, height=1, captured_at="")
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.screenshot.return_value = mock_result
        mock_client.host = "h"

        run_id = str(uuid.uuid4())
        cfg = {
            "brunhand": {
                "hosts": [{"name": "h", "host": "127.0.0.1", "port": 8848, "tls": False, "token": "t"}],
                "client": {"timeout_seconds": 5.0, "request_timeout_buffer": 1.0, "retry_max": 1},
            }
        }
        req = BrunhandDispatchRequest(
            host_name="h", primitive="screenshot", run_id=run_id, config=cfg
        )
        with patch("seidr_smidja.brunhand.client.factory.make_client_from_config", return_value=mock_client):
            result = brunhand_dispatch(req, null_annall)

        assert result.run_id == run_id


class TestCallPrimitive:
    def test_valid_primitive_dispatched(self) -> None:
        from seidr_smidja.bridges.core.dispatch import _call_primitive
        from seidr_smidja.brunhand.client.client import ScreenshotResult

        mock_client = MagicMock()
        mock_client.screenshot.return_value = ScreenshotResult(success=True, png_bytes=b"", width=1, height=1, captured_at="")
        result = _call_primitive(mock_client, "screenshot", {})
        assert result.success is True

    def test_unknown_primitive_raises(self) -> None:
        from seidr_smidja.bridges.core.dispatch import _call_primitive
        from seidr_smidja.brunhand.exceptions import BrunhandCapabilityError

        with pytest.raises(BrunhandCapabilityError):
            _call_primitive(MagicMock(), "does_not_exist", {})
