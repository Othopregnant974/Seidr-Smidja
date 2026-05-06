"""Tests for seidr_smidja.brunhand.client.oracle_channel — Ljósbrú."""
from __future__ import annotations

import base64
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


class TestLjosbruFeed:
    def test_returns_none_when_oracle_not_configured(self, sample_png_bytes: bytes) -> None:
        from seidr_smidja.brunhand.client.oracle_channel import Ljosbrú
        bridge = Ljosbrú(oracle_eye_module=None)
        result = bridge.feed(sample_png_bytes)
        assert result is None

    def test_returns_result_when_oracle_configured(self, sample_png_bytes: bytes) -> None:
        from seidr_smidja.brunhand.client.oracle_channel import Ljosbrú, LjosbruResult

        mock_oracle = MagicMock()
        mock_register_result = MagicMock()
        mock_register_result.view_name = "live/test-session/20260101_120000"
        mock_register_result.view_path = None
        mock_oracle.register_external_render.return_value = mock_register_result

        with patch("seidr_smidja.oracle_eye.eye.ExternalRenderMetadata", MagicMock()):
            bridge = Ljosbrú(oracle_eye_module=mock_oracle, host="test-host")
            result = bridge.feed(sample_png_bytes, session_id="test-session")

        assert result is not None
        assert isinstance(result, LjosbruResult)
        assert result.oracle_available is True
        assert result.byte_count == len(sample_png_bytes)

    def test_never_raises_on_oracle_failure(self, sample_png_bytes: bytes) -> None:
        from seidr_smidja.brunhand.client.oracle_channel import Ljosbrú

        mock_oracle = MagicMock()
        mock_oracle.register_external_render.side_effect = RuntimeError("Oracle broken")

        bridge = Ljosbrú(oracle_eye_module=mock_oracle)
        # Should NOT raise
        result = bridge.feed(sample_png_bytes)
        # Returns a result with oracle_available=False
        assert result is not None
        assert result.oracle_available is False

    def test_view_name_pattern(self, sample_png_bytes: bytes) -> None:
        from seidr_smidja.brunhand.client.oracle_channel import Ljosbrú

        mock_oracle = MagicMock()
        mock_register_result = MagicMock()
        # The view name should follow "live/<session_id>/<timestamp>" pattern
        mock_register_result.view_name = "live/abc123/20260101_120000"
        mock_register_result.view_path = None
        mock_oracle.register_external_render.return_value = mock_register_result

        with patch("seidr_smidja.oracle_eye.eye.ExternalRenderMetadata", MagicMock()):
            bridge = Ljosbrú(oracle_eye_module=mock_oracle)
            result = bridge.feed(sample_png_bytes, session_id="abc123")

        call_kwargs = mock_oracle.register_external_render.call_args[1]
        view = call_kwargs.get("view", "")
        assert view.startswith("live/abc123/")

    def test_bytes_never_logged(self, sample_png_bytes: bytes) -> None:
        """INVARIANT: raw PNG bytes must NOT appear in Annáll events."""
        from seidr_smidja.brunhand.client.oracle_channel import Ljosbrú

        mock_oracle = MagicMock()
        mock_register_result = MagicMock()
        mock_register_result.view_name = "live/s/t"
        mock_register_result.view_path = None
        mock_oracle.register_external_render.return_value = mock_register_result

        logged_events = []

        class CapturingAnnall:
            def log_event(self, session_id, event):
                logged_events.append(event)

        with patch("seidr_smidja.oracle_eye.eye.ExternalRenderMetadata", MagicMock()):
            bridge = Ljosbrú(
                oracle_eye_module=mock_oracle,
                annall=CapturingAnnall(),
                annall_session_id="sess-123",
            )
            bridge.feed(sample_png_bytes, session_id="s")

        # PNG bytes must NOT appear in any logged event payload
        png_b64 = base64.b64encode(sample_png_bytes).decode("ascii")
        for event in logged_events:
            payload_str = str(getattr(event, "payload", {}))
            assert sample_png_bytes not in payload_str.encode("ascii", errors="ignore")
            assert png_b64 not in payload_str


class TestLjosbruResult:
    def test_fields(self) -> None:
        from seidr_smidja.brunhand.client.oracle_channel import LjosbruResult
        result = LjosbruResult(
            view_name="live/s/t",
            view_path=None,
            byte_count=1024,
            oracle_available=True,
        )
        assert result.view_name == "live/s/t"
        assert result.byte_count == 1024
        assert result.oracle_available is True


class TestFeedScreenshot:
    def test_calls_register(self, sample_png_bytes: bytes) -> None:
        from seidr_smidja.brunhand.client.oracle_channel import feed_screenshot

        mock_oracle = MagicMock()
        mock_oracle.register_external_render.return_value = MagicMock()
        feed_screenshot(
            oracle_eye=mock_oracle,
            source="brunhand",
            view="live/test/ts",
            png_bytes=sample_png_bytes,
            metadata=MagicMock(),
        )
        mock_oracle.register_external_render.assert_called_once()

    def test_returns_none_on_oracle_failure(self, sample_png_bytes: bytes) -> None:
        from seidr_smidja.brunhand.client.oracle_channel import feed_screenshot

        mock_oracle = MagicMock()
        mock_oracle.register_external_render.side_effect = RuntimeError("broken")
        result = feed_screenshot(
            oracle_eye=mock_oracle,
            source="brunhand",
            view="v",
            png_bytes=sample_png_bytes,
            metadata=MagicMock(),
        )
        assert result is None
