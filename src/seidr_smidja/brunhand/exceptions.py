"""seidr_smidja.brunhand.exceptions — Brúarhönd exception hierarchy.

All Brúarhönd client exceptions are typed subclasses of BrunhandError.
No bare httpx or network exceptions propagate beyond Hengilherðir (BrunhandClient).

Every exception carries enough context for an agent to decide on a recovery path:
  - host           — which Tailscale host was the target
  - primitive      — which primitive was being called
  - request_id     — UUID for Annáll correlation
  - session_id     — Tengslastig session UUID for Annáll correlation
  - message        — human-readable description

INVARIANT: Bearer tokens are NEVER included in any exception string, repr, or attribute.

See: src/seidr_smidja/brunhand/client/INTERFACE.md §Exception Class Hierarchy
See: docs/features/brunhand/ARCHITECTURE.md §XI Failure Model
"""
from __future__ import annotations


class BrunhandError(Exception):
    """Base class for all Brúarhönd exceptions.

    Every subclass carries host, primitive, request_id, session_id, and message
    so an agent can correlate the failure back to its Annáll records.
    """

    def __init__(
        self,
        message: str,
        host: str = "",
        primitive: str = "",
        request_id: str = "",
        session_id: str = "",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.host = host
        self.primitive = primitive
        self.request_id = request_id
        self.session_id = session_id

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"host={self.host!r}, primitive={self.primitive!r}, "
            f"request_id={self.request_id!r}, message={self.message!r})"
        )


class BrunhandConfigError(BrunhandError):
    """Configuration is malformed or missing a required value.

    Raised before any network call is attempted.
    """


class BrunhandAuthError(BrunhandError):
    """Bearer token was rejected by the daemon (HTTP 401 or 403).

    Retrying with the same token will not succeed.
    Recovery: rotate the BRUNHAND_TOKEN and restart the daemon.
    """


class BrunhandConnectionError(BrunhandError):
    """Daemon is unreachable — Tailscale partition, daemon not running, or TLS failure.

    Attributes:
        cause: One of 'dns', 'connect', 'tls', 'read', 'write', 'unknown'.
               Helps the agent decide whether to wait for connectivity (Tailscale)
               or ask an operator to restart the daemon.
    """

    def __init__(
        self,
        message: str,
        cause: str = "unknown",
        host: str = "",
        primitive: str = "",
        request_id: str = "",
        session_id: str = "",
    ) -> None:
        super().__init__(
            message,
            host=host,
            primitive=primitive,
            request_id=request_id,
            session_id=session_id,
        )
        self.cause = cause

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"cause={self.cause!r}, host={self.host!r}, "
            f"primitive={self.primitive!r}, message={self.message!r})"
        )


class BrunhandPrimitiveError(BrunhandError):
    """The daemon executed the primitive but it raised an OS-level error.

    The daemon process is still alive; the primitive failed.
    The agent may issue screenshot() to re-establish visual ground truth.

    Attributes:
        vroid_running:      Whether VRoid Studio was detected on the daemon host.
        screen_accessible:  Whether the desktop screen was accessible.
        permission_denied:  Whether the failure was a permission/accessibility error.
        stack_summary:      Truncated daemon-side traceback for diagnosis.
    """

    def __init__(
        self,
        message: str,
        vroid_running: bool = True,
        screen_accessible: bool = True,
        permission_denied: bool = False,
        stack_summary: str | None = None,
        host: str = "",
        primitive: str = "",
        request_id: str = "",
        session_id: str = "",
    ) -> None:
        super().__init__(
            message,
            host=host,
            primitive=primitive,
            request_id=request_id,
            session_id=session_id,
        )
        self.vroid_running = vroid_running
        self.screen_accessible = screen_accessible
        self.permission_denied = permission_denied
        self.stack_summary = stack_summary


class BrunhandCapabilityError(BrunhandError):
    """The requested primitive is not supported on the daemon's platform.

    Raised locally by Tengslastig (from the cached CapabilitiesManifest)
    before any network round-trip is made.

    Attributes:
        primitive_name:       The primitive that was requested.
        platform:             The daemon's OS platform ('windows', 'linux', 'darwin').
        available_primitives: List of primitive names that ARE available.
    """

    def __init__(
        self,
        message: str,
        primitive_name: str = "",
        platform: str = "",
        available_primitives: list[str] | None = None,
        host: str = "",
        request_id: str = "",
        session_id: str = "",
    ) -> None:
        super().__init__(
            message,
            host=host,
            primitive=primitive_name,
            request_id=request_id,
            session_id=session_id,
        )
        self.primitive_name = primitive_name
        self.platform = platform
        self.available_primitives = available_primitives or []


class BrunhandTimeoutError(BrunhandError):
    """The request or primitive exceeded the configured timeout.

    Distinct from wait_for_window(found=False) — this is an HTTP-level timeout,
    meaning the connection to the daemon timed out before a response was received.
    """


class VroidNotRunningError(BrunhandPrimitiveError):
    """VRoid Studio process was not detected on the daemon host.

    Raised when the daemon's psutil scan finds no VRoid Studio process,
    or when the VRoid Studio window cannot be located for a high-level primitive.

    Recovery pattern (from DATA_FLOW.md §F5):
        1. Issue wait_for_window(title_pattern="VRoid Studio", timeout_seconds=60)
        2. Or issue find_window(title_pattern="VRoid") to confirm state.
        3. Retry the original primitive once VRoid Studio is detected.
    """

    def __init__(
        self,
        message: str = "VRoid Studio is not running on the daemon host.",
        host: str = "",
        primitive: str = "",
        request_id: str = "",
        session_id: str = "",
        stack_summary: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            vroid_running=False,
            screen_accessible=True,
            permission_denied=False,
            stack_summary=stack_summary,
            host=host,
            primitive=primitive,
            request_id=request_id,
            session_id=session_id,
        )


class BrunhandProtocolError(BrunhandError):
    """Response shape did not match the expected schema.

    Indicates a version mismatch between the client and daemon, or an
    unexpected response format that Pydantic cannot parse.

    Attributes:
        raw_status_code:   HTTP status code received.
        raw_body_preview:  First 200 characters of the raw response body.
    """

    def __init__(
        self,
        message: str,
        raw_status_code: int = 0,
        raw_body_preview: str = "",
        host: str = "",
        primitive: str = "",
        request_id: str = "",
        session_id: str = "",
    ) -> None:
        super().__init__(
            message,
            host=host,
            primitive=primitive,
            request_id=request_id,
            session_id=session_id,
        )
        self.raw_status_code = raw_status_code
        self.raw_body_preview = raw_body_preview
