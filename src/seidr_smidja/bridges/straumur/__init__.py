"""
Straumur — the REST Bridge.

The HTTP API bridge, implemented with FastAPI. Exposes REST endpoints that
receive build requests as JSON, construct BuildRequest objects, call
bridges.core.dispatch(), and return BuildResponse as JSON.

No forge logic lives here. Straumur is a door, not the forge.
"""
