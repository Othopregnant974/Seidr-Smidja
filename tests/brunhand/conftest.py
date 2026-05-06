"""Shared fixtures for the Brúarhönd test suite."""
from __future__ import annotations

import base64
import io
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def null_annall():
    """NullAnnallAdapter for tests that don't need telemetry."""
    from seidr_smidja.annall.adapters.null import NullAnnallAdapter
    return NullAnnallAdapter()


@pytest.fixture
def sample_token() -> str:
    """A sample bearer token for testing."""
    return "test-bearer-token-abc123"


@pytest.fixture
def sample_session_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def sample_png_bytes() -> bytes:
    """Minimal 1x1 white PNG for testing."""
    # 1x1 white PNG — valid but minimal
    png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
        "z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=="
    )
    return base64.b64decode(png_b64)


@pytest.fixture
def minimal_daemon_config() -> dict[str, Any]:
    """Minimal daemon configuration dict."""
    return {
        "bind_address": "127.0.0.1",
        "port": 8848,
        "allow_remote_bind": False,
        "export_root": "exports",
        "project_root": "projects",
        "tls": {"enabled": False},
        "primitive_defaults": {
            "click_move_duration": 0.1,
            "type_interval": 0.05,
        },
    }


@pytest.fixture
def minimal_brunhand_config(sample_token: str) -> dict[str, Any]:
    """Minimal brunhand config with one named host."""
    return {
        "brunhand": {
            "hosts": [
                {
                    "name": "test-host",
                    "host": "127.0.0.1",
                    "port": 8848,
                    "tls": False,
                    "token": sample_token,
                }
            ],
            "daemon": {
                "bind_address": "127.0.0.1",
                "port": 8848,
                "allow_remote_bind": False,
            },
            "client": {
                "timeout_seconds": 30.0,
                "request_timeout_buffer": 5.0,
                "retry_max": 1,
            },
        }
    }


@pytest.fixture
def mock_response_envelope() -> dict[str, Any]:
    """A minimal successful BrunhandResponseEnvelope dict."""
    return {
        "request_id": str(uuid.uuid4()),
        "session_id": "",
        "success": True,
        "payload": {},
        "error": None,
        "latency_ms": 10.0,
    }
