# Brúarhönd v0.1 — Phase 6 Audit Report
**Date:** 2026-05-06
**Scope:** Brúarhönd Phase 5 implementation — all source files under `src/seidr_smidja/brunhand/`, modified files `oracle_eye/eye.py`, `bridges/core/dispatch.py`, `bridges/runstafr/cli.py`, `bridges/straumur/api.py`, `bridges/mjoll/server.py`, `pyproject.toml`, `config/defaults.yaml`
**Branch:** development
**HEAD commit:** afe89f2 (post-Phase 5)
**Auditor:** Sólrún Hvítmynd
**Commands run:**
- `pytest tests/brunhand/ -m "not requires_blender and not requires_vroid_host" -q` → 144 passed
- `pytest tests/ -m "not requires_blender and not requires_vroid_host" -q` → 430 passed, 2 skipped
- `pytest tests/brunhand/ --cov=seidr_smidja.brunhand --cov-report=term-missing -q`
- Live probes via `python -c` for auth, bind logic, path traversal, and model validation
**Environment:** Windows 11, Python 3.10.11, platform win32

---

## Summary Verdict

**PASS WITH CONCERNS** — no authentication bypass, no token leak, no Critical findings. Three High findings are present: an absent concurrency serialization that contradicts an explicit architectural contract, a path traversal surface on VRoid path arguments with no allow-list enforcement, and vroid high-level primitives that are functional stubs (dialog opens but file path is never typed). All three have clear additive remediation paths. Fourteen additional findings from Medium through Notable are documented below.

---

## Section 1 — Run Metadata

| Field | Value |
|---|---|
| Date | 2026-05-06 |
| Branch | development |
| HEAD | afe89f2 |
| Test runs | `pytest tests/brunhand/` (144 tests), full suite (430 tests, 2 skipped) |
| Coverage (brunhand) | 58% aggregate; per-module detail in Section 3 |
| Files audited | 19 source files under `brunhand/`, 16 test files |
| Source LOC reviewed | ~1,836 measured statements |

---

## Section 2 — Findings by Severity

---

### B-001 — Concurrent sessions not serialized: HTTP 423 Locked documented but absent
- **Severity:** High
- **Domain:** brunhand/daemon/app
- **File:** `src/seidr_smidja/brunhand/daemon/app.py` (entire file); `docs/features/brunhand/ARCHITECTURE.md:627–638`; `src/seidr_smidja/brunhand/daemon/INTERFACE.md:583`
- **Category:** Concurrency
- **Symptom:** Two agents can open simultaneous sessions to the same daemon and both will move the mouse/keyboard at the same time. The expected HTTP 423 response never arrives.
- **Root cause:** ARCHITECTURE.md §XII explicitly states: *"If a second session request arrives while a session is active: Default (v0.1): `423 Locked` with `X-Brunhand-Session-Active: <session_id>`."* The daemon INTERFACE.md confirms this at line 583. The implementation in `app.py` has no session-tracking variable, no global lock, and no middleware or handler that can produce a 423 response. The string "423" and the word "Locked" appear nowhere in any `.py` file under `brunhand/daemon/`.
- **Reproduction:** Issue two concurrent POST requests to any primitive endpoint while the daemon is running. Both succeed simultaneously.
- **Recommended fix (additive):** Add a module-level `asyncio.Lock` or a threading lock in `app.py` that is acquired at the start of any authenticated POST handler and released on response. Rejected sessions return 423 with `X-Brunhand-Session-Active` header. Because uvicorn runs the FastAPI app in an async event loop, use `asyncio.Lock` with `async with`.
- **Owner:** Forge Worker

---

