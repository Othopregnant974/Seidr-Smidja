# Brúarhönd — Top-Level Domain Interface Contract
**Last updated:** 2026-05-06
**Domain:** Brúarhönd — the Bridge-Hand
**Module:** `src/seidr_smidja/brunhand/`
**Keeper:** Rúnhild Svartdóttir (Architect)

---

## Purpose

Brúarhönd is the forge's reaching arm across the Tailscale wire — a bearer-authenticated daemon and client pair that lets an AI agent operate a live VRoid Studio session on a remote machine through precise GUI primitives, returning screenshots through the Oracle Eye so the agent always sees what its hand has done.

---

## Public Sub-Modules and Their Roles

| Sub-module | True Name | Location | Role |
|---|---|---|---|
| `brunhand.client` | Hengilherðir — the Reaching Client | `client/` | Forge-side library; `BrunhandClient`, `Tengslastig`, `Ljósbrú` |
| `brunhand.daemon` | Horfunarþjónn — the Watching-Daemon | `daemon/` | HTTP server on VRoid host; run with `python -m seidr_smidja.brunhand.daemon` |
| `brunhand.models` | — | `models.py` | Shared pydantic models: `BrunhandRequest`, `BrunhandResponse`, `PrimitiveCall`, `PrimitiveResult`, `CapabilitiesManifest`, `BrunhandEnvelope`, `BrunhandResponseEnvelope` |
| `brunhand.exceptions` | — | `exceptions.py` | Exception hierarchy: `BrunhandError`, `BrunhandConnectionError`, `BrunhandAuthError`, `BrunhandTimeoutError`, `BrunhandCapabilitiesError`, `BrunhandPrimitiveError`, `VroidNotRunningError`, `BrunhandProtocolError` |

---

## Top-Level Public API

### `brunhand.session(host, token, timeout, run_id, annall, oracle_eye_module)`

Returns a `Tengslastig` context manager for sequential primitive execution against one VRoid host.

```python
with brunhand.session(
    host="vroid-host.tailnet.ts.net",
    run_id=build_response.annall_session_id,   # optional — cross-correlate with dispatch()
    annall=annall_port,
) as sess:
    result = sess.execute_and_see(sess.click, x=412, y=288)
```

Full signature and behavior: see `client/INTERFACE.md`.

### `brunhand.brunhand_dispatch(request, annall, config)`

The parallel dispatch function called by Bridge Core when a `BrunhandRequest` is present. Returns a `BrunhandResponse`. Never propagates unhandled exceptions to Bridge callers.

This function is the entry point used by Bridge sub-modules (Mjöll, Rúnstafr, Straumur, Skills). Direct calls from outside the Bridges layer are not part of the supported contract.

---

## Optional Dependency Model

| Install target | What it provides | Who needs it |
|---|---|---|
| `seidr-smidja` (base) | Client-side only (`httpx`) | Agent running the forge |
| `seidr-smidja[brunhand-daemon]` | `pyautogui`, `mss`, `pygetwindow` | Operator running daemon on VRoid host |
| `seidr-smidja[brunhand-win]` | `pywinauto` (Windows accessibility) | VRoid host on Windows |
| `seidr-smidja[brunhand-mac]` | `pyobjc-framework-Quartz` (macOS accessibility) | VRoid host on macOS |
| `seidr-smidja[brunhand-linux]` | `pyatspi` (Linux AT-SPI accessibility) | VRoid host on Linux |

The daemon will raise `ImportError` with a clear install instruction if its required GUI libs are absent. The client never requires GUI libs.

---

## Placement in the Dependency Graph

Brúarhönd is a **lateral** domain — it does not sit in the Loom→Hoard→Forge→Oracle Eye→Gate pipeline. It sits beside Bridge Core at Layer 3, invoked by the same Bridge sub-modules that call `bridges.core.dispatch()`.

```
Bridges → brunhand_dispatch() → Hengilherðir → [network] → Horfunarþjónn
                                      ↓
                              oracle_eye.register_external_render()
                                      ↓
                                   Annáll
```

**What Brúarhönd may call:**
- `oracle_eye.register_external_render()` (for vision integration via Ljósbrú)
- `annall.log_event()` / `annall.open_session()` / `annall.close_session()` (for telemetry)
- `seidr_smidja.config` (for token and host resolution)

**What Brúarhönd must never call:**
- `bridges.core.dispatch()` (circular — Brúarhönd is called by bridges, not the other way)
- `loom`, `hoard`, `forge`, `gate` (these are Blender-pipeline domains; no dependency)
- `oracle_eye.render()` (that is the Blender render path; Brúarhönd uses `register_external_render()` only)

---

## Invariants

1. Every primitive execution requires a valid bearer token — no exceptions, no configuration to disable.
2. The daemon process never crashes due to a primitive failure — all primitive handlers are wrapped in `try/except`.
3. Screenshot bytes always flow through Ljósbrú to Oracle Eye before being returned to the Bridge. Raw PNG bytes are never returned directly to Bridge callers.
4. Bearer tokens never appear in logs, traces, Annáll events, or response bodies.
5. The daemon binds to `127.0.0.1` by default — network exposure requires explicit operator configuration.
6. All configuration values (token, host, port, TLS paths) are loaded from env vars or YAML — never hardcoded.

---

## Cross-References

- `docs/features/brunhand/ARCHITECTURE.md` — full structural decomposition
- `docs/features/brunhand/VISION.md` — feature soul and Primary Rite
- `docs/features/brunhand/PHILOSOPHY_ADDENDUM.md` — sacred principles VI–IX
- `src/seidr_smidja/brunhand/daemon/INTERFACE.md` — daemon HTTP API contract
- `src/seidr_smidja/brunhand/client/INTERFACE.md` — client Python API contract
- `src/seidr_smidja/oracle_eye/INTERFACE.md` — the Oracle Eye contract extended by Ljósbrú

---

*Rúnhild Svartdóttir, Architect — 2026-05-06*
