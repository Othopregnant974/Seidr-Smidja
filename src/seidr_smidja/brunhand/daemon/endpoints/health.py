"""Horfunarþjónn — GET /v1/brunhand/health endpoint.

No authentication required. Returns daemon liveness, version, OS name, and uptime.
Does NOT return desktop access, capability details, or mutable state.

This is the only endpoint that bypasses Gæslumaðr — a documented, bounded exception.
See: docs/features/brunhand/ARCHITECTURE.md §III Middleware Order
"""
from __future__ import annotations

import time
from typing import Any

_DAEMON_START_TIME = time.monotonic()


def get_health_response(daemon_version: str = "0.1.0") -> dict[str, Any]:
    """Build the health response dict.

    Returns:
        Dict matching HealthResponse schema.
    """
    import sys

    os_map = {"win32": "windows", "darwin": "darwin"}
    os_name = os_map.get(sys.platform, "linux")
    uptime = time.monotonic() - _DAEMON_START_TIME

    return {
        "daemon_version": daemon_version,
        "os_name": os_name,
        "uptime_seconds": round(uptime, 2),
        "status": "ok",
    }
