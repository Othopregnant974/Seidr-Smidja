"""Tests for seidr_smidja.brunhand.daemon.__main__ — CLI entry point and safety checks."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


class TestNonLocalhostRefusal:
    def test_refuses_non_localhost_without_allow_remote(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-localhost binding without allow_remote_bind must exit with error."""
        monkeypatch.setenv("BRUNHAND_TOKEN", "test-token")

        from seidr_smidja.brunhand.daemon.__main__ import main

        # Patch at source module level since these are imported inside main()
        with patch("seidr_smidja.brunhand.daemon.__main__._check_daemon_deps"), \
             patch("seidr_smidja.brunhand.daemon.config.load_daemon_config", return_value={
                 "bind_address": "192.168.1.100",  # non-localhost
                 "port": 8848,
                 "allow_remote_bind": False,  # not set
                 "tls": {},
             }), \
             patch("seidr_smidja.brunhand.daemon.config.load_bearer_token", return_value="test-token"):
            with pytest.raises(SystemExit) as exc_info:
                main([])
        assert exc_info.value.code != 0 or isinstance(exc_info.value.code, str)

    def test_allows_localhost_binding(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Localhost binding must be allowed without allow_remote_bind."""
        monkeypatch.setenv("BRUNHAND_TOKEN", "test-token")

        from seidr_smidja.brunhand.daemon.__main__ import main

        with patch("seidr_smidja.brunhand.daemon.__main__._check_daemon_deps"), \
             patch("seidr_smidja.brunhand.daemon.config.load_daemon_config", return_value={
                 "bind_address": "127.0.0.1",
                 "port": 8848,
                 "allow_remote_bind": False,
                 "tls": {},
             }), \
             patch("seidr_smidja.brunhand.daemon.config.load_bearer_token", return_value="test-token"), \
             patch("seidr_smidja.brunhand.daemon.app.create_daemon_app", return_value=MagicMock()), \
             patch("seidr_smidja.brunhand.daemon.__main__._print_banner"), \
             patch("uvicorn.run") as mock_uvicorn:
            main([])
        mock_uvicorn.assert_called_once()

    def test_allows_non_localhost_with_allow_remote(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-localhost with allow_remote_bind=True must be allowed."""
        monkeypatch.setenv("BRUNHAND_TOKEN", "test-token")

        from seidr_smidja.brunhand.daemon.__main__ import main

        with patch("seidr_smidja.brunhand.daemon.__main__._check_daemon_deps"), \
             patch("seidr_smidja.brunhand.daemon.config.load_daemon_config", return_value={
                 "bind_address": "100.64.0.1",
                 "port": 8848,
                 "allow_remote_bind": True,  # explicitly enabled
                 "tls": {},
             }), \
             patch("seidr_smidja.brunhand.daemon.config.load_bearer_token", return_value="test-token"), \
             patch("seidr_smidja.brunhand.daemon.app.create_daemon_app", return_value=MagicMock()), \
             patch("seidr_smidja.brunhand.daemon.__main__._print_banner"), \
             patch("uvicorn.run") as mock_uvicorn:
            main([])
        mock_uvicorn.assert_called_once()


class TestMissingToken:
    def test_missing_token_exits_loudly(self) -> None:
        """Missing bearer token must cause a loud failure, not a silent skip."""
        from seidr_smidja.brunhand.daemon.__main__ import main

        with patch("seidr_smidja.brunhand.daemon.__main__._check_daemon_deps"), \
             patch("seidr_smidja.brunhand.daemon.config.load_daemon_config", return_value={
                 "bind_address": "127.0.0.1", "port": 8848, "allow_remote_bind": False, "tls": {},
             }), \
             patch("seidr_smidja.brunhand.daemon.config.load_bearer_token",
                   side_effect=RuntimeError("BRUNHAND_TOKEN must be set")):
            with pytest.raises(SystemExit):
                main([])


class TestCliArgOverride:
    def test_host_arg_overrides_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BRUNHAND_TOKEN", "tok")

        from seidr_smidja.brunhand.daemon.__main__ import main

        with patch("seidr_smidja.brunhand.daemon.__main__._check_daemon_deps"), \
             patch("seidr_smidja.brunhand.daemon.config.load_daemon_config", return_value={
                 "bind_address": "127.0.0.1", "port": 8848, "allow_remote_bind": False, "tls": {},
             }), \
             patch("seidr_smidja.brunhand.daemon.config.load_bearer_token", return_value="tok"), \
             patch("seidr_smidja.brunhand.daemon.app.create_daemon_app", return_value=MagicMock()), \
             patch("seidr_smidja.brunhand.daemon.__main__._print_banner"), \
             patch("uvicorn.run"):
            main(["--host", "127.0.0.1", "--port", "9999"])