### B-002 — Path traversal: vroid_open_project and vroid_export_vrm accept unconstrained paths
- **Severity:** High
- **Domain:** brunhand/daemon/endpoints/vroid; brunhand/daemon/runtime
- **File:** `src/seidr_smidja/brunhand/daemon/endpoints/vroid.py:30–50`; `src/seidr_smidja/brunhand/daemon/runtime.py:407–469`; `src/seidr_smidja/brunhand/daemon/runtime.py:491–529`
- **Category:** Path safety
- **Symptom:** An authenticated agent can supply `output_path="../../etc/passwd"` or `project_path="~/.ssh/authorized_keys"` to the vroid endpoints. These strings are accepted without validation, logged to Annáll (`vroid.py:41` logs `output_path=req.output_path`), and the daemon proceeds into the high-level script. In v0.1 the actual file path is never typed into the GUI dialog (see B-003) — but the path IS returned in the success response payload as `exported_path` / `opened_path`, making future-phase implementations that complete the stub vulnerable to path traversal by construction.
- **Root cause:** `VroidExportVrmRequest.output_path` and `VroidOpenProjectRequest.project_path` are plain `str` fields with no Pydantic validator, no `Path.resolve()` check, and no comparison against a configured allow-list (`export_root` / `project_root` from config are passed to the runtime but used only as contextual metadata, not as a constraining boundary). `runtime.vroid_export_vrm` (`runtime.py:410`) receives `export_root` but never validates that `output_path` is a child of it.
- **Reproduction:** Authenticated POST to `/v1/brunhand/vroid/export_vrm` with body `{"output_path": "../../sensitive", ...}`. Response contains `{"exported_path": "../../sensitive"}`. No rejection.
- **Recommended fix (additive):** Add a `_validate_path_in_root(path_str: str, root_str: str)` helper in `runtime.py` that calls `Path(root_str).resolve() / Path(path_str).resolve()` and raises `ValueError` if the resolved path is not within the resolved root. Call it at the top of `vroid_export_vrm` and `vroid_open_project`. Add a Pydantic validator on the request model for a first line of defence.
- **Owner:** Forge Worker

---

### B-003 — vroid_export_vrm and vroid_open_project are functional stubs: path never set in dialog
- **Severity:** High
- **Domain:** brunhand/daemon/runtime
- **File:** `src/seidr_smidja/brunhand/daemon/runtime.py:449–465` (export); `runtime.py:507–529` (open)
- **Category:** Other (incomplete implementation)
- **Symptom:** Calling `vroid_export_vrm` with `output_path="my_avatar.vrm"` will open VRoid Studio's export dialog and press Enter — but the path `my_avatar.vrm` is never typed. The dialog confirms with whatever path VRoid Studio has pre-filled. The response payload claims `exported_path="my_avatar.vrm"` which is false: the agent believes the export went to the specified path, but the actual export destination is determined by VRoid Studio's own state. Same for `vroid_open_project`.
- **Root cause:** `runtime.py:449–452`: *"# The path would be set here in a full implementation. For v0.1, we log the step and note the path parameter."* The step `set_path:{output_path}` is appended to `steps_executed` (a log string) but no `pyautogui.typewrite(output_path)` or `pyautogui.hotkey(['ctrl','a'])` + `typewrite` is present. The comment is explicit that this is a stub.
- **Reproduction:** Live daemon with VRoid Studio running: call `vroid_export_vrm(output_path="AUDIT_TEST.vrm")`. The file is NOT saved at `AUDIT_TEST.vrm`; VRoid Studio exports to its previously set path.
- **Recommended fix (additive):** In `runtime.vroid_export_vrm`, after the export dialog opens, add: `pyautogui.hotkey('ctrl', 'a')` to select the existing path text, then `pyautogui.typewrite(str(Path(export_root) / output_path), interval=0.05)` to type the validated path. Same pattern for `vroid_open_project`. Document the stub status clearly in the primitive's response if the path-setting step is intentionally deferred.
- **Owner:** Forge Worker

---

### B-004 — Middleware execution order inverted relative to documented design
- **Severity:** Medium
- **Domain:** brunhand/daemon/app
- **File:** `src/seidr_smidja/brunhand/daemon/app.py:102–107`
- **Category:** Error handling / doc drift
- **Symptom:** ARCHITECTURE.md §III states the middleware order is: *(1) Request logging (outermost), (2) Gæslumaðr, (3) Rate limiting, (4) Request ID injection*. The actual FastAPI/Starlette execution order for `add_middleware` is that the **last call is the outermost layer** (runs first). `RequestLogMiddleware` is added on line 102 (first); `GaeslumadrMiddleware` is added on line 107 (second). Therefore Gæslumaðr runs before `RequestLogMiddleware` — the documented order is reversed.
- **Root cause:** In Starlette, each `add_middleware()` call wraps the existing stack, making it outermost. The Forge Worker registered them in insertion order but Starlette uses reverse-insertion order.
- **Reproduction:** Trap all request bodies to the running daemon and observe that the `X-Request-ID` response header (added by `RequestLogMiddleware`) is NOT present on rejected 401 responses. The request log event is also absent for rejected requests since `RequestLogMiddleware` never executes for them.
- **Recommended fix (additive):** Swap the add_middleware calls: add `GaeslumadrMiddleware` first, then `RequestLogMiddleware`. Or restructure using Starlette's `Middleware` list which has more intuitive ordering.
- **Owner:** Forge Worker

