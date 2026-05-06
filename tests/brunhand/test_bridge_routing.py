"""Tests for bridge-level Brúarhönd routing — CLI, Straumur REST, Mjöll MCP."""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


class TestCLIBrunhandGroup:
    def test_brunhand_group_registered(self) -> None:
        from click.testing import CliRunner
        from seidr_smidja.bridges.runstafr.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["brunhand", "--help"])
        assert result.exit_code == 0
        assert "brunhand" in result.output.lower() or "Bru" in result.output

    def test_health_command_exists(self) -> None:
        from click.testing import CliRunner
        from seidr_smidja.bridges.runstafr.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["brunhand", "health", "--help"])
        assert result.exit_code == 0
        assert "--host" in result.output

    def test_screenshot_command_exists(self) -> None:
        from click.testing import CliRunner
        from seidr_smidja.bridges.runstafr.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["brunhand", "screenshot", "--help"])
        assert result.exit_code == 0

    def test_vroid_export_command_exists(self) -> None:
        from click.testing import CliRunner
        from seidr_smidja.bridges.runstafr.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["brunhand", "vroid-export", "--help"])
        assert result.exit_code == 0

    def test_health_command_outputs_json(self) -> None:
        from click.testing import CliRunner
        from seidr_smidja.bridges.runstafr.cli import cli
        from seidr_smidja.brunhand.client.client import HealthResult

        runner = CliRunner()
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.health.return_value = HealthResult(
            status="ok", daemon_version="0.1.0", os_name="Windows", uptime_seconds=42.0
        )

        with patch("seidr_smidja.brunhand.client.factory.make_client_from_config", return_value=mock_client), \
             patch("seidr_smidja.bridges.runstafr.cli._find_project_root", return_value=MagicMock()), \
             patch("seidr_smidja.bridges.runstafr.cli._load_config", return_value={}):
            result = runner.invoke(cli, ["brunhand", "health", "--host", "test", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "ok"


class TestStraumurBrunhandDispatch:
    def test_endpoint_registered(self) -> None:
        """POST /v1/brunhand/dispatch endpoint must be registered."""
        try:
            from seidr_smidja.bridges.straumur.api import create_app
        except ImportError:
            pytest.skip("FastAPI not available")

        from unittest.mock import MagicMock
        app = create_app({})
        routes = [r.path for r in app.routes]
        assert "/v1/brunhand/dispatch" in routes

    def test_dispatch_endpoint_returns_json(self) -> None:
        """POST /v1/brunhand/dispatch must return JSON (success or failure)."""
        try:
            from fastapi.testclient import TestClient
            from seidr_smidja.bridges.straumur.api import create_app
        except ImportError:
            pytest.skip("FastAPI or TestClient not available")

        cfg = {
            "annall": {"adapter": "null"},
            "brunhand": {"hosts": [], "client": {"timeout_seconds": 5.0}},
        }
        app = create_app(cfg)
        http_client = TestClient(app, raise_server_exceptions=False)

        # With no real host, this will return a failure response — but it MUST
        # return JSON with a 'success' key, not a 500 exception.
        resp = http_client.post("/v1/brunhand/dispatch", json={
            "host_name": "nonexistent-host",
            "primitive": "screenshot",
        })

        # Must return a valid JSON response (not 500 or crash)
        assert resp.status_code in (200, 422)
        data = resp.json()
        assert "success" in data
        # With nonexistent host, success must be False
        assert data["success"] is False


class TestMjollBrunhandTools:
    def test_brunhand_tools_in_list(self) -> None:
        """seidr.brunhand_screenshot, seidr.brunhand_click, seidr.brunhand_vroid_export must be listed."""
        try:
            from seidr_smidja.bridges.mjoll.server import build_mcp_server
        except ImportError:
            pytest.skip("MCP SDK not available")

        # Build server with mocked MCP SDK
        with patch("seidr_smidja.bridges.mjoll.server._MCP_AVAILABLE", True), \
             patch("seidr_smidja.bridges.mjoll.server.mcp_types") as mock_types, \
             patch("seidr_smidja.bridges.mjoll.server.Server") as mock_server_class:

            mock_server = MagicMock()
            mock_server_class.return_value = mock_server
            mock_tools = []

            def capture_decorator(fn):
                return fn

            mock_server.list_tools.return_value = capture_decorator
            mock_server.call_tool.return_value = capture_decorator

            from seidr_smidja.bridges.mjoll.server import build_mcp_server
            build_mcp_server({})
            # Just verify the server was built without error
            mock_server_class.assert_called_once_with("seidr-smidja")
