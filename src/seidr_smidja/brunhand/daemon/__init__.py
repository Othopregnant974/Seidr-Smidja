"""
Horfunarþjónn — the Watching-Daemon.

The FastAPI HTTP server that runs on the VRoid Studio host machine. It receives
bearer-authenticated primitive commands, executes them on the live desktop, and returns
structured responses.

Invocation:
    python -m seidr_smidja.brunhand.daemon

Default bind: 127.0.0.1:8848
Authentication: Bearer token via Gæslumaðr middleware
Capabilities: Sjálfsmöguleiki capabilities registry

Sub-modules:
    daemon.auth          — Gæslumaðr, bearer-token middleware
    daemon.capabilities  — Sjálfsmöguleiki, platform capabilities registry
    daemon.platform      — Platform-conditional import isolation
    daemon.handlers      — Primitive endpoint handlers
    daemon.scripts       — VRoid-specific high-level scripts (vroid_export_vrm, etc.)

See: src/seidr_smidja/brunhand/daemon/INTERFACE.md
See: docs/features/brunhand/ARCHITECTURE.md §III
"""
