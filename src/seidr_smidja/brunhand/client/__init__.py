"""
Hengilherðir — the Reaching Client.

The forge-side client library for Brúarhönd. Manages HTTP connections to remote
Horfunarþjónn instances, handles session state, retries, and routes screenshots
through Ljósbrú to the Oracle Eye.

Primary public API:
    BrunhandClient(host, token, ...)  — low-level, one method per primitive
    Tengslastig                       — session context manager (via brunhand.session())
    BrunhandSession                   — alias for Tengslastig
    Ljósbrú (oracle_channel.py)       — PNG bytes → Oracle Eye adapter
    make_client_from_config()         — factory from config + host name
    make_session_from_config()        — context manager factory from config + host name

No GUI dependencies. Requires only: httpx, pydantic.

See: src/seidr_smidja/brunhand/client/INTERFACE.md
See: docs/features/brunhand/ARCHITECTURE.md §IV
"""
from seidr_smidja.brunhand.client.client import BrunhandClient
from seidr_smidja.brunhand.client.factory import make_client_from_config, make_session_from_config
from seidr_smidja.brunhand.client.oracle_channel import LjosbruResult, Ljosbrú, feed_screenshot
from seidr_smidja.brunhand.client.session import (
    BrunhandSession,
    CommandRecord,
    ExecuteAndSeeResult,
    Tengslastig,
)

__all__ = [
    "BrunhandClient",
    "Tengslastig",
    "BrunhandSession",
    "CommandRecord",
    "ExecuteAndSeeResult",
    "LjosbruResult",
    "Ljosbrú",
    "feed_screenshot",
    "make_client_from_config",
    "make_session_from_config",
]