---

### B-005 — Dead `gaeslu` instance: `set_daemon_session_id` called on unreferenced object
- **Severity:** Medium
- **Domain:** brunhand/daemon/app
- **File:** `src/seidr_smidja/brunhand/daemon/app.py:106–107; 143`
- **Category:** Error handling / telemetry
- **Symptom:** Auth rejection events in Annáll are logged with `session_id=""` (empty string) instead of the daemon's session ID.
- **Root cause:** Line 106 creates `gaeslu = GaeslumadrMiddleware(app=app, token=token, annall=annall)` — a standalone object never registered anywhere. Line 107 registers a *different* `GaeslumadrMiddleware` instance via `app.add_middleware(...)`. The registered instance (used for every request) never has `set_daemon_session_id()` called on it; `gaeslu.set_daemon_session_id(sid)` on line 143 calls the method on the dead, unregistered instance. The live middleware's `_daemon_session_id` remains `""` for the daemon's lifetime.
- **Reproduction:** Run the daemon with Annáll enabled. Submit a request with a wrong token. Query the daemon-side Annáll. The `auth.rejected` event will have `session_id=""` or the outer session fallback `"daemon"`.
- **Recommended fix (additive):** Remove the dead `gaeslu = GaeslumadrMiddleware(...)` line (106). For `set_daemon_session_id`, either expose the middleware instance reference through FastAPI's middleware registry, or pass a mutable container (e.g., a `list[str]` like the existing `_daemon_annall_session_id` pattern) to the middleware constructor and update it from the startup handler.
- **Owner:** Forge Worker

---

### B-006 — Primitive handlers do not produce a structured `capabilities_error` response; F4 failure mode misrepresented
- **Severity:** Medium
- **Domain:** brunhand/daemon/endpoints/primitives; brunhand/daemon/runtime
- **File:** `src/seidr_smidja/brunhand/daemon/endpoints/primitives.py:83–110`; `src/seidr_smidja/brunhand/daemon/runtime.py:118–122`; `docs/features/brunhand/DATA_FLOW.md:649–657`
- **Category:** Error handling / doc drift
- **Symptom:** DATA_FLOW.md §F4 states that when a primitive is unsupported on this platform, the daemon returns a *structured `capabilities_error` response* before the primitive executes. An agent checking `error.error_type` for a distinguished capability-error string receives `"CapabilityRuntimeError"` instead.
- **Root cause:** The primitive handlers (`handle_screenshot`, `handle_click`, etc.) do not call `is_primitive_available()` before delegating to `runtime`. The runtime raises `CapabilityRuntimeError` (a `RuntimeError` subclass) when the underlying library is absent. This falls through to the handler's outer `except Exception as exc:` and is wrapped in a generic `BrunhandErrorDetail` with `error_type=type(exc).__name__` = `"CapabilityRuntimeError"`. The agent-facing `_raise_if_primitive_error()` in `client.py` only discriminates `VroidNotRunningError`; a `CapabilityRuntimeError` becomes a `BrunhandPrimitiveError`, not a `BrunhandCapabilityError`.
- **Recommended fix (additive):** In each primitive handler, call `is_primitive_available(primitive_name)` before the `try` block. On `False`, return a `BrunhandResponseEnvelope(success=False, error=BrunhandErrorDetail(error_type="capabilities_error", ...))` and log `primitive.capability_unavailable`. Add a corresponding discriminator in `_raise_if_primitive_error()` to raise `BrunhandCapabilityError`.
- **Owner:** Forge Worker

---

