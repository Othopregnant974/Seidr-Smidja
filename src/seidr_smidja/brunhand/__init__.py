"""
Brúarhönd — the Bridge-Hand.

The forge's reaching arm across the Tailscale wire: a bearer-authenticated daemon and
client pair that lets an AI agent operate a live VRoid Studio session on a remote machine
through precise GUI primitives, returning screenshots through the Oracle Eye.

Sub-modules:
    brunhand.client  — Hengilherðir, the Reaching Client (forge-side)
    brunhand.daemon  — Horfunarþjónn, the Watching-Daemon (VRoid host-side)
    brunhand.models  — Shared pydantic envelope models
    brunhand.exceptions — BrunhandError exception hierarchy

Primary entry point:
    brunhand.session(host, ...) -> ContextManager[Tengslastig]

See: src/seidr_smidja/brunhand/INTERFACE.md
See: docs/features/brunhand/ARCHITECTURE.md
"""
