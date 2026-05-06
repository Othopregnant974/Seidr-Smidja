# Hengilherðir — Client Python API Contract
**Last updated:** 2026-05-06
**Domain:** Brúarhönd — Hengilherðir, the Reaching Client
**Module:** `src/seidr_smidja/brunhand/client/`
**Keeper:** Rúnhild Svartdóttir (Architect)

---

## Purpose

Hengilherðir is the forge-side client library for Brúarhönd. It forms signed HTTP requests, manages session state, handles retries and timeouts, and feeds screenshots into the Oracle Eye through Ljósbrú. It runs in the forge process; it has no GUI dependencies of its own.

---

## Configuration Loading

Client configuration is loaded from the layered config system:

```yaml
# config/defaults.yaml
brunhand:
  client:
    timeout_seconds: 30.0
    connect_timeout_seconds: 5.0
    retry_max: 3
    retry_backoff_base: 0.5
    retry_on: [500, 502, 503]
    verify_ssl: true
  hosts:
    - name: "vroid-host"
      address: "vroid-host.tailnet.ts.net"
      port: 8848
      tls: true
```

Token loading for client-side: `BRUNHAND_TOKEN` env var or `brunhand.daemon.token` in config.

**Per-call overrides:** `BrunhandClient(host, token, timeout)` constructor parameters take precedence over config file values.

---

## `BrunhandClient` — Class Signature

```python
class BrunhandClient:
    def __init__(
        self,
        host: str,
        token: str,
        port: int = 8848,
        tls: bool = True,
        timeout: float | None = None,          # Overrides config if set
        connect_timeout: float | None = None,
        verify_ssl: bool | None = None,
        config: BrunhandConfig | None = None,  # Loaded from YAML if None
    ) -> None: ...
```

All methods below return typed result objects. All methods raise typed `BrunhandError` subclasses on failure (never bare `httpx` exceptions).

---

## `BrunhandClient` Methods

### `health() -> HealthResult`

Calls `GET /v1/brunhand/health`. Does not require authentication.

```python
@dataclass
class HealthResult:
    daemon_version: str
    os_name: str
    uptime_seconds: float
    status: str              # "ok"
```

**Raises:** `BrunhandConnectionError` if daemon unreachable.

---

### `capabilities() -> CapabilitiesManifest`

Calls `GET /v1/brunhand/capabilities`. Requires authentication.

```python
@dataclass
class CapabilitiesManifest:
    daemon_version: str
    os_name: str
    os_version: str
    screen_geometry: list[ScreenRect]
    primitives: dict[str, PrimitiveStatus]
    probed_at: str
```

**Raises:** `BrunhandAuthError`, `BrunhandConnectionError`.

---

### `screenshot(region: ScreenRect | None = None, session_id: str = "", agent_id: str = "") -> ScreenshotResult`

Calls `POST /v1/brunhand/screenshot`.

```python
@dataclass
class ScreenshotResult:
    success: bool
    png_bytes: bytes          # Decoded from base64 response
    width: int
    height: int
    captured_at: str
    monitor_index: int
    error: BrunhandErrorDetail | None
```

**Raises:** `BrunhandAuthError`, `BrunhandConnectionError`, `BrunhandTimeoutError`, `BrunhandPrimitiveError`.

---

### `click(x: int, y: int, button: str = "left", clicks: int = 1, interval: float = 0.0, modifiers: list[str] | None = None, session_id: str = "", agent_id: str = "") -> ClickResult`

```python
@dataclass
class ClickResult:
    success: bool
    x: int
    y: int
    button: str
    clicks_delivered: int
    error: BrunhandErrorDetail | None
```

**Raises:** `BrunhandAuthError`, `BrunhandConnectionError`, `BrunhandPrimitiveError`.

---

### `move(x: int, y: int, duration: float = 0.25, tween: str = "linear", session_id: str = "", agent_id: str = "") -> MoveResult`

```python
@dataclass
class MoveResult:
    success: bool
    x: int
    y: int
    error: BrunhandErrorDetail | None
```

---

### `drag(x1: int, y1: int, x2: int, y2: int, button: str = "left", duration: float = 0.5, session_id: str = "", agent_id: str = "") -> DragResult`

```python
@dataclass
class DragResult:
    success: bool
    from_pos: tuple[int, int]
    to_pos: tuple[int, int]
    error: BrunhandErrorDetail | None
```

---

### `scroll(x: int, y: int, clicks: int, direction: str = "down", session_id: str = "", agent_id: str = "") -> ScrollResult`

