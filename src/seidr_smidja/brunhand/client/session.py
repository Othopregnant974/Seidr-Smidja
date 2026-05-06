"""seidr_smidja.brunhand.client.session — Tengslastig, the Brúarhönd Session.

Tengslastig (Connection-State) is the session context manager that wraps a
BrunhandClient with:
  - A session-scoped UUID (session_id) for Annáll correlation.
  - A run_id for Mode C cross-Annáll correlation.
  - An agent_id string propagated to all primitive calls.
  - An optional oracle_eye reference injected at construction for Ljósbrú.
  - A rolling command log (last N calls) for audit and replay.
  - execute_and_see() convenience: run any primitive, auto-capture screenshot,
    auto-feed Ljósbrú.

INVARIANTS:
  - session_id is a fresh UUID4 on every __enter__ invocation.
  - Tengslastig is a context manager; use `with` or async-with (sync only in v0.1).
  - On __exit__, a session.closed Annáll event is logged regardless of exceptions.
  - Bearer token is never stored on Tengslastig — only held by the inner client.
  - execute_and_see() never raises for screenshot/Oracle failures: it swallows
    them and returns oracle_result=None if the secondary capture fails.

See: src/seidr_smidja/brunhand/client/INTERFACE.md §Tengslastig
See: docs/features/brunhand/ARCHITECTURE.md §V Session Layer (Tengslastig)
"""
from __future__ import annotations

import logging
import time
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class CommandRecord:
    """A record of a single primitive call within a Tengslastig session."""

    primitive: str
    args: dict[str, Any]
    success: bool
    elapsed_ms: float
    error_type: str = ""
    request_id: str = ""


@dataclass
class ExecuteAndSeeResult:
    """Result of execute_and_see(): primitive result + optional Oracle Eye result."""

    primitive_result: Any                  # The typed result from the primitive call
    screenshot_result: Any = None          # ScreenshotResult or None if capture failed
    oracle_result: Any = None              # LjosbruResult or None if Oracle not available
    primitive_success: bool = True
    screenshot_success: bool = False
    oracle_fed: bool = False


