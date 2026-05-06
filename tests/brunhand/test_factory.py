"""Tests for seidr_smidja.brunhand.client.factory — make_client_from_config."""
from __future__ import annotations

import os
from typing import Any

import pytest


def _cfg_with_host(host: str = "127.0.0.1", token: str = "test-token") -> dict[str, Any]:
    return {
        "brunhand": {
            "hosts": [
                {
                    "name": "test-host",
                    "host": host,
                    "port": 8848,
                    "tls": False,
                    "token": token,
                }
            ],
            "client": {
                "timeout_seconds": 10.0,
                "request_timeout_buffer": 2.0,
                "retry_max": 1,
            },
        }
    }


class TestMakeClientFromConfig:
    def test_returns_client(self) -> None:
        from seidr_smidja.brunhand.client.client import BrunhandClient
        from seidr_smidja.brunhand.client.factory import make_client_from_config

        config = _cfg_with_host()
        client = make_client_from_config("test-host", config)
        assert isinstance(client, BrunhandClient)
        client.close()

    def test_host_not_found_raises_config_error(self) -> None:
        from seidr_smidja.brunhand.client.factory import make_client_from_config
        from seidr_smidja.brunhand.exceptions import BrunhandConfigError

        with pytest.raises(BrunhandConfigError, match="nonexistent"):
            make_client_from_config("nonexistent", _cfg_with_host())

    def test_token_override_used(self) -> None:
        from seidr_smidja.brunhand.client.factory import make_client_from_config

        config = _cfg_with_host(token="original-token")
        client = make_client_from_config("test-host", config, token_override="override-token")
        # Token is private but we can confirm the client was built
        assert client is not None
        client.close()

    def test_empty_hosts_raises_config_error(self) -> None:
        from seidr_smidja.brunhand.client.factory import make_client_from_config
        from seidr_smidja.brunhand.exceptions import BrunhandConfigError

        config = {"brunhand": {"hosts": []}}
        with pytest.raises(BrunhandConfigError):
            make_client_from_config("test-host", config)

    def test_resolves_token_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from seidr_smidja.brunhand.client.factory import make_client_from_config

        monkeypatch.setenv("BRUNHAND_TOKEN", "env-token")
        # Config with no inline token
        config = {
            "brunhand": {
                "hosts": [{"name": "test-host", "host": "127.0.0.1", "port": 8848, "tls": False}],
                "client": {"timeout_seconds": 10.0},
            }
        }
        client = make_client_from_config("test-host", config)
        assert client is not None
        client.close()

    def test_missing_token_raises_config_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from seidr_smidja.brunhand.client.factory import make_client_from_config
        from seidr_smidja.brunhand.exceptions import BrunhandConfigError

        monkeypatch.delenv("BRUNHAND_TOKEN", raising=False)
        monkeypatch.delenv("BRUNHAND_TOKEN_TEST_HOST", raising=False)
        config = {
            "brunhand": {
                "hosts": [{"name": "test-host", "host": "127.0.0.1", "port": 8848, "tls": False}],
            }
        }
        with pytest.raises(BrunhandConfigError, match="token"):
            make_client_from_config("test-host", config)


class TestMakeSessionFromConfig:
    def test_context_manager_yields_tengslastig(self) -> None:
        from seidr_smidja.brunhand.client.factory import make_session_from_config
        from seidr_smidja.brunhand.client.session import Tengslastig

        config = _cfg_with_host()
        with make_session_from_config("test-host", config) as session:
            assert isinstance(session, Tengslastig)
            assert session.session_id != ""

    def test_closes_client_on_exit(self) -> None:
        from seidr_smidja.brunhand.client.factory import make_client_from_config, make_session_from_config
        from unittest.mock import patch, MagicMock

        config = _cfg_with_host()
        mock_client = MagicMock()

        with patch("seidr_smidja.brunhand.client.factory.make_client_from_config", return_value=mock_client):
            with make_session_from_config("test-host", config):
                pass

        mock_client.close.assert_called_once()