```python
@dataclass
class ScrollResult:
    success: bool
    x: int
    y: int
    clicks: int
    direction: str
    error: BrunhandErrorDetail | None
```

---

### `type_text(text: str, interval: float = 0.05, session_id: str = "", agent_id: str = "") -> TypeResult`

```python
@dataclass
class TypeResult:
    success: bool
    characters_typed: int
    error: BrunhandErrorDetail | None
```

---

### `hotkey(keys: list[str], session_id: str = "", agent_id: str = "") -> HotkeyResult`

```python
@dataclass
class HotkeyResult:
    success: bool
    keys: list[str]
    error: BrunhandErrorDetail | None
```

---

### `find_window(title_pattern: str, exact: bool = False, session_id: str = "", agent_id: str = "") -> FindWindowResult`

```python
@dataclass
class FindWindowResult:
    success: bool
    found: bool                    # True if at least one window matched
    windows: list[WindowInfo]
    error: BrunhandErrorDetail | None

@dataclass
class WindowInfo:
    title: str
    left: int
    top: int
    width: int
    height: int
    is_foreground: bool
```

---

### `wait_for_window(title_pattern: str, timeout_seconds: float = 30.0, poll_interval_seconds: float = 0.5, session_id: str = "", agent_id: str = "") -> WaitForWindowResult`

```python
@dataclass
class WaitForWindowResult:
    success: bool
    found: bool                    # False = timed out (not an error at success=true level)
    elapsed_seconds: float
    window: WindowInfo | None
    error: BrunhandErrorDetail | None
```

---

### `vroid_export_vrm(output_path: str, overwrite: bool = True, wait_timeout_seconds: float = 120.0, session_id: str = "", agent_id: str = "") -> VroidExportResult`

```python
@dataclass
class VroidExportResult:
    success: bool
    exported_path: str
    elapsed_seconds: float
    steps_executed: list[str]
    error: BrunhandErrorDetail | None
```

---

### `vroid_save_project(session_id: str = "", agent_id: str = "") -> VroidSaveResult`

```python
@dataclass
class VroidSaveResult:
    success: bool
    elapsed_seconds: float
    steps_executed: list[str]
    error: BrunhandErrorDetail | None
```

---

### `vroid_open_project(project_path: str, wait_timeout_seconds: float = 60.0, session_id: str = "", agent_id: str = "") -> VroidOpenResult`

```python
@dataclass
class VroidOpenResult:
    success: bool
    opened_path: str
    elapsed_seconds: float
    steps_executed: list[str]
    error: BrunhandErrorDetail | None
```

---

## `Tengslastig` — Session Context Manager

### `brunhand.session(...)` — Top-Level Factory

```python
def session(
    host: str,
    token: str | None = None,
    port: int = 8848,
    tls: bool = True,
    timeout: float | None = None,
    run_id: str | None = None,
    annall: AnnallPort | None = None,
    oracle_eye_module: Any | None = None,
    config: BrunhandConfig | None = None,
) -> ContextManager[Tengslastig]:
    ...
```

### `Tengslastig` Properties

| Property | Type | Description |
|---|---|---|
| `session_id` | `str` | UUID identifying this session; threaded into every request |
| `run_id` | `str \| None` | If set, links to a `dispatch()` `BuildResponse.annall_session_id` |
| `capabilities` | `CapabilitiesManifest` | Cached on `__enter__`; refreshable via `sess.refresh_capabilities()` |
| `command_count` | `int` | Number of primitives successfully executed in this session |
| `host` | `str` | Target host |

### `Tengslastig` Methods

All `BrunhandClient` methods are available on `Tengslastig` directly — the session threads `session_id` and `agent_id` automatically.

#### `execute_and_see(primitive_fn: Callable, *args, **kwargs) -> ExecuteAndSeeResult`

Executes a primitive, then automatically captures a screenshot and feeds it to Ljósbrú.

```python
@dataclass
class ExecuteAndSeeResult:
    primitive_result: Any          # The result of primitive_fn(*args, **kwargs)
    screenshot_result: ScreenshotResult
    oracle_render_result: ExternalRenderResult | None   # None if oracle_eye not injected
```

**Example:**
```python
with brunhand.session(host="vroid-host.tailnet.ts.net", annall=annall) as sess:
    result = sess.execute_and_see(sess.click, x=412, y=288)
    # result.primitive_result — ClickResult
    # result.screenshot_result — ScreenshotResult with PNG bytes
    # result.oracle_render_result — ExternalRenderResult if Oracle Eye injected
```

#### `refresh_capabilities() -> CapabilitiesManifest`

Re-probes the daemon and updates the cached `CapabilitiesManifest`.

---

