# Horfunarþjónn — Daemon HTTP API Contract
**Last updated:** 2026-05-06
**Domain:** Brúarhönd — Horfunarþjónn, the Watching-Daemon
**Module:** `src/seidr_smidja/brunhand/daemon/`
**Keeper:** Rúnhild Svartdóttir (Architect)

---

## Purpose

Horfunarþjónn is the FastAPI HTTP server that runs on the VRoid Studio host machine. It receives bearer-authenticated commands, executes them on the live desktop via PyAutoGUI/MSS/pygetwindow, and returns structured responses. It is the far end of the Brúarhönd bridge.

**Invocation:** `python -m seidr_smidja.brunhand.daemon`
**Default bind:** `127.0.0.1:8848`
**API prefix:** `/v1/brunhand/`

---

## Authentication

All endpoints except `GET /v1/brunhand/health` require:

```
Authorization: Bearer <token>
```

The token is validated by Gæslumaðr (constant-time comparison via `hmac.compare_digest()`). Missing or invalid token returns:

```json
HTTP 401 Unauthorized
{
    "error": "unauthorized",
    "message": "Bearer token is missing or invalid."
}
```

The token value is never echoed in any response. The header value is logged as `[REDACTED]` in all Annáll events.

---

## Shared Envelope

### Request Envelope Fields

Every authenticated POST request body must include these universal fields alongside primitive-specific parameters:

```json
{
    "request_id": "uuid-string",
    "session_id": "uuid-string",
    "agent_id": "string"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `request_id` | `string` (UUID) | Yes | Unique per-request identifier; echoed in response |
| `session_id` | `string` | Yes | Tengslastig session identifier; used for Annáll correlation |
| `agent_id` | `string` | Yes | Agent identity string for audit log |

### Response Envelope

Every response (success or failure) is wrapped in:

```json
{
    "request_id": "uuid-string",
    "session_id": "uuid-string",
    "success": true,
    "payload": {},
    "error": null,
    "daemon_timestamp": "2026-05-06T12:00:00.000Z",
    "latency_ms": 42.7
}
```

| Field | Type | Description |
|---|---|---|
| `request_id` | `string` | Echoed from request |
| `session_id` | `string` | Echoed from request |
| `success` | `boolean` | True if the primitive executed without error |
| `payload` | `object` | Primitive-specific result data (schema below per endpoint) |
| `error` | `BrunhandErrorDetail \| null` | Structured error if `success=false` |
| `daemon_timestamp` | `string` | ISO 8601 UTC timestamp of response assembly |
| `latency_ms` | `float` | Wall-clock time from request receipt to response assembly |

### `BrunhandErrorDetail` Schema

```json
{
    "error_type": "string",
    "message": "string",
    "primitive": "string",
    "vroid_running": true,
    "screen_accessible": true,
    "permission_denied": false,
    "platform": "windows",
    "stack_summary": "string | null"
}
```

---

## Versioning Policy

All endpoints are prefixed with `/v1/`. Evolution policy:
- Additive changes (new optional request fields, new optional response fields) are non-breaking and require no version bump.
- Breaking changes (removing fields, changing field semantics, changing HTTP method) require a new version prefix (`/v2/`).
- v1 endpoints remain available when v2 is introduced.

---

## Rate Limit and Timeout Defaults

| Setting | Default | Config key |
|---|---|---|
| Rate limit | Disabled | `brunhand.daemon.rate_limit` |
| Rate limit window | 60 seconds | `brunhand.daemon.rate_limit_window_seconds` |
| Max requests per window | 120 | `brunhand.daemon.rate_limit_max` |
| Request timeout (uvicorn) | 60 seconds | `brunhand.daemon.request_timeout_seconds` |
| Max screenshot region | Full screen | `brunhand.daemon.max_screenshot_region` |

---

## Endpoint Table

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/v1/brunhand/health` | None | Heartbeat — daemon liveness probe |
| `GET` | `/v1/brunhand/capabilities` | Bearer | Platform capabilities manifest |
| `POST` | `/v1/brunhand/screenshot` | Bearer | Capture full screen or region as PNG |
| `POST` | `/v1/brunhand/click` | Bearer | Mouse click at coordinates |
| `POST` | `/v1/brunhand/move` | Bearer | Mouse move to coordinates |
| `POST` | `/v1/brunhand/drag` | Bearer | Mouse drag from point to point |
| `POST` | `/v1/brunhand/scroll` | Bearer | Mouse wheel scroll |
| `POST` | `/v1/brunhand/type` | Bearer | Type a text string |
| `POST` | `/v1/brunhand/hotkey` | Bearer | Press a key combination |
| `POST` | `/v1/brunhand/find_window` | Bearer | Find window geometry by title pattern |
| `POST` | `/v1/brunhand/wait_for_window` | Bearer | Block until window appears |
| `POST` | `/v1/brunhand/vroid/export_vrm` | Bearer | Drive VRoid Studio export-VRM flow |
| `POST` | `/v1/brunhand/vroid/save_project` | Bearer | Save current .vroid project |
| `POST` | `/v1/brunhand/vroid/open_project` | Bearer | Open a .vroid project file |