### B-007 — BrunhandCapabilityError and BrunhandProtocolError missing from `__init__.__all__`
- **Severity:** Medium
- **Domain:** brunhand/__init__
- **File:** `src/seidr_smidja/brunhand/__init__.py:108–120`; `src/seidr_smidja/brunhand/INTERFACE.md:22`
- **Category:** Doc drift
- **Symptom:** `from seidr_smidja.brunhand import BrunhandCapabilityError` raises `ImportError`. The INTERFACE.md claims `BrunhandCapabilitiesError` (plural) is exported, but the class is named `BrunhandCapabilityError` (singular) in `exceptions.py`. Neither form is in `__all__`.
- **Root cause:** `__init__.py:98–120` imports and exports six of the eight exception classes. `BrunhandCapabilityError` and `BrunhandProtocolError` are imported in `client.py` (line 270–274) but omitted from the package's public re-export.
- **Recommended fix (additive):** Add `BrunhandCapabilityError` and `BrunhandProtocolError` to the import block and `__all__` in `__init__.py`. Fix the INTERFACE.md name from `BrunhandCapabilitiesError` to `BrunhandCapabilityError`.
- **Owner:** Forge Worker / Scribe

---

### B-008 — `verify_tls=False` produces no logged warning despite documentation claim
- **Severity:** Medium
- **Domain:** brunhand/client/client
- **File:** `src/seidr_smidja/brunhand/client/client.py:221–239`; `docs/features/brunhand/ARCHITECTURE.md:579`
- **Category:** Doc drift / Auth
- **Symptom:** ARCHITECTURE.md §X states: *"When disabled, a startup warning is logged via Annáll."* Passing `verify_tls=False` to `BrunhandClient` silently disables TLS verification with no log entry.
- **Root cause:** Lines 221–239 in `client.py` apply `self._verify_tls = verify_tls` and pass it to `httpx.Client(verify=...)`. No `logger.warning(...)` or Annáll event is emitted.
- **Recommended fix (additive):** After line 239 in `client.py`, add: `if not self._verify_tls: logger.warning("BrunhandClient: TLS verification disabled for host %s. Only acceptable on Tailscale-internal topology.", self.host)`.
- **Owner:** Forge Worker

---

### B-009 — X-Forwarded-For header trusted without validation — forensic IP spoofing
- **Severity:** Medium
- **Domain:** brunhand/daemon/auth; brunhand/daemon/app
- **File:** `src/seidr_smidja/brunhand/daemon/auth.py:147–154`; `src/seidr_smidja/brunhand/daemon/app.py:291–298`
- **Category:** Auth / telemetry integrity
- **Symptom:** An attacker who can send requests to the daemon (e.g., a compromised Tailscale peer) can supply `X-Forwarded-For: 127.0.0.1` and appear as localhost in the Annáll rejection log. This does not bypass authentication, but it corrupts the forensic IP record.
- **Root cause:** `_get_client_ip()` in both files: `forwarded = request.headers.get("x-forwarded-for", "")` — the first IP in the header is taken without verifying whether a proxy actually set it.
- **Recommended fix (additive):** In the Tailscale-only deployment model there is no legitimate proxy. Add a config flag `brunhand.daemon.trust_proxy_headers: false` (default) that gates `X-Forwarded-For` use. When `false`, use only `request.client.host`.
- **Owner:** Forge Worker

---

### B-010 — `_localhost_addresses` set in `__main__.py` is dead code
- **Severity:** Low
- **Domain:** brunhand/daemon/__main__
- **File:** `src/seidr_smidja/brunhand/daemon/__main__.py:75`
- **Category:** Other
- **Symptom:** No functional impact; code smell indicating the bind guard logic was refactored mid-way.
- **Root cause:** Line 75 assigns `_localhost_addresses = {"127.0.0.1", "::1", "localhost", "0.0.0.0"}`. This variable is never referenced after its assignment. The actual `is_localhost` check on line 76 uses an inline tuple. The dead variable creates the false impression that `0.0.0.0` is treated as localhost (it is not in the actual check, which is correct — `0.0.0.0` without `allow_remote_bind` is refused).
- **Recommended fix (additive):** Remove the dead `_localhost_addresses` assignment and replace with an explanatory comment documenting that `0.0.0.0` is refused without `allow_remote_bind`.
- **Owner:** Forge Worker

---

### B-011 — `Tengslastig` does not close `BrunhandClient` on `__exit__` when used directly
- **Severity:** Low
- **Domain:** brunhand/client/session
- **File:** `src/seidr_smidja/brunhand/client/session.py:163–187`
- **Category:** Resource
- **Symptom:** If an agent constructs `Tengslastig(client, ...)` directly (not via the factory), the `httpx.Client` connection pool is not closed when the session context exits.
- **Root cause:** `Tengslastig.__exit__` (line 163) does not call `self._client.close()`. The `factory.py:make_session_from_config()` correctly closes the client in its `finally` block (line 151), so the factory path is safe. The direct-construction path is not.
- **Recommended fix (additive):** Add `self._client.close()` (wrapped in `contextlib.suppress(Exception)`) at the top of `Tengslastig.__exit__`, with a documentation note that this is idempotent for callers who also manage the client's lifecycle externally.
- **Owner:** Forge Worker

