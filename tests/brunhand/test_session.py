"""Tests for seidr_smidja.brunhand.client.session — Tengslastig."""
from __future__ import annotations

import base64
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


def _make_mock_client(host: str = "127.0.0.1") -> MagicMock:
    """Create a mock BrunhandClient."""
    client = MagicMock()
    client.host = host
    return client


class TestTengslastigContextManager:
    def test_session_id_set_on_enter(self) -> None:
        from seidr_smidja.brunhand.client.session import Tengslastig
        client = _make_mock_client()
        with Tengslastig(client=client) as session:
            assert session.session_id != ""
            uuid.UUID(session.session_id)  # validates UUID

    def test_fresh_session_id_each_enter(self) -> None:
        from seidr_smidja.brunhand.client.session import Tengslastig
        client = _make_mock_client()
        ids = set()
        for _ in range(3):
            with Tengslastig(client=client) as session:
                ids.add(session.session_id)
        assert len(ids) == 3

    def test_exits_cleanly_without_annall(self) -> None:
        from seidr_smidja.brunhand.client.session import Tengslastig
        client = _make_mock_client()
        with Tengslastig(client=client):
            pass  # no exceptions

    def test_exits_cleanly_on_exception(self) -> None:
        from seidr_smidja.brunhand.client.session import Tengslastig
        client = _make_mock_client()
        with pytest.raises(ValueError):
            with Tengslastig(client=client):
                raise ValueError("test error")

    def test_client_property(self) -> None:
        from seidr_smidja.brunhand.client.session import Tengslastig
        client = _make_mock_client()
        with Tengslastig(client=client) as session:
            assert session.client is client


class TestTengslastigPrimitiveWrappers:
    def test_screenshot_injects_session_id(self) -> None:
        from seidr_smidja.brunhand.client.session import Tengslastig
        client = _make_mock_client()
        client.screenshot.return_value = MagicMock(success=True, png_bytes=b"", width=1920, height=1080, captured_at="")
        with Tengslastig(client=client) as session:
            result = session.screenshot()
        # Verify session_id was injected
        call_kwargs = client.screenshot.call_args[1]
        assert call_kwargs.get("session_id") == session.session_id

    def test_click_records_in_command_log(self) -> None:
        from seidr_smidja.brunhand.client.session import Tengslastig
        client = _make_mock_client()
        client.click.return_value = MagicMock(success=True)
        with Tengslastig(client=client) as session:
            session.click(100, 200)
            log = session.command_log
        assert len(log) == 1
        assert log[0].primitive == "click"
        assert log[0].success is True

    def test_failed_primitive_records_error_type(self) -> None:
        from seidr_smidja.brunhand.client.session import Tengslastig
        from seidr_smidja.brunhand.exceptions import BrunhandPrimitiveError
        client = _make_mock_client()
        client.click.side_effect = BrunhandPrimitiveError("screen locked")
        with Tengslastig(client=client) as session:
            with pytest.raises(BrunhandPrimitiveError):
                session.click(0, 0)
            log = session.command_log
        assert log[0].error_type == "BrunhandPrimitiveError"

    def test_command_log_rolling_limit(self) -> None:
        from seidr_smidja.brunhand.client.session import Tengslastig
        client = _make_mock_client()
        client.click.return_value = MagicMock(success=True)
        with Tengslastig(client=client, command_log_size=5) as session:
            for _ in range(10):
                session.click(0, 0)
            log = session.command_log
        assert len(log) == 5  # rolling maxlen=5


class TestExecuteAndSee:
    def test_returns_execute_and_see_result(self) -> None:
        from seidr_smidja.brunhand.client.session import ExecuteAndSeeResult, Tengslastig
        client = _make_mock_client()
        client.click.return_value = MagicMock(success=True)
        client.screenshot.return_value = MagicMock(
            success=True, png_bytes=b"fake_png", width=1920, height=1080, captured_at=""
        )
        with Tengslastig(client=client) as session:
            result = session.execute_and_see(client.click, x=100, y=200)
        assert isinstance(result, ExecuteAndSeeResult)
        assert result.primitive_success is True

    def test_screenshot_failure_does_not_propagate(self) -> None:
        from seidr_smidja.brunhand.client.session import Tengslastig
        from seidr_smidja.brunhand.exceptions import BrunhandConnectionError
        client = _make_mock_client()
        client.click.return_value = MagicMock(success=True)
        client.screenshot.side_effect = BrunhandConnectionError("lost connection")
        with Tengslastig(client=client) as session:
            # Should NOT raise
            result = session.execute_and_see(client.click, x=0, y=0)
        assert result.primitive_success is True
        assert result.screenshot_result is None

    def test_oracle_fed_when_ljosbrú_available(self, sample_png_bytes: bytes) -> None:
        from seidr_smidja.brunhand.client.session import Tengslastig
        mock_oracle = MagicMock()
        mock_oracle_result = MagicMock()
        mock_oracle_result.view_name = "live/test/12345"
        mock_oracle_result.byte_count = len(sample_png_bytes)
        mock_oracle.register_external_render.return_value = mock_oracle_result

        client = _make_mock_client()
        client.click.return_value = MagicMock(success=True)
        client.screenshot.return_value = MagicMock(
            success=True, png_bytes=sample_png_bytes, width=1, height=1, captured_at=""
        )

        with patch("seidr_smidja.brunhand.client.oracle_channel.Ljosbrú.feed") as mock_feed:
            from seidr_smidja.brunhand.client.oracle_channel import LjosbruResult
            mock_feed.return_value = LjosbruResult(
                view_name="live/test/12345", view_path=None,
                byte_count=len(sample_png_bytes), oracle_available=True,
            )
            with Tengslastig(client=client, oracle_eye=mock_oracle) as session:
                result = session.execute_and_see(client.click, x=0, y=0)

        assert result.oracle_fed is True


class TestBrunhandSession:
    def test_alias_works(self) -> None:
        from seidr_smidja.brunhand.client.session import BrunhandSession, Tengslastig
        assert BrunhandSession is Tengslastig