class Tengslastig:
    """Tengslastig — the Brúarhönd Session.

    A session context manager wrapping a BrunhandClient. Holds session-scoped
    state and provides the execute_and_see() convenience method.

    Usage:
        with Tengslastig(client, agent_id="my_agent") as session:
            result = session.screenshot()
            result2 = session.execute_and_see(session.client.click, 100, 200)

    Or via the factory:
        with brunhand.session(host="vroid-host", token="...") as session:
            ...
    """

    def __init__(
        self,
        client: Any,
        agent_id: str = "",
        oracle_eye: Any = None,
        annall: Any = None,
        annall_session_id: str = "",
        run_id: str | None = None,
        command_log_size: int = 200,
        output_dir: Any = None,
    ) -> None:
        """Initialise Tengslastig.

        Args:
            client:              A BrunhandClient instance (already open).
            agent_id:            Agent identity string (logged to Annáll and requests).
            oracle_eye:          Optional oracle_eye module for Ljósbrú integration.
            annall:              Optional AnnallPort for telemetry.
            annall_session_id:   External Annáll session ID (if none, opened internally).
            run_id:              Optional Mode C run_id for cross-Annáll correlation.
            command_log_size:    Max commands kept in the rolling log (default 200).
            output_dir:          Optional dir for Oracle Eye render output.
        """
        self._client = client
        self.agent_id = agent_id or "Tengslastig"
        self._oracle_eye = oracle_eye
        self._annall = annall
        self._annall_session_id = annall_session_id
        self.run_id = run_id
        self._command_log: deque[CommandRecord] = deque(maxlen=command_log_size)
        self._output_dir = output_dir

        # Session state — populated on __enter__
        self.session_id: str = ""
        self._session_start: float = 0.0
        self._own_annall_session = False  # True if we opened our own Annáll session

        # Ljósbrú instance — created on __enter__ when oracle_eye is available
        self._ljosbrú: Any = None

    # ── Context manager ───────────────────────────────────────────────────────

    def __enter__(self) -> Tengslastig:
        self.session_id = str(uuid.uuid4())
        self._session_start = time.monotonic()

        # Open Annáll session if we have a port but no external session ID
        if self._annall is not None and not self._annall_session_id:
            try:
                self._annall_session_id = self._annall.open_session(
                    self.session_id,
                    metadata={
                        "agent_id": self.agent_id,
                        "host": getattr(self._client, "host", ""),
                        "run_id": self.run_id,
                    },
                )
                self._own_annall_session = True
            except Exception as exc:
                logger.debug("Tengslastig: could not open Annáll session: %s", exc)

        # Initialise Ljósbrú if oracle_eye is available
        if self._oracle_eye is not None:
            try:
                from seidr_smidja.brunhand.client.oracle_channel import Ljosbrú
                self._ljosbrú = Ljosbrú(
                    oracle_eye_module=self._oracle_eye,
                    host=getattr(self._client, "host", ""),
                    output_dir=self._output_dir,
                    annall=self._annall,
                    annall_session_id=self._annall_session_id,
                )
            except Exception as exc:
                logger.debug("Tengslastig: could not create Ljósbrú: %s", exc)

        self._log_annall("brunhand.session.opened", {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "host": getattr(self._client, "host", ""),
            "run_id": self.run_id,
        })
        logger.debug("Tengslastig: session opened — %s", self.session_id)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        elapsed = time.monotonic() - self._session_start
        self._log_annall("brunhand.session.closed", {
            "session_id": self.session_id,
            "elapsed_seconds": elapsed,
            "commands_executed": len(self._command_log),
            "error_type": exc_type.__name__ if exc_type else None,
        })
        if self._own_annall_session and self._annall is not None:
            try:
                from seidr_smidja.annall.port import SessionOutcome
                outcome = SessionOutcome.FAILED if exc_type else SessionOutcome.SUCCESS
                self._annall.close_session(
                    self._annall_session_id,
                    outcome=outcome,
                    metadata={"elapsed_seconds": elapsed},
                )
            except Exception as exc:
                logger.debug("Tengslastig: could not close Annáll session: %s", exc)
        logger.debug(
            "Tengslastig: session closed — %s (%.2fs, %d commands)",
            self.session_id, elapsed, len(self._command_log),
        )
        # Do not suppress exceptions
        return None

    # ── Client passthrough properties ─────────────────────────────────────────

    @property
    def client(self) -> Any:
        """The underlying BrunhandClient."""
        return self._client

    @property
    def command_log(self) -> list[CommandRecord]:
        """The rolling command history (most recent last)."""
        return list(self._command_log)

    # ── Session-aware primitive wrappers ──────────────────────────────────────

    def _run_primitive(
        self,
        primitive_name: str,
        fn: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Run a primitive, inject session_id/agent_id, record in command log."""
        # Inject session context
        kwargs.setdefault("session_id", self.session_id)
        kwargs.setdefault("agent_id", self.agent_id)

        start = time.monotonic()
        record = CommandRecord(
            primitive=primitive_name,
            args={},  # Do not log args — may contain sensitive text
            success=False,
            elapsed_ms=0.0,
        )
        try:
            result = fn(*args, **kwargs)
            record.success = True
            if hasattr(result, "request_id"):
                record.request_id = getattr(result, "request_id", "")
            return result
        except Exception as exc:
            record.error_type = type(exc).__name__
            raise
        finally:
            record.elapsed_ms = (time.monotonic() - start) * 1000
            self._command_log.append(record)

    def screenshot(self, region: dict[str, int] | None = None) -> Any:
        """Session-aware screenshot. Returns ScreenshotResult."""
        return self._run_primitive("screenshot", self._client.screenshot, region=region)

    def click(
        self, x: int, y: int, button: str = "left", clicks: int = 1,
        interval: float = 0.0, modifiers: list[str] | None = None,
    ) -> Any:
        """Session-aware click. Returns ClickResult."""
        return self._run_primitive(
            "click", self._client.click,
            x=x, y=y, button=button, clicks=clicks,
            interval=interval, modifiers=modifiers,
        )

    def move(self, x: int, y: int, duration: float = 0.25, tween: str = "linear") -> Any:
        """Session-aware mouse move. Returns MoveResult."""
        return self._run_primitive(
            "move", self._client.move, x=x, y=y, duration=duration, tween=tween,
        )

    def drag(
        self, x1: int, y1: int, x2: int, y2: int,
        button: str = "left", duration: float = 0.5,
    ) -> Any:
        """Session-aware drag. Returns DragResult."""
        return self._run_primitive(
            "drag", self._client.drag,
            x1=x1, y1=y1, x2=x2, y2=y2, button=button, duration=duration,
        )

    def scroll(
        self, x: int, y: int, clicks: int, direction: str = "down",
    ) -> Any:
        """Session-aware scroll. Returns ScrollResult."""
        return self._run_primitive(
            "scroll", self._client.scroll,
            x=x, y=y, clicks=clicks, direction=direction,
        )

    def type_text(self, text: str, interval: float = 0.05) -> Any:
        """Session-aware text input. Returns TypeResult."""
        return self._run_primitive(
            "type_text", self._client.type_text, text=text, interval=interval,
        )

    def hotkey(self, keys: list[str]) -> Any:
        """Session-aware hotkey. Returns HotkeyResult."""
        return self._run_primitive("hotkey", self._client.hotkey, keys=keys)

    def find_window(self, title_pattern: str, exact: bool = False) -> Any:
        """Session-aware find_window. Returns FindWindowResult."""
        return self._run_primitive(
            "find_window", self._client.find_window,
            title_pattern=title_pattern, exact=exact,
        )

    def wait_for_window(
        self, title_pattern: str,
        timeout_seconds: float = 30.0,
        poll_interval_seconds: float = 0.5,
    ) -> Any:
        """Session-aware wait_for_window. Returns WaitForWindowResult."""
        return self._run_primitive(
            "wait_for_window", self._client.wait_for_window,
            title_pattern=title_pattern,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )

    def vroid_export_vrm(
        self, output_path: str, overwrite: bool = True,
        wait_timeout_seconds: float = 120.0,
    ) -> Any:
        """Session-aware VRM export. Returns VroidExportResult."""
        return self._run_primitive(
            "vroid_export_vrm", self._client.vroid_export_vrm,
            output_path=output_path, overwrite=overwrite,
            wait_timeout_seconds=wait_timeout_seconds,
        )

    def vroid_save_project(self) -> Any:
        """Session-aware VRoid save. Returns VroidSaveResult."""
        return self._run_primitive("vroid_save_project", self._client.vroid_save_project)

    def vroid_open_project(
        self, project_path: str, wait_timeout_seconds: float = 60.0,
    ) -> Any:
        """Session-aware VRoid open project. Returns VroidOpenResult."""
        return self._run_primitive(
            "vroid_open_project", self._client.vroid_open_project,
            project_path=project_path, wait_timeout_seconds=wait_timeout_seconds,
        )

    # ── execute_and_see ───────────────────────────────────────────────────────

    def execute_and_see(
        self,
        primitive_fn: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> ExecuteAndSeeResult:
        """Execute a primitive, then auto-capture a screenshot and feed Ljósbrú.

        This is the primary agent convenience method. Agents typically want to:
          1. Perform an action (click, hotkey, etc.)
          2. Immediately see what changed on screen.
          3. Have that screenshot visible in the Oracle Eye for vision analysis.

        execute_and_see() bundles all three steps. Screenshot and Oracle failures
        are NEVER propagated — they return None in the result so the agent can
        continue even if vision capture is temporarily unavailable.

        Args:
            primitive_fn: A bound method on this session or the inner client.
            *args, **kwargs: Arguments forwarded to primitive_fn.

        Returns:
            ExecuteAndSeeResult with the primitive result + optional vision data.

        INVARIANT: Only the primitive_fn error propagates. Screenshot/Oracle
                   failures are caught and logged, with oracle_result=None.
        """
        # Inject session context into kwargs if the fn accepts them
        kwargs.setdefault("session_id", self.session_id)
        kwargs.setdefault("agent_id", self.agent_id)

        # ── Step 1: Execute the primitive ─────────────────────────────────────
        primitive_name = getattr(primitive_fn, "__name__", "unknown")
        start = time.monotonic()
        try:
            primitive_result = primitive_fn(*args, **kwargs)
            primitive_success = True
        except Exception:
            record = CommandRecord(
                primitive=primitive_name,
                args={},
                success=False,
                elapsed_ms=(time.monotonic() - start) * 1000,
            )
            self._command_log.append(record)
            raise
        finally:
            pass

        record = CommandRecord(
            primitive=primitive_name,
            args={},
            success=True,
            elapsed_ms=(time.monotonic() - start) * 1000,
        )
        self._command_log.append(record)

        # ── Step 2: Capture screenshot (swallowing errors) ────────────────────
        screenshot_result = None
        screenshot_success = False
        try:
            screenshot_result = self._client.screenshot(
                session_id=self.session_id,
                agent_id=self.agent_id,
            )
            screenshot_success = getattr(screenshot_result, "success", True)
        except Exception as exc:
            logger.debug("execute_and_see: screenshot failed (non-fatal): %s", exc)

        # ── Step 3: Feed Ljósbrú (swallowing errors) ──────────────────────────
        oracle_result = None
        oracle_fed = False
        if screenshot_result is not None and self._ljosbrú is not None:
            png_bytes = getattr(screenshot_result, "png_bytes", b"")
            if png_bytes:
                try:
                    oracle_result = self._ljosbrú.feed(
                        png_bytes=png_bytes,
                        session_id=self.session_id,
                        agent_id=self.agent_id,
                        captured_at=getattr(screenshot_result, "captured_at", ""),
                        run_id=self.run_id,
                    )
                    oracle_fed = oracle_result is not None
                except Exception as exc:
                    logger.debug("execute_and_see: Ljósbrú feed failed (non-fatal): %s", exc)

        return ExecuteAndSeeResult(
            primitive_result=primitive_result,
            screenshot_result=screenshot_result,
            oracle_result=oracle_result,
            primitive_success=primitive_success,
            screenshot_success=screenshot_success,
            oracle_fed=oracle_fed,
        )

    # ── Internals ─────────────────────────────────────────────────────────────

    def _log_annall(self, event_type: str, payload: dict[str, Any]) -> None:
        """Log to Annáll, swallowing all errors."""
        if self._annall is None or not self._annall_session_id:
            return
        try:
            from seidr_smidja.annall.port import AnnallEvent
            self._annall.log_event(
                self._annall_session_id,
                AnnallEvent.info(event_type, payload),
            )
        except Exception:
            pass


# Alias for external use
BrunhandSession = Tengslastig