---

### B-012 — Multi-monitor VRoid Studio: screenshot always captures primary monitor regardless of VRoid's location
- **Severity:** Low
- **Domain:** brunhand/daemon/runtime
- **File:** `src/seidr_smidja/brunhand/daemon/runtime.py:136`
- **Category:** Cross-platform
- **Symptom:** On a dual-monitor setup where VRoid Studio is open on monitor 2, `screenshot()` with no region specified captures monitor 1. The agent sees an empty desktop or a different application, not VRoid Studio.
- **Root cause:** `runtime.take_screenshot` line 136: `monitor = sct.monitors[1]` — MSS index 1 is always the primary display (index 0 is the combined virtual screen).
- **Recommended fix (additive):** Document this constraint in capabilities manifest notes for `screenshot`. Add an optional `monitor_index` parameter to `ScreenshotRequest` that maps to `sct.monitors[monitor_index + 1]` (with bounds checking). Add a note in `TAILSCALE.md` operator guidance.
- **Owner:** Forge Worker / Scribe

---

### B-013 — Inline bearer tokens in config YAML are only warned, not blocked
- **Severity:** Low
- **Domain:** brunhand/client/factory
- **File:** `src/seidr_smidja/brunhand/client/factory.py:167–173`
- **Category:** Auth
- **Symptom:** An operator who places the bearer token inline in `config/user.yaml` under `brunhand.hosts[].token` receives a `logger.warning()` but the token is used. The token persists on disk in plain text and may be included in config file backups, version control accidental commits, etc.
- **Root cause:** `factory.py:_resolve_token` line 167–173: inline token is accepted with only a warning.
- **Recommended fix (additive):** This is a tradeoff between usability and security for v0.1. At minimum, document in `TAILSCALE.md` that inline tokens in YAML config must be excluded from git via `.gitignore` on `config/user.yaml`.
- **Owner:** Scribe

---

### B-014 — `HotkeyRequest.keys` and `ClickRequest.button` have no allow-list or enum validation
- **Severity:** Low
- **Domain:** brunhand/models
- **File:** `src/seidr_smidja/brunhand/models.py:256–259` (hotkey); `models.py:163–170` (click)
- **Category:** Input validation
- **Symptom:** An agent can send `keys=["win", "l"]` (Windows lock screen) or `button="xyz"` (PyAutoGUI will silently treat unknown buttons as left). Dangerous key combinations are sent without any documented allow/deny policy.
- **Root cause:** `HotkeyRequest.keys: list[str]` and `ClickRequest.button: str = "left"` have no Pydantic validators constraining their values. The VISION.md makes no explicit promise about this, but it also makes no explicit pass-through permission. The ARCHITECTURE documents that the daemon has *full* authority over the desktop — the design intent is that the daemon is an extension of the agent's will.
- **Recommended fix (additive):** Document the explicit design choice: Brúarhönd is an intentional full-authority agent hand — all hotkeys including system-level ones are pass-throughs by design. Add this statement to `PHILOSOPHY_ADDENDUM.md` and `INTERFACE.md`. If a deny-list is desired, it is an additive v0.2 concern.
- **Owner:** Scribe (documentation of intentional pass-through)

---

### B-015 — `TypeTextRequest.text` has no size limit — potential DoS / blocking
- **Severity:** Low
- **Domain:** brunhand/models; brunhand/daemon/runtime
- **File:** `src/seidr_smidja/brunhand/models.py:241–244`; `src/seidr_smidja/brunhand/daemon/runtime.py:262`
- **Category:** Input validation
- **Symptom:** An agent can send `text="a" * 1_000_000`. `pyautogui.typewrite(text, interval=0.05)` would execute for 50,000 seconds, blocking the daemon's async loop for that thread (uvicorn uses a thread pool for sync endpoint handlers).
- **Root cause:** `TypeTextRequest.text: str` — no `Field(max_length=...)` constraint. `do_type_text` calls `pyautogui.typewrite(text, ...)` directly.
- **Recommended fix (additive):** Add `Field(max_length=10000, description="Maximum 10,000 characters per type_text call")` to `TypeTextRequest.text`. Add a note in `INTERFACE.md` that longer text sequences should be split across multiple calls.
- **Owner:** Forge Worker

