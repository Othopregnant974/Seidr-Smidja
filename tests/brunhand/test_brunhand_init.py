"""Tests for seidr_smidja.brunhand.__init__ — top-level package API."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestBrunhandSession:
    def test_session_factory_yields_tengslastig(self) -> None:
        from seidr_smidja.brunhand.client.session import Tengslastig
        import seidr_smidja.brunhand as brunhand

        mock_client = MagicMock()
        with patch("seidr_smidja.brunhand.client.client.BrunhandClient", return_value=mock_client):
            with brunhand.session(
                host="127.0.0.1", token="test-token", tls=False
            ) as sess:
                assert isinstance(sess, Tengslastig)

    def test_session_closes_client_on_exit(self) -> None:
        import seidr_smidja.brunhand as brunhand

        mock_client = MagicMock()
        # brunhand.session() uses BrunhandClient from seidr_smidja.brunhand.client.client
        with patch("seidr_smidja.brunhand.client.client.BrunhandClient", return_value=mock_client):
            with brunhand.session(host="127.0.0.1", token="t", tls=False):
                pass
        mock_client.close.assert_called_once()

    def test_exports_key_exceptions(self) -> None:
        import seidr_smidja.brunhand as brunhand
        assert hasattr(brunhand, "BrunhandError")
        assert hasattr(brunhand, "VroidNotRunningError")
        assert hasattr(brunhand, "BrunhandConnectionError")
        assert hasattr(brunhand, "BrunhandAuthError")
        assert hasattr(brunhand, "BrunhandTimeoutError")

    def test_exports_client_and_session(self) -> None:
        import seidr_smidja.brunhand as brunhand
        assert hasattr(brunhand, "BrunhandClient")
        assert hasattr(brunhand, "Tengslastig")
        assert hasattr(brunhand, "BrunhandSession")