## `Ljósbrú` — Oracle Eye Integration

**Module:** `brunhand/client/oracle_channel.py`

`Ljósbrú` is an internal adapter. It is not part of the direct caller-facing API — it is used by `Tengslastig.execute_and_see()` and by direct `BrunhandClient.screenshot()` calls within a session.

### `Ljósbrú.feed(screenshot_result: ScreenshotResult, session: Tengslastig) -> ExternalRenderResult | None`

Calls `oracle_eye.register_external_render()` with the screenshot bytes. Returns `None` if Oracle Eye was not injected into the session.

**What Ljósbrú must never do:**
- Return raw PNG bytes to Bridge callers as a substitute for Oracle Eye registration.
- Construct its own render pipeline.
- Access any Brúarhönd channel other than `oracle_eye.register_external_render()`.

---

## Exception Class Hierarchy

```python
class BrunhandError(Exception):
    """Base class for all Brúarhönd exceptions."""
    host: str
    primitive: str
    request_id: str
    session_id: str
    message: str

class BrunhandConnectionError(BrunhandError):
    """Daemon unreachable — Tailscale partition, daemon down, port refused."""

class BrunhandAuthError(BrunhandError):
    """Bearer token rejected — 401 response."""

class BrunhandTimeoutError(BrunhandError):
    """Request exceeded configured timeout."""

class BrunhandCapabilitiesError(BrunhandError):
    """Daemon reported the requested primitive is not available on its platform.
    Raised locally by Tengslastig before making a network call, based on cached manifest."""
    primitive_name: str
    platform: str
    available_primitives: list[str]

class BrunhandPrimitiveError(BrunhandError):
    """Daemon executed the primitive but it raised an OS-level error.
    The daemon is still alive; the primitive failed."""
    vroid_running: bool
    screen_accessible: bool
    permission_denied: bool
    stack_summary: str | None

class VroidNotRunningError(BrunhandPrimitiveError):
    """VRoid Studio process was not detected on the daemon host."""

class BrunhandProtocolError(BrunhandError):
    """Response shape did not match expected schema — version mismatch or unexpected format."""
    raw_status_code: int
    raw_body_preview: str
```

**Raise conditions summary:**

| Exception | When |
|---|---|
| `BrunhandConnectionError` | `httpx.ConnectError`, `httpx.ConnectTimeout`, daemon port refused |
| `BrunhandAuthError` | HTTP 401 from daemon |
| `BrunhandTimeoutError` | `httpx.ReadTimeout`, `httpx.WriteTimeout` |
| `BrunhandCapabilitiesError` | `capabilities.primitives[name].available == False` (local check) |
| `BrunhandPrimitiveError` | HTTP 200 with `success=false` and OS-level error detail |
| `VroidNotRunningError` | HTTP 200 with `success=false` and `vroid_running=false` |
| `BrunhandProtocolError` | HTTP 200 with unrecognized response schema; HTTP 5xx without structured body |

---

## Annáll Events Emitted (Forge-Side)

| Event type | When emitted |
|---|---|
| `brunhand.client.session.opened` | On `Tengslastig.__enter__` |
| `brunhand.client.session.closed` | On `Tengslastig.__exit__` |
| `brunhand.client.primitive.sent` | Before each HTTP request |
| `brunhand.client.primitive.received` | After successful response |
| `brunhand.client.primitive.error` | On exception |
| `brunhand.client.oracle.fed` | After Ljósbrú calls register_external_render |

---

## Invariants

1. `Tengslastig` always probes capabilities on session open. A session against an unreachable daemon raises `BrunhandConnectionError` at `__enter__`, never silently.
2. Screenshot bytes are always routed through `Ljósbrú` to Oracle Eye when an `oracle_eye_module` is provided. Raw PNG bytes are never returned to Bridge callers as a vision substitute.
3. The bearer token is never included in any `AnnallEvent` payload, log message, or exception string.
4. Exceptions from `BrunhandClient` methods are always typed `BrunhandError` subclasses — never bare `httpx` exceptions propagated to callers.
5. `Tengslastig` logs a session-close event even if `__exit__` is called due to an exception.

---

## Dependencies

- `httpx>=0.27` — HTTP client (sync)
- `pydantic>=2.0` — request/response model validation
- `seidr_smidja.annall.port` — forge-side telemetry (injected, never global)
- `seidr_smidja.oracle_eye` — vision integration via `register_external_render()` (injected, optional)
- `seidr_smidja.config` — configuration loading

No GUI dependencies. No PyAutoGUI. No MSS.

---

*Rúnhild Svartdóttir, Architect — 2026-05-06*