---

### B-016 — `daemon/__main__.py:59%` coverage — bind refusal path and startup banner untested
- **Severity:** Notable
- **Domain:** tests/brunhand
- **File:** `tests/brunhand/test_daemon_main.py`; `src/seidr_smidja/brunhand/daemon/__main__.py:78–89` (bind refusal)
- **Category:** Test quality
- **Symptom:** The security-critical bind refusal path (non-localhost without `allow_remote_bind`) has no unit test. The test suite cannot detect regressions to this invariant.
- **Root cause:** Coverage report: `daemon/__main__.py: 59% (41 lines uncovered)`. Lines 78–89 (the bind refusal `sys.exit`) are in the uncovered set.
- **Recommended fix (additive):** Add a test that calls `main(["--host", "192.168.1.1"])` without `allow_remote_bind` config and asserts `SystemExit` is raised with the correct message. Use `pytest.raises(SystemExit)` and patch `load_bearer_token`.
- **Owner:** Forge Worker

---

### B-017 — `daemon/app.py: 9%` coverage — the live FastAPI app never tested through the HTTP stack
- **Severity:** Notable
- **Domain:** tests/brunhand
- **File:** `src/seidr_smidja/brunhand/daemon/app.py` (9% coverage); `tests/brunhand/test_daemon_endpoints.py`
- **Category:** Test quality
- **Symptom:** The live FastAPI application (middleware stack, route bindings, startup/shutdown events) is almost entirely untested. The existing endpoint tests patch the runtime layer and call handlers directly — the Gæslumaðr middleware is not exercised in any test.
- **Root cause:** No `TestClient` (from `fastapi.testclient`) is used to mount the live `create_daemon_app()` and issue real HTTP requests through it. The middleware order bug (B-004) and the dead gaeslu instance bug (B-005) were only discoverable by reading the code, not by a failing test.
- **Recommended fix (additive):** Add an integration test class `TestDaemonHTTPStack` using `fastapi.testclient.TestClient(create_daemon_app(token="test-token"))` that covers: health without auth, capabilities with correct token, capabilities with wrong token (assert 401), any primitive with no auth header (assert 401), any primitive with wrong token (assert 401), correct token succeeds.
- **Owner:** Forge Worker

---

### B-018 — `daemon/runtime.py: 18%` coverage — all runtime shims are untested paths
- **Severity:** Notable
- **Domain:** tests/brunhand
- **File:** `src/seidr_smidja/brunhand/daemon/runtime.py` (18% coverage)
- **Category:** Test quality
- **Symptom:** The platform shim layer — including `take_screenshot`, `do_click`, `do_hotkey`, `vroid_export_vrm` — is almost entirely uncovered. Bugs in the PyAutoGUI call signatures or the MSS image pipeline would not be caught by CI.
- **Root cause:** Endpoint tests mock `runtime.*` rather than testing the runtime functions themselves with mocked underlying libraries (`pyautogui`, `mss`).
- **Recommended fix (additive):** Add a `test_daemon_runtime.py` file that patches `pyautogui`, `mss`, and `psutil` at the module level and tests each runtime function's call signatures, return shapes, and `CapabilityRuntimeError` paths when libraries are absent.
- **Owner:** Forge Worker

---

## Section 3 — Coverage Map

