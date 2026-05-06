"""seidr_smidja.brunhand.client.client — BrunhandClient, Hengilherðir.

The forge-side HTTP client for Brúarhönd. One method per daemon endpoint.

INVARIANTS:
  - Never propagates bare httpx exceptions — always raises typed BrunhandError subclasses.
  - Bearer token is never included in any log, exception string, or Annáll event.
  - Automatic timeout propagation: when a primitive request includes timeout_seconds,
    the httpx request timeout is set to (timeout_seconds + request_timeout_buffer).
    This prevents the HTTP connection from timing out before the daemon finishes.
    (D-010 Cartographer tension #3 resolution.)
  - No GUI dependencies. Requires only: httpx, pydantic.

See: src/seidr_smidja/brunhand/client/INTERFACE.md
See: docs/features/brunhand/ARCHITECTURE.md §IV The Client (Hengilherðir)
"""
from __future__ import annotations

import base64
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False
    httpx = None  # type: ignore[assignment]


# ─── Result dataclasses ───────────────────────────────────────────────────────


@dataclass
class HealthResult:
    daemon_version: str = ""
    os_name: str = ""
    uptime_seconds: float = 0.0
    status: str = "ok"


@dataclass
class ScreenshotResult:
    success: bool = True
    png_bytes: bytes = b""
    width: int = 0
    height: int = 0
    captured_at: str = ""
    monitor_index: int = 0
    error: Any = None


@dataclass
class ClickResult:
    success: bool = True
    x: int = 0
    y: int = 0
    button: str = "left"
    clicks_delivered: int = 1
    error: Any = None


@dataclass
class MoveResult:
    success: bool = True
    x: int = 0
    y: int = 0
    error: Any = None


@dataclass
class DragResult:
    success: bool = True
    from_pos: tuple[int, int] = (0, 0)
    to_pos: tuple[int, int] = (0, 0)
    error: Any = None


@dataclass
class ScrollResult:
    success: bool = True
    x: int = 0
    y: int = 0
    clicks: int = 0
    direction: str = "down"
    error: Any = None


@dataclass
class TypeResult:
    success: bool = True
    characters_typed: int = 0
    error: Any = None


@dataclass
class HotkeyResult:
    success: bool = True
    keys: list[str] = field(default_factory=list)
    error: Any = None


@dataclass
class WindowInfo:
    title: str = ""
    left: int = 0
    top: int = 0
    width: int = 0
    height: int = 0
    is_foreground: bool = False


@dataclass
class FindWindowResult:
    success: bool = True
    found: bool = False
    windows: list[WindowInfo] = field(default_factory=list)
    error: Any = None


@dataclass
class WaitForWindowResult:
    success: bool = True
    found: bool = False
    elapsed_seconds: float = 0.0
    window: WindowInfo | None = None
    error: Any = None


@dataclass
class VroidExportResult:
    success: bool = True
    exported_path: str = ""
    elapsed_seconds: float = 0.0
    steps_executed: list[str] = field(default_factory=list)
    error: Any = None


@dataclass
class VroidSaveResult:
    success: bool = True
    elapsed_seconds: float = 0.0
    steps_executed: list[str] = field(default_factory=list)
    error: Any = None


@dataclass
class VroidOpenResult:
    success: bool = True
    opened_path: str = ""
    elapsed_seconds: float = 0.0
    steps_executed: list[str] = field(default_factory=list)
    error: Any = None


@dataclass
class CapabilitiesManifestResult:
    """Deserialized capabilities manifest from the daemon."""
    daemon_version: str = ""
    os_name: str = ""
    os_version: str = ""
    screen_geometry: list[dict[str, Any]] = field(default_factory=list)
    primitives: dict[str, dict[str, Any]] = field(default_factory=dict)
    probed_at: str = ""


# ─── BrunhandClient ───────────────────────────────────────────────────────────


