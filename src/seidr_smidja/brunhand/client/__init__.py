"""
Hengilherðir — the Reaching Client.

The forge-side client library for Brúarhönd. Manages HTTP connections to remote
Horfunarþjónn instances, handles session state, retries, and routes screenshots
through Ljósbrú to the Oracle Eye.

Primary public API:
    BrunhandClient(host, token, ...)  — low-level, one method per primitive
    Tengslastig                       — session context manager (via brunhand.session())
    Ljósbrú (oracle_channel.py)       — PNG bytes → Oracle Eye adapter

No GUI dependencies. Requires only: httpx, pydantic.

See: src/seidr_smidja/brunhand/client/INTERFACE.md
See: docs/features/brunhand/ARCHITECTURE.md §IV
"""