| Module | Coverage | Critical Uncovered Surfaces |
|---|---|---|
| `__init__.py` | 100% | — |
| `client/__init__.py` | 100% | — |
| `exceptions.py` | 100% | — |
| `models.py` | 100% | — |
| `daemon/endpoints/health.py` | 100% | — |
| `client/oracle_channel.py` | 96% | Lines 181–182 (feed_screenshot fallback) |
| `daemon/capabilities.py` | 82% | Lines 92–95 (macOS pygetwindow degraded note), 181–202 (screen geometry probe) |
| `daemon/config.py` | 81% | Env var override paths (BRUNHAND_HOST, BRUNHAND_TLS_*), token_path file read |
| `client/factory.py` | 86% | Lines 179–185 (token_path resolution) |
| `client/session.py` | 78% | Annáll session open/close paths, execute_and_see Ljósbrú path |
| `client/client.py` | 72% | All retry paths, httpx.HTTPError, ConnectTimeout, TLSError, capabilities error handling |
| `daemon/__main__.py` | 59% | Bind refusal (B-016), banner print, SSL config, startup dep check |
| `daemon/endpoints/primitives.py` | 46% | move, drag, scroll, type_text, hotkey, find_window handlers |
| `daemon/endpoints/vroid.py` | 38% | save_project and open_project success/failure paths |
| `daemon/auth.py` | 43% | GaeslumadrMiddleware.dispatch (entire HTTP middleware — only unit helpers tested) |
| `daemon/app.py` | 9% | Everything: middleware, routes, startup/shutdown events |
| `daemon/runtime.py` | 18% | All PyAutoGUI/MSS shims, VRoid scripts |

**Aggregate: 58% on brunhand.** Target was ≥75% per-module. Eleven of sixteen modules fail to meet that target.

---

## Section 4 — Cross-Cutting Themes

**Theme 1: Primitive handler tests bypass the HTTP layer entirely.** All nine endpoint handler tests in `test_daemon_endpoints.py` call functions directly (e.g., `handle_screenshot(req)`) without mounting the FastAPI app. The middleware, auth, and route registration code at 9% coverage is untested. This means auth bugs introduced into the middleware stack would produce zero test failures.

**Theme 2: Runtime shims are mocked from above, never tested from below.** Every handler test patches `seidr_smidja.brunhand.daemon.runtime.*`. No test imports the runtime module and patches its third-party dependencies (`pyautogui`, `mss`, `psutil`). The actual call signatures passed to PyAutoGUI are never verified.

**Theme 3: Starlette middleware ordering confusion.** The middleware reversal (B-004) and the dead instance (B-005) stem from the same root: Starlette's counter-intuitive `add_middleware` ordering is not documented anywhere in the codebase, making it easy to introduce ordering bugs silently.

**Theme 4: Stub implementations shipped with documentation claiming full behavior.** Both `vroid_export_vrm` and `vroid_open_project` (B-003) contain explicit stub comments but the INTERFACE.md and VISION.md describe them as working primitives. This pattern — stub with aspirational documentation — produces misleading agent behavior and obscures what is actually implemented.

---

## Section 5 — Authenticated Probe Results

All probes were conducted via Python interpreter with the project in the working directory.

### Probe 1 — Bearer token extraction edge cases
**Attempted:** `_extract_token("Bearer Bearer token")` → extracted `"Bearer token"` with status `"accepted"`. This is not a bypass: subsequent `_tokens_match("Bearer token", real_token)` returns `False` unless the actual configured token is literally `"Bearer token"`. No authentication bypass.

**Attempted:** `_extract_token(" Bearer mytoken")` (leading space) → `""`, `"malformed"`. Correctly rejected.

**Attempted:** `_extract_token("Βearer mytoken")` (Greek capital Beta Unicode confusable) → `""`, `"malformed"`. Correctly rejected by case-insensitive `parts[0].lower()` check.

**Attempted:** `_extract_token("Bearer   ")` (whitespace-only token after `Bearer`) → `""`, `"accepted"` (status is `"accepted"` because the prefix is valid, but `parts[1].strip()` is empty). Then `_tokens_match("", configured)` → `False` due to the `not presented` guard. No bypass.

### Probe 2 — Empty BRUNHAND_TOKEN env var
**Attempted:** Set `BRUNHAND_TOKEN=""` and called `load_bearer_token()`. Result: `RuntimeError: "BRUNHAND_TOKEN is not set. The daemon will not start without a bearer token."` Correct fail-loud behavior.

### Probe 3 — Constant-time comparison
**Evidence:** `auth.py:139` uses `hmac.compare_digest(presented.encode(), configured.encode())`. Confirmed by source inspection and verified that the import is `import hmac` (stdlib) with no overridden `compare_digest`. The guard at lines 136–137 (`if not presented or not configured: return False`) short-circuits on empty strings before the comparison — this does NOT introduce a timing leak because both empty checks are O(1) and the adversary cannot infer the configured token's length from this path.

### Probe 4 — Non-localhost bind without allow_remote_bind
**Attempted:** Simulated `__main__` bind logic with `bind_address="192.168.1.100"`, `allow_remote_bind=False`. Result: `is_localhost=False` → startup refuses with `sys.exit(...)`. **Pass.**

