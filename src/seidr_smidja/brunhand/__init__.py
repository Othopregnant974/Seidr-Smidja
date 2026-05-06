"""
Brúarhönd — the Bridge-Hand.

The forge's reaching arm across the Tailscale wire: a bearer-authenticated daemon and
client pair that lets an AI agent operate a live VRoid Studio session on a remote machine
through precise GUI primitives, returning screenshots through the Oracle Eye.

Sub-modules:
    brunhand.client      — Hengilherðir, the Reaching Client (forge-side)
    brunhand.daemon      — Horfunarþjónn, the Watching-Daemon (VRoid host-side)
    brunhand.models      — Shared pydantic envelope models
    brunhand.exceptions  — BrunhandError exception hierarchy

Primary entry points:
    brunhand.session(host, token, ...)   -> ContextManager[Tengslastig]
    brunhand.brunhand_dispatch(request, annall) -> BrunhandDispatchResponse

See: src/seidr_smidja/brunhand/INTERFACE.md
See: docs/features/brunhand/ARCHITECTURE.md
"""
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any


@contextmanager
def session(
    host: str,
    token: str,
    port: int = 8848,
    tls: bool = True,
    timeout: float | None = None,
    agent_id: str = "",
    oracle_eye: Any = None,
    annall: Any = None,
    run_id: str | None = None,
    output_dir: Any = None,
    verify_tls: bool | str = True,
    request_timeout_buffer: float = 5.0,
) -> Iterator[Any]:
    """Open a Tengslastig session to a Horfunarþjónn daemon.

    Convenience entry point — builds the client, opens the session,
    yields the Tengslastig, and closes everything on exit.

    Usage:
        with brunhand.session("vroid-host.ts.net", token=os.environ["BRUNHAND_TOKEN"]) as sess:
            result = sess.screenshot()
            sess.hotkey(["ctrl", "s"])

    Args:
        host:                  Daemon hostname or IP.
        token:                 Bearer token (from env or config).
        port:                  Daemon port (default 8848).
        tls:                   Use HTTPS (auto-false for localhost).
        timeout:               Base request timeout seconds (default 30.0).
        agent_id:              Agent identity string for Annáll events.
        oracle_eye:            Optional oracle_eye module for Ljósbrú integration.
        annall:                Optional AnnallPort for telemetry.
        run_id:                Optional Mode C run_id for cross-Annáll correlation.
        output_dir:            Optional dir for Oracle Eye render output.
        verify_tls:            TLS certificate verification (bool or path).
        request_timeout_buffer: Seconds added to primitive_timeout for httpx timeout.

    Yields:
        A Tengslastig session context.
    """
    from seidr_smidja.brunhand.client.client import BrunhandClient
    from seidr_smidja.brunhand.client.session import Tengslastig

    client = BrunhandClient(
        host=host,
        token=token,
        port=port,
        tls=tls,
        timeout=timeout,
        verify_tls=verify_tls,
        request_timeout_buffer=request_timeout_buffer,
    )
    try:
        sess = Tengslastig(
            client=client,
            agent_id=agent_id,
            oracle_eye=oracle_eye,
            annall=annall,
            run_id=run_id,
            output_dir=output_dir,
        )
        with sess:
            yield sess
    finally:
        client.close()


# Re-export key types at package level
from seidr_smidja.brunhand.client.client import BrunhandClient  # noqa: E402
from seidr_smidja.brunhand.client.session import BrunhandSession, Tengslastig  # noqa: E402
from seidr_smidja.brunhand.exceptions import (  # noqa: E402
    BrunhandAuthError,
    BrunhandConfigError,
    BrunhandConnectionError,
    BrunhandError,
    BrunhandPrimitiveError,
    BrunhandTimeoutError,
    VroidNotRunningError,
)

__all__ = [
    "session",
    "BrunhandClient",
    "Tengslastig",
    "BrunhandSession",
    "BrunhandError",
    "BrunhandAuthError",
    "BrunhandConfigError",
    "BrunhandConnectionError",
    "BrunhandPrimitiveError",
    "BrunhandTimeoutError",
    "VroidNotRunningError",
]