class BrunhandClient:
    """Hengilherðir — the Reaching Client.

    Low-level client for the Brúarhönd daemon. One method per daemon endpoint.
    All methods return typed result objects and raise typed BrunhandError subclasses.

    Automatic timeout propagation (D-010 tension #3):
    When a primitive request includes a `timeout_seconds` field (e.g., wait_for_window),
    the httpx request timeout is automatically extended to:
        timeout_seconds + request_timeout_buffer (default: 5.0 seconds)
    This ensures the HTTP connection doesn't time out before the daemon finishes.
    """

    def __init__(
        self,
        host: str,
        token: str,
        port: int = 8848,
        tls: bool = True,
        timeout: float | None = None,
        connect_timeout: float | None = None,
        verify_tls: bool | str = True,
        http_scheme: str | None = None,
        config: dict[str, Any] | None = None,
        request_timeout_buffer: float = 5.0,
    ) -> None:
        if not _HTTPX_AVAILABLE:
            raise ImportError(
                "httpx is required for the Brúarhönd client. "
                "Install with: pip install httpx or pip install seidr-smidja"
            )

        self.host = host
        self._token = token  # Never logged
        self.port = port
        self.request_timeout_buffer = request_timeout_buffer

        # Resolve configuration
        cfg = config or {}
        client_cfg = cfg.get("brunhand", {}).get("client", {})

        self._base_timeout = timeout or client_cfg.get("timeout_seconds", 30.0)
        self._connect_timeout = connect_timeout or client_cfg.get("connect_timeout_seconds", 5.0)
        self._retry_max = client_cfg.get("retry_max", 3)
        self._retry_backoff = client_cfg.get("retry_backoff_base", 0.5)
        self._retry_on = set(client_cfg.get("retry_on", [500, 502, 503]))
        default_tls = client_cfg.get("verify_tls", True)
        self._verify_tls = verify_tls if verify_tls is not None else default_tls

        # Determine scheme: explicit override > tls flag > localhost detection
        if http_scheme:
            self._scheme = http_scheme
        elif not tls or host in ("127.0.0.1", "localhost", "::1"):
            self._scheme = "http"
        else:
            self._scheme = "https"

        self._base_url = f"{self._scheme}://{host}:{port}"

        # B-008: Warn when TLS verification is disabled (ARCHITECTURE.md §X).
        if not self._verify_tls:
            logger.warning(
                "BrunhandClient: TLS verification disabled for host %s. "
                "Only acceptable on Tailscale-internal topology where the network "
                "layer provides confidentiality. Do NOT use on public networks.",
                host,
            )

        # Build httpx client
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=httpx.Timeout(self._base_timeout, connect=self._connect_timeout),
            verify=self._verify_tls,  # type: ignore[arg-type]
        )

    def close(self) -> None:
        """Close the underlying httpx client."""
        import contextlib
        with contextlib.suppress(Exception):
            self._client.close()

    def __enter__(self) -> BrunhandClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _post(
        self,
        path: str,
        body: dict[str, Any],
        primitive_timeout: float | None = None,
    ) -> dict[str, Any]:
        """Execute an authenticated POST request.

        Implements:
          - Automatic timeout propagation for primitives with their own timeout.
          - Retry logic for transient server errors (500, 502, 503).
          - Typed exception mapping (never propagates bare httpx exceptions).
        """
        from seidr_smidja.brunhand.exceptions import (
            BrunhandAuthError,
            BrunhandConnectionError,
            BrunhandProtocolError,
            BrunhandTimeoutError,
        )

        # D-010 tension #3: automatic timeout propagation
        if primitive_timeout is not None:
            effective_timeout = primitive_timeout + self.request_timeout_buffer
        else:
            effective_timeout = self._base_timeout

        timeout_obj = httpx.Timeout(effective_timeout, connect=self._connect_timeout)

        last_exc: Exception | None = None
        for attempt in range(max(1, self._retry_max)):
            try:
                response = self._client.post(path, json=body, timeout=timeout_obj)
            except httpx.ConnectError as exc:
                raise BrunhandConnectionError(
                    f"Cannot connect to daemon at {self._base_url}: {exc}",
                    cause="connect",
                    host=self.host,
                    primitive=body.get("primitive", path),
                    request_id=body.get("request_id", ""),
                    session_id=body.get("session_id", ""),
                ) from exc
            except httpx.ConnectTimeout as exc:
                raise BrunhandConnectionError(
                    f"Connection timeout to daemon at {self._base_url}: {exc}",
                    cause="connect",
                    host=self.host,
                    primitive=body.get("primitive", path),
                ) from exc
            except (httpx.ReadTimeout, httpx.WriteTimeout) as exc:
                raise BrunhandTimeoutError(
                    f"Request to {self._base_url}{path} timed out: {exc}",
                    host=self.host,
                    primitive=body.get("primitive", path),
                ) from exc
            except httpx.TLSError as exc:
                raise BrunhandConnectionError(
                    f"TLS error connecting to daemon at {self._base_url}: {exc}",
                    cause="tls",
                    host=self.host,
                ) from exc
            except httpx.HTTPError as exc:
                # Any other HTTP-level error
                raise BrunhandConnectionError(
                    f"HTTP error communicating with daemon at {self._base_url}: {exc}",
                    cause="unknown",
                    host=self.host,
                ) from exc

            # ── Handle HTTP status codes ──────────────────────────────────────
            if response.status_code == 401:
                raise BrunhandAuthError(
                    "Bearer token rejected by daemon (HTTP 401).",
                    host=self.host,
                    primitive=body.get("primitive", path),
                    request_id=body.get("request_id", ""),
                    session_id=body.get("session_id", ""),
                )

            if response.status_code == 403:
                raise BrunhandAuthError(
                    "Access forbidden by daemon (HTTP 403).",
                    host=self.host,
                    primitive=body.get("primitive", path),
                )

            if response.status_code in self._retry_on and attempt < self._retry_max - 1:
                wait = self._retry_backoff * (2 ** attempt)
                logger.warning(
                    "BrunhandClient: HTTP %d from %s%s — retrying in %.1fs (attempt %d/%d)",
                    response.status_code, self._base_url, path, wait, attempt + 1, self._retry_max,
                )
                time.sleep(wait)
                last_exc = BrunhandProtocolError(
                    f"HTTP {response.status_code} from daemon",
                    raw_status_code=response.status_code,
                    raw_body_preview=response.text[:200],
                    host=self.host,
                )
                continue

            if response.status_code not in (200, 201, 202):
                raise BrunhandProtocolError(
                    f"Unexpected HTTP {response.status_code} from daemon at {path}",
                    raw_status_code=response.status_code,
                    raw_body_preview=response.text[:200],
                    host=self.host,
                    primitive=body.get("primitive", path),
                )

            try:
                return response.json()
            except Exception as exc:
                raise BrunhandProtocolError(
                    f"Non-JSON response from daemon at {path}: {exc}",
                    raw_status_code=response.status_code,
                    raw_body_preview=response.text[:200],
                    host=self.host,
                ) from exc

        # All retries exhausted
        if last_exc:
            raise last_exc
        raise BrunhandConnectionError("All retry attempts exhausted.", host=self.host)

    def _get(self, path: str) -> dict[str, Any]:
        """Execute an unauthenticated GET request (for health endpoint)."""
        from seidr_smidja.brunhand.exceptions import (
            BrunhandConnectionError,
            BrunhandProtocolError,
            BrunhandTimeoutError,
        )
        try:
            response = self._client.get(
                path,
                timeout=httpx.Timeout(self._base_timeout, connect=self._connect_timeout),
                headers={},  # No auth header for health
            )
            if response.status_code == 200:
                return response.json()
            raise BrunhandProtocolError(
                f"Unexpected HTTP {response.status_code} from health endpoint",
                raw_status_code=response.status_code,
                raw_body_preview=response.text[:200],
                host=self.host,
            )
        except httpx.ConnectError as exc:
            raise BrunhandConnectionError(
                f"Cannot connect to daemon at {self._base_url}: {exc}",
                cause="connect", host=self.host,
            ) from exc
        except (httpx.ReadTimeout, httpx.WriteTimeout) as exc:
            raise BrunhandTimeoutError(
                f"Health check timed out: {exc}", host=self.host,
            ) from exc
        except (BrunhandConnectionError, BrunhandProtocolError, BrunhandTimeoutError):
            raise
        except Exception as exc:
            raise BrunhandConnectionError(
                f"Unexpected error during health check: {exc}",
                cause="unknown", host=self.host,
            ) from exc

    def _build_envelope(
        self, session_id: str = "", agent_id: str = ""
    ) -> dict[str, Any]:
        """Build the standard request envelope fields."""
        return {
            "request_id": str(uuid.uuid4()),
            "session_id": session_id,
            "agent_id": agent_id or "BrunhandClient",
        }

    def _parse_error(self, payload: dict[str, Any]) -> Any:
        """Parse error detail from response payload."""
        err = payload.get("error")
        if err and isinstance(err, dict):
            from seidr_smidja.brunhand.models import BrunhandErrorDetail
            return BrunhandErrorDetail(**{k: v for k, v in err.items() if v is not None})
        return None

    def _raise_if_primitive_error(
        self,
        envelope: dict[str, Any],
        primitive: str,
        session_id: str = "",
    ) -> None:
        """Raise a typed exception if the envelope indicates failure.

        B-006: 'capabilities_error' error_type now raises BrunhandCapabilityError
        so agents can discriminate capability absence from primitive execution failure.
        """
        from seidr_smidja.brunhand.exceptions import (
            BrunhandCapabilityError,
            BrunhandPrimitiveError,
            VroidNotRunningError,
        )
        if not envelope.get("success", True):
            error = envelope.get("error") or {}
            if isinstance(error, dict):
                error_type = error.get("error_type", "")
                message = error.get("message", "Primitive failed.")
                vroid_running = error.get("vroid_running", True)

                # B-006: Structured capabilities_error → BrunhandCapabilityError
                if error_type == "capabilities_error":
                    raise BrunhandCapabilityError(
                        message=message,
                        primitive_name=primitive,
                        platform=error.get("platform", ""),
                        host=self.host,
                        request_id=envelope.get("request_id", ""),
                        session_id=session_id,
                    )

                if error_type == "VroidNotRunningError" or not vroid_running:
                    raise VroidNotRunningError(
                        message=message,
                        host=self.host,
                        primitive=primitive,
                        request_id=envelope.get("request_id", ""),
                        session_id=session_id,
                    )
                raise BrunhandPrimitiveError(
                    message=message,
                    vroid_running=vroid_running,
                    screen_accessible=error.get("screen_accessible", True),
                    permission_denied=error.get("permission_denied", False),
                    stack_summary=error.get("stack_summary"),
                    host=self.host,
                    primitive=primitive,
                    request_id=envelope.get("request_id", ""),
                    session_id=session_id,
                )

    # ── Public Methods ────────────────────────────────────────────────────────

    def health(self) -> HealthResult:
        """GET /v1/brunhand/health — daemon liveness probe. No auth required."""
        data = self._get("/v1/brunhand/health")
        return HealthResult(
            daemon_version=data.get("daemon_version", ""),
            os_name=data.get("os_name", ""),
            uptime_seconds=float(data.get("uptime_seconds", 0.0)),
            status=data.get("status", "ok"),
        )

    def capabilities(self, session_id: str = "", agent_id: str = "") -> CapabilitiesManifestResult:
        """GET /v1/brunhand/capabilities — platform capabilities manifest. Auth required."""
        # Capabilities is a GET endpoint but requires auth header
        # We use the POST helper pattern to leverage the auth header from the client
        from seidr_smidja.brunhand.exceptions import (
            BrunhandAuthError,
            BrunhandConnectionError,
            BrunhandProtocolError,
            BrunhandTimeoutError,
        )
        try:
            response = self._client.get(
                "/v1/brunhand/capabilities",
                timeout=httpx.Timeout(self._base_timeout, connect=self._connect_timeout),
            )
            if response.status_code == 401:
                raise BrunhandAuthError("Auth rejected for capabilities.", host=self.host)
            if response.status_code == 200:
                data = response.json()
                return CapabilitiesManifestResult(
                    daemon_version=data.get("daemon_version", ""),
                    os_name=data.get("os_name", ""),
                    os_version=data.get("os_version", ""),
                    screen_geometry=data.get("screen_geometry", []),
                    primitives=data.get("primitives", {}),
                    probed_at=data.get("probed_at", ""),
                )
            raise BrunhandProtocolError(
                f"Unexpected HTTP {response.status_code} from capabilities",
                raw_status_code=response.status_code,
                raw_body_preview=response.text[:200],
                host=self.host,
            )
        except (BrunhandAuthError, BrunhandProtocolError):
            raise
        except httpx.ConnectError as exc:
            raise BrunhandConnectionError(
                f"Cannot connect to daemon: {exc}", cause="connect", host=self.host,
            ) from exc
        except (httpx.ReadTimeout, httpx.WriteTimeout) as exc:
            raise BrunhandTimeoutError(
                f"Capabilities request timed out: {exc}", host=self.host,
            ) from exc

    def screenshot(
        self,
        region: dict[str, int] | None = None,
        session_id: str = "",
        agent_id: str = "",
    ) -> ScreenshotResult:
        """POST /v1/brunhand/screenshot — capture screen as PNG bytes."""
        body = {
            **self._build_envelope(session_id, agent_id),
            "region": region,
        }
        envelope = self._post("/v1/brunhand/screenshot", body)
        self._raise_if_primitive_error(envelope, "screenshot", session_id)
        payload = envelope.get("payload", {})
        png_b64 = payload.get("png_bytes_b64", "")
        png_bytes = base64.b64decode(png_b64) if png_b64 else b""
        return ScreenshotResult(
            success=envelope.get("success", True),
            png_bytes=png_bytes,
            width=payload.get("width", 0),
            height=payload.get("height", 0),
            captured_at=payload.get("captured_at", ""),
            monitor_index=payload.get("monitor_index", 0),
        )

    def click(
        self,
        x: int,
        y: int,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.0,
        modifiers: list[str] | None = None,
        session_id: str = "",
        agent_id: str = "",
    ) -> ClickResult:
        """POST /v1/brunhand/click."""
        body = {
            **self._build_envelope(session_id, agent_id),
            "x": x, "y": y, "button": button,
            "clicks": clicks, "interval": interval,
            "modifiers": modifiers or [],
        }
        envelope = self._post("/v1/brunhand/click", body)
        self._raise_if_primitive_error(envelope, "click", session_id)
        payload = envelope.get("payload", {})
        return ClickResult(
            success=envelope.get("success", True),
            x=payload.get("x", x), y=payload.get("y", y),
            button=payload.get("button", button),
            clicks_delivered=payload.get("clicks_delivered", clicks),
        )

    def move(
        self, x: int, y: int, duration: float = 0.25, tween: str = "linear",
        session_id: str = "", agent_id: str = "",
    ) -> MoveResult:
        """POST /v1/brunhand/move."""
        body = {**self._build_envelope(session_id, agent_id), "x": x, "y": y,
                "duration": duration, "tween": tween}
        envelope = self._post("/v1/brunhand/move", body)
        self._raise_if_primitive_error(envelope, "move", session_id)
        payload = envelope.get("payload", {})
        return MoveResult(success=envelope.get("success", True),
                          x=payload.get("x", x), y=payload.get("y", y))

    def drag(
        self, x1: int, y1: int, x2: int, y2: int,
        button: str = "left", duration: float = 0.5,
        session_id: str = "", agent_id: str = "",
    ) -> DragResult:
        """POST /v1/brunhand/drag."""
        body = {**self._build_envelope(session_id, agent_id),
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "button": button, "duration": duration}
        envelope = self._post("/v1/brunhand/drag", body)
        self._raise_if_primitive_error(envelope, "drag", session_id)
        payload = envelope.get("payload", {})
        from_pos = payload.get("from_pos", [x1, y1])
        to_pos = payload.get("to_pos", [x2, y2])
        return DragResult(
            success=envelope.get("success", True),
            from_pos=tuple(from_pos) if from_pos else (x1, y1),  # type: ignore[arg-type]
            to_pos=tuple(to_pos) if to_pos else (x2, y2),  # type: ignore[arg-type]
        )

    def scroll(
        self, x: int, y: int, clicks: int, direction: str = "down",
        session_id: str = "", agent_id: str = "",
    ) -> ScrollResult:
        """POST /v1/brunhand/scroll."""
        body = {**self._build_envelope(session_id, agent_id),
                "x": x, "y": y, "clicks": clicks, "direction": direction}
        envelope = self._post("/v1/brunhand/scroll", body)
        self._raise_if_primitive_error(envelope, "scroll", session_id)
        payload = envelope.get("payload", {})
        return ScrollResult(
            success=envelope.get("success", True),
            x=payload.get("x", x), y=payload.get("y", y),
            clicks=payload.get("clicks", clicks),
            direction=payload.get("direction", direction),
        )

    def type_text(
        self, text: str, interval: float = 0.05,
        session_id: str = "", agent_id: str = "",
    ) -> TypeResult:
        """POST /v1/brunhand/type."""
        body = {**self._build_envelope(session_id, agent_id),
                "text": text, "interval": interval}
        envelope = self._post("/v1/brunhand/type", body)
        self._raise_if_primitive_error(envelope, "type_text", session_id)
        payload = envelope.get("payload", {})
        return TypeResult(
            success=envelope.get("success", True),
            characters_typed=payload.get("characters_typed", len(text)),
        )

    def hotkey(
        self, keys: list[str],
        session_id: str = "", agent_id: str = "",
    ) -> HotkeyResult:
        """POST /v1/brunhand/hotkey."""
        body = {**self._build_envelope(session_id, agent_id), "keys": keys}
        envelope = self._post("/v1/brunhand/hotkey", body)
        self._raise_if_primitive_error(envelope, "hotkey", session_id)
        payload = envelope.get("payload", {})
        return HotkeyResult(
            success=envelope.get("success", True),
            keys=payload.get("keys", keys),
        )

    def find_window(
        self, title_pattern: str, exact: bool = False,
        session_id: str = "", agent_id: str = "",
    ) -> FindWindowResult:
        """POST /v1/brunhand/find_window."""
        body = {**self._build_envelope(session_id, agent_id),
                "title_pattern": title_pattern, "exact": exact}
        envelope = self._post("/v1/brunhand/find_window", body)
        self._raise_if_primitive_error(envelope, "find_window", session_id)
        payload = envelope.get("payload", {})
        windows = [
            WindowInfo(
                title=w.get("title", ""), left=w.get("left", 0), top=w.get("top", 0),
                width=w.get("width", 0), height=w.get("height", 0),
                is_foreground=w.get("is_foreground", False),
            )
            for w in payload.get("windows", [])
        ]
        return FindWindowResult(
            success=envelope.get("success", True),
            found=payload.get("found", bool(windows)),
            windows=windows,
        )

    def wait_for_window(
        self, title_pattern: str, timeout_seconds: float = 30.0,
        poll_interval_seconds: float = 0.5,
        session_id: str = "", agent_id: str = "",
    ) -> WaitForWindowResult:
        """POST /v1/brunhand/wait_for_window.

        Automatically extends httpx timeout to timeout_seconds + buffer
        (D-010 Cartographer tension #3).
        """
        body = {
            **self._build_envelope(session_id, agent_id),
            "title_pattern": title_pattern,
            "timeout_seconds": timeout_seconds,
            "poll_interval_seconds": poll_interval_seconds,
        }
        # Pass primitive_timeout so _post() applies the buffer
        envelope = self._post(
            "/v1/brunhand/wait_for_window", body,
            primitive_timeout=timeout_seconds,
        )
        # wait_for_window timeout is NOT an error — success=True, found=False
        payload = envelope.get("payload", {})
        window_data = payload.get("window")
        window = None
        if window_data:
            window = WindowInfo(
                title=window_data.get("title", ""),
                left=window_data.get("left", 0),
                top=window_data.get("top", 0),
                width=window_data.get("width", 0),
                height=window_data.get("height", 0),
                is_foreground=window_data.get("is_foreground", False),
            )
        return WaitForWindowResult(
            success=envelope.get("success", True),
            found=payload.get("found", False),
            elapsed_seconds=float(payload.get("elapsed_seconds", 0.0)),
            window=window,
        )

    def vroid_export_vrm(
        self, output_path: str, overwrite: bool = True,
        wait_timeout_seconds: float = 120.0,
        session_id: str = "", agent_id: str = "",
    ) -> VroidExportResult:
        """POST /v1/brunhand/vroid/export_vrm."""
        body = {
            **self._build_envelope(session_id, agent_id),
            "output_path": output_path, "overwrite": overwrite,
            "wait_timeout_seconds": wait_timeout_seconds,
        }
        envelope = self._post(
            "/v1/brunhand/vroid/export_vrm", body,
            primitive_timeout=wait_timeout_seconds,
        )
        self._raise_if_primitive_error(envelope, "vroid_export_vrm", session_id)
        payload = envelope.get("payload", {})
        return VroidExportResult(
            success=envelope.get("success", True),
            exported_path=payload.get("exported_path", output_path),
            elapsed_seconds=float(payload.get("elapsed_seconds", 0.0)),
            steps_executed=payload.get("steps_executed", []),
        )

    def vroid_save_project(
        self, session_id: str = "", agent_id: str = "",
    ) -> VroidSaveResult:
        """POST /v1/brunhand/vroid/save_project."""
        body = self._build_envelope(session_id, agent_id)
        envelope = self._post("/v1/brunhand/vroid/save_project", body)
        self._raise_if_primitive_error(envelope, "vroid_save_project", session_id)
        payload = envelope.get("payload", {})
        return VroidSaveResult(
            success=envelope.get("success", True),
            elapsed_seconds=float(payload.get("elapsed_seconds", 0.0)),
            steps_executed=payload.get("steps_executed", []),
        )

    def vroid_open_project(
        self, project_path: str, wait_timeout_seconds: float = 60.0,
        session_id: str = "", agent_id: str = "",
    ) -> VroidOpenResult:
        """POST /v1/brunhand/vroid/open_project."""
        body = {
            **self._build_envelope(session_id, agent_id),
            "project_path": project_path,
            "wait_timeout_seconds": wait_timeout_seconds,
        }
        envelope = self._post(
            "/v1/brunhand/vroid/open_project", body,
            primitive_timeout=wait_timeout_seconds,
        )
        self._raise_if_primitive_error(envelope, "vroid_open_project", session_id)
        payload = envelope.get("payload", {})
        return VroidOpenResult(
            success=envelope.get("success", True),
            opened_path=payload.get("opened_path", project_path),
            elapsed_seconds=float(payload.get("elapsed_seconds", 0.0)),
            steps_executed=payload.get("steps_executed", []),
        )