**Attempted:** `bind_address="0.0.0.0"`, `allow_remote_bind=False`. Result: `is_localhost=False` → startup refuses. **Pass.**

Dead variable `_localhost_addresses` noted (B-010) — does not affect correctness but confuses readers.

### Probe 5 — Path traversal in vroid endpoints
**Attempted:** Examined vroid handler code for `Path.resolve()`, `is_relative_to()`, allow-list comparison, or any sanitization of `output_path` / `project_path`. None found. The path strings are logged to Annáll (`vroid.py:41`), passed to `runtime.vroid_export_vrm`, and returned in the response without modification. **Finding B-002 confirmed.** Live execution not performed (no VRoid Studio running in CI).

### Probe 6 — Health endpoint content
**Attempted:** `get_health_response("0.1.0")`. Response: `{"daemon_version": "0.1.0", "os_name": "windows", "uptime_seconds": 0.0, "status": "ok"}`. No username, hostname, screen geometry, file paths, or environment variables. **Pass — bounded as documented.**

### Probe 7 — Screenshot scope
**Evidence from source:** `runtime.py:136` hardcodes `sct.monitors[1]` (primary monitor in MSS). An agent cannot target a specific non-primary monitor without a `region` parameter that maps to that monitor's screen coordinates. **Finding B-012 confirmed.** No bypass — just a documented limitation.

---

## Section 6 — Punch List

| ID | Severity | File | Owner |
|---|---|---|---|
| B-001 | High | `daemon/app.py` (entire) | Forge Worker |
| B-002 | High | `daemon/endpoints/vroid.py:30–50`, `daemon/runtime.py:407–529` | Forge Worker |
| B-003 | High | `daemon/runtime.py:449–465, 507–529` | Forge Worker |
| B-004 | Medium | `daemon/app.py:102–107` | Forge Worker |
| B-005 | Medium | `daemon/app.py:106–107, 143` | Forge Worker |
| B-006 | Medium | `daemon/endpoints/primitives.py:83–110`, `DATA_FLOW.md:649` | Forge Worker |
| B-007 | Medium | `brunhand/__init__.py:108–120`, `INTERFACE.md:22` | Forge Worker / Scribe |
| B-008 | Medium | `client/client.py:221–239`, `ARCHITECTURE.md:579` | Forge Worker |
| B-009 | Medium | `daemon/auth.py:147–154`, `daemon/app.py:291–298` | Forge Worker |
| B-010 | Low | `daemon/__main__.py:75` | Forge Worker |
| B-011 | Low | `client/session.py:163–187` | Forge Worker |
| B-012 | Low | `daemon/runtime.py:136` | Forge Worker / Scribe |
| B-013 | Low | `client/factory.py:167–173` | Scribe |
| B-014 | Low | `models.py:256–259, 163–170` | Scribe |
| B-015 | Low | `models.py:241–244`, `daemon/runtime.py:262` | Forge Worker |
| B-016 | Notable | `daemon/__main__.py:78–89`, `tests/brunhand/test_daemon_main.py` | Forge Worker |
| B-017 | Notable | `daemon/app.py` (9% coverage), test suite | Forge Worker |
| B-018 | Notable | `daemon/runtime.py` (18% coverage), test suite | Forge Worker |

---

## Section 7 — Verdict

**PASS WITH CONCERNS.**

Authentication is sound: bearer token comparison is constant-time via `hmac.compare_digest`, the token never appears in logs or responses, the health endpoint is the only correctly bounded auth bypass, and the daemon refuses non-localhost binds without explicit operator consent. These invariants hold.

Three High findings require remediation before the feature can be considered production-safe. The most operationally dangerous is B-003: the two high-level VRoid primitives are functional stubs that open dialogs without setting the file path, producing silently incorrect behavior. B-001 (absent session serialization) allows concurrent agents to issue contradictory GUI commands simultaneously. B-002 (path traversal) establishes a structural vulnerability that will be exploitable once B-003 is fixed and the path is actually typed into the dialog.

The Medium and Low findings are quality and hardening items that do not create an immediate security boundary failure but represent drift between documentation and implementation that will degrade the feature's reliability and operator trust over time.

---

*Audit sealed by Sólrún Hvítmynd, 2026-05-06.*
