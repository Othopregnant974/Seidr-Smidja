"""Tests for seidr_smidja.brunhand.daemon.config — load_daemon_config, load_bearer_token."""
from __future__ import annotations

import os

import pytest


class TestLoadDaemonConfig:
    def test_returns_defaults_with_no_extra(self) -> None:
        from seidr_smidja.brunhand.daemon.config import load_daemon_config
        cfg = load_daemon_config({})
        assert "bind_address" in cfg
        assert "port" in cfg
        assert isinstance(cfg["port"], int)

    def test_extra_config_overrides_bind_address(self) -> None:
        from seidr_smidja.brunhand.daemon.config import load_daemon_config
        # extra_config follows the full config structure brunhand.daemon.*
        cfg = load_daemon_config({"brunhand": {"daemon": {"bind_address": "0.0.0.0"}}})
        assert cfg["bind_address"] == "0.0.0.0"

    def test_default_bind_address_is_localhost(self) -> None:
        from seidr_smidja.brunhand.daemon.config import load_daemon_config
        cfg = load_daemon_config({})
        assert cfg.get("bind_address") == "127.0.0.1"

    def test_allow_remote_bind_defaults_false(self) -> None:
        from seidr_smidja.brunhand.daemon.config import load_daemon_config
        cfg = load_daemon_config({})
        assert cfg.get("allow_remote_bind") is False

    def test_env_var_overrides_port(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BRUNHAND_PORT", "9999")
        from seidr_smidja.brunhand.daemon.config import load_daemon_config
        cfg = load_daemon_config({})
        assert cfg.get("port") == 9999

    def test_env_var_overrides_bind_address(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BRUNHAND_HOST", "192.168.1.100")
        from seidr_smidja.brunhand.daemon.config import load_daemon_config
        cfg = load_daemon_config({})
        assert cfg.get("bind_address") == "192.168.1.100"


class TestLoadBearerToken:
    def test_reads_from_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BRUNHAND_TOKEN", "my-secret-token")
        from seidr_smidja.brunhand.daemon.config import load_bearer_token
        token = load_bearer_token()
        assert token == "my-secret-token"

    def test_raises_if_no_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("BRUNHAND_TOKEN", raising=False)
        from seidr_smidja.brunhand.daemon.config import load_bearer_token
        with pytest.raises(RuntimeError, match="BRUNHAND_TOKEN"):
            load_bearer_token()

    def test_reads_from_token_path_via_config(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        """load_bearer_token reads token_path from brunhand.daemon.token_path in config."""
        monkeypatch.delenv("BRUNHAND_TOKEN", raising=False)
        token_file = tmp_path / "token.txt"
        token_file.write_text("file-token-value\n", encoding="utf-8")

        # Patch the config loading to return our token_path
        mock_cfg = {
            "brunhand": {
                "daemon": {"token_path": str(token_file)}
            }
        }
        with __import__("unittest.mock", fromlist=["patch"]).patch(
            "seidr_smidja.config.load_config", return_value=mock_cfg
        ), __import__("unittest.mock", fromlist=["patch"]).patch(
            "seidr_smidja.config._find_config_root", return_value=tmp_path
        ):
            from seidr_smidja.brunhand.daemon.config import load_bearer_token
            token = load_bearer_token()
        assert token == "file-token-value"