---

## Endpoint Contracts

---

### `GET /v1/brunhand/health`

**Auth:** None required.

**Response 200:**
```json
{
    "daemon_version": "0.1.0",
    "os_name": "windows",
    "uptime_seconds": 3600.0,
    "status": "ok"
}
```

**No error responses** — if the daemon is down, the HTTP connection fails.

---

### `GET /v1/brunhand/capabilities`

**Auth:** Bearer required.

**Response 200 payload:**
```json
{
    "daemon_version": "0.1.0",
    "os_name": "windows",
    "os_version": "10.0.22621",
    "screen_geometry": [
        {"monitor_index": 0, "left": 0, "top": 0, "width": 1920, "height": 1080}
    ],
    "primitives": {
        "screenshot":              {"available": true,  "library": "mss",          "degraded": false, "degraded_reason": null},
        "click":                   {"available": true,  "library": "pyautogui",    "degraded": false, "degraded_reason": null},
        "move":                    {"available": true,  "library": "pyautogui",    "degraded": false, "degraded_reason": null},
        "drag":                    {"available": true,  "library": "pyautogui",    "degraded": false, "degraded_reason": null},
        "scroll":                  {"available": true,  "library": "pyautogui",    "degraded": false, "degraded_reason": null},
        "type_text":               {"available": true,  "library": "pyautogui",    "degraded": false, "degraded_reason": null},
        "hotkey":                  {"available": true,  "library": "pyautogui",    "degraded": false, "degraded_reason": null},
        "find_window":             {"available": true,  "library": "pygetwindow",  "degraded": false, "degraded_reason": null},
        "wait_for_window":         {"available": true,  "library": "pygetwindow",  "degraded": false, "degraded_reason": null},
        "find_window_by_accessibility": {"available": true, "library": "pywinauto", "degraded": false, "degraded_reason": null}
    },
    "probed_at": "2026-05-06T12:00:00.000Z"
}
```

**Error responses:**
- `401` — auth failure (standard envelope)

---

### `POST /v1/brunhand/screenshot`

**Auth:** Bearer required.

**Request body:**
```json
{
    "request_id": "uuid",
    "session_id": "uuid",
    "agent_id": "string",
    "region": null
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `region` | `ScreenRect \| null` | No | If null, captures full primary monitor. If provided: `{"left": int, "top": int, "width": int, "height": int}` |

**Response 200 payload:**
```json
{
    "png_bytes_b64": "<base64-encoded PNG>",
    "width": 1920,
    "height": 1080,
    "captured_at": "2026-05-06T12:00:00.000Z",
    "monitor_index": 0
}
```

**Error responses:**
- `401` — auth failure
- `200 success=false` — screen inaccessible, permission denied

---

### `POST /v1/brunhand/click`

**Request body:**
```json
{
    "request_id": "uuid",
    "session_id": "uuid",
    "agent_id": "string",
    "x": 412,
    "y": 288,
    "button": "left",
    "clicks": 1,
    "interval": 0.0,
    "modifiers": []
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `x` | `int` | Yes | Screen X coordinate |
| `y` | `int` | Yes | Screen Y coordinate |
| `button` | `"left" \| "right" \| "middle"` | No (default: `"left"`) | Mouse button |
| `clicks` | `int` | No (default: `1`) | Number of clicks |
| `interval` | `float` | No (default: `0.0`) | Seconds between clicks |
| `modifiers` | `list[string]` | No (default: `[]`) | Held modifier keys e.g. `["shift", "ctrl"]` |

**Response 200 payload:**
```json
{
    "x": 412,
    "y": 288,
    "button": "left",
    "clicks_delivered": 1
}
```

---

### `POST /v1/brunhand/move`

**Request body:**
```json
{
    "request_id": "uuid",
    "session_id": "uuid",
    "agent_id": "string",
    "x": 500,
    "y": 300,
    "duration": 0.25,
    "tween": "linear"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `x` | `int` | Yes | Target X coordinate |
| `y` | `int` | Yes | Target Y coordinate |
| `duration` | `float` | No (default: `0.25`) | Move duration in seconds |
| `tween` | `string` | No (default: `"linear"`) | Easing: `"linear"`, `"ease_in_out"` |

**Response 200 payload:**
```json
{ "x": 500, "y": 300 }
```

---

### `POST /v1/brunhand/drag`

**Request body:**
```json
{
    "request_id": "uuid",
    "session_id": "uuid",
    "agent_id": "string",
    "x1": 100, "y1": 200,
    "x2": 400, "y2": 200,
    "button": "left",
    "duration": 0.5
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `x1`, `y1` | `int` | Yes | Drag start coordinates |
| `x2`, `y2` | `int` | Yes | Drag end coordinates |
| `button` | `string` | No (default: `"left"`) | Mouse button held during drag |
| `duration` | `float` | No (default: `0.5`) | Drag duration in seconds |

**Response 200 payload:**
```json
{ "from": [100, 200], "to": [400, 200] }
```

---

### `POST /v1/brunhand/scroll`

**Request body:**
```json
{
    "request_id": "uuid",
    "session_id": "uuid",
    "agent_id": "string",
    "x": 960, "y": 540,
    "clicks": 3,
    "direction": "down"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `x`, `y` | `int` | Yes | Scroll target coordinates |
| `clicks` | `int` | Yes | Number of scroll notches |
| `direction` | `"up" \| "down"` | No (default: `"down"`) | Scroll direction |

**Response 200 payload:**
```json
{ "x": 960, "y": 540, "clicks": 3, "direction": "down" }
```

---

### `POST /v1/brunhand/type`

**Request body:**
```json
{
    "request_id": "uuid",
    "session_id": "uuid",
    "agent_id": "string",
    "text": "Hello VRoid",
    "interval": 0.05
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `text` | `string` | Yes | Text to type. Unicode supported. |
| `interval` | `float` | No (default: `0.05`) | Seconds between keystrokes |

**Response 200 payload:**
```json
{ "characters_typed": 11 }
```

---

### `POST /v1/brunhand/hotkey`

**Request body:**
```json
{
    "request_id": "uuid",
    "session_id": "uuid",
    "agent_id": "string",
    "keys": ["ctrl", "s"]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `keys` | `list[string]` | Yes | Ordered list of keys; all pressed simultaneously. See PyAutoGUI key names. |

**Response 200 payload:**
```json
{ "keys": ["ctrl", "s"] }
```

---

### `POST /v1/brunhand/find_window`

**Request body:**
```json
{
    "request_id": "uuid",
    "session_id": "uuid",
    "agent_id": "string",
    "title_pattern": "VRoid Studio",
    "exact": false
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `title_pattern` | `string` | Yes | Window title or substring/regex to match |
| `exact` | `boolean` | No (default: `false`) | If true, exact title match only |

**Response 200 payload:**
```json
{
    "found": true,
    "windows": [
        {
            "title": "VRoid Studio 1.28.1",
            "left": 0, "top": 0,
            "width": 1440, "height": 900,
            "is_foreground": true
        }
    ]
}
```

**Success with `found=false`:** No windows matched; `windows=[]`. This is `success=true` at the envelope level — the search executed; it simply found nothing.

---

### `POST /v1/brunhand/wait_for_window`

**Request body:**
```json
{
    "request_id": "uuid",
    "session_id": "uuid",
    "agent_id": "string",
    "title_pattern": "Export VRM",
    "timeout_seconds": 30.0,
    "poll_interval_seconds": 0.5
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `title_pattern` | `string` | Yes | Window title or pattern to wait for |
| `timeout_seconds` | `float` | No (default: `30.0`) | Maximum wait time |
| `poll_interval_seconds` | `float` | No (default: `0.5`) | How often to check |

**Response 200 payload:**
```json
{
    "found": true,
    "elapsed_seconds": 2.3,
    "window": {
        "title": "Export VRM",
        "left": 200, "top": 150,
        "width": 600, "height": 400,
        "is_foreground": true
    }
}
```

**Timeout (not an error, `success=true`):** `found=false`, `elapsed_seconds=30.0`, `window=null`.

---

### `POST /v1/brunhand/vroid/export_vrm`

High-level script: drives VRoid Studio's File → Export → Export VRM flow.

**Request body:**
```json
{
    "request_id": "uuid",
    "session_id": "uuid",
    "agent_id": "string",
    "output_path": "relative/path/to/output.vrm",
    "overwrite": true,
    "wait_timeout_seconds": 120.0
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `output_path` | `string` | Yes | Path on the daemon host where VRoid should save the file. Must be relative to the daemon's configured `brunhand.daemon.export_root`. |
| `overwrite` | `boolean` | No (default: `true`) | Whether to confirm overwrite if file exists |
| `wait_timeout_seconds` | `float` | No (default: `120.0`) | Max seconds to wait for export dialog and completion |

**Response 200 payload:**
```json
{
    "exported_path": "relative/path/to/output.vrm",
    "elapsed_seconds": 8.4,
    "steps_executed": ["hotkey_file_menu", "click_export_vrm", "set_path", "confirm_dialog"]
}
```

**Error responses:**
- `200 success=false` — VRoid not running, export dialog did not appear within timeout, file write failed.

---

### `POST /v1/brunhand/vroid/save_project`

High-level script: saves the current VRoid Studio project.

**Request body:**
```json
{
    "request_id": "uuid",
    "session_id": "uuid",
    "agent_id": "string"
}
```

No additional fields — saves whatever is currently open.

**Response 200 payload:**
```json
{
    "elapsed_seconds": 1.2,
    "steps_executed": ["hotkey_ctrl_s"]
}
```

---

### `POST /v1/brunhand/vroid/open_project`

High-level script: opens a .vroid project file in VRoid Studio.

**Request body:**
```json
{
    "request_id": "uuid",
    "session_id": "uuid",
    "agent_id": "string",
    "project_path": "relative/path/to/character.vroid",
    "wait_timeout_seconds": 60.0
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `project_path` | `string` | Yes | Path on the daemon host. Must be relative to daemon's configured `brunhand.daemon.project_root`. |
| `wait_timeout_seconds` | `float` | No (default: `60.0`) | Max seconds to wait for VRoid to load the project |

**Response 200 payload:**
```json
{
    "opened_path": "relative/path/to/character.vroid",
    "elapsed_seconds": 5.1,
    "steps_executed": ["hotkey_file_open", "set_path", "confirm_open", "wait_for_load"]
}
```

---

## Error Response Codes

| HTTP Status | Meaning |
|---|---|
| `200 success=false` | Primitive executed but failed at the OS/application level. Full `BrunhandErrorDetail` in `error` field. |
| `400` | Malformed request body (field missing or wrong type). |
| `401` | Authentication failure — bearer token absent or invalid. |
| `422` | Pydantic validation error — request body fails schema validation. |
| `423` | Session lock — daemon has an active session from another connection. |
| `429` | Rate limit exceeded (when rate limiting is configured). |
| `500` | Internal daemon error (unhandled exception in handler code). |
| `503` | Daemon is shutting down or in degraded state. |

---

## Annáll Events Emitted

Every request logs to the daemon's local Annáll instance:

| Event type | When emitted |
|---|---|
| `brunhand.daemon.request.received` | Every request, before Gæslumaðr check |
| `brunhand.daemon.auth.rejected` | On 401 |
| `brunhand.daemon.primitive.started` | Before primitive execution |
| `brunhand.daemon.primitive.completed` | On success |
| `brunhand.daemon.primitive.failed` | On primitive error |
| `brunhand.daemon.capabilities.probed` | On daemon startup |
| `brunhand.daemon.session.locked` | On 423 |

---

*Rúnhild Svartdóttir, Architect — 2026-05-06*
