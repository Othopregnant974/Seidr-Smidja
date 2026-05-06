"""seidr_smidja.brunhand.client.oracle_channel — Ljósbrú, the Oracle Eye Channel.

Ljósbrú (Light-Bridge) is the adapter that translates a daemon screenshot response
into an oracle_eye.register_external_render() call, routing the remote desktop image
through the Oracle Eye's vision pipeline.

This ensures agents see remote VRoid Studio screenshots through the SAME Oracle Eye
channel as headless Blender renders — one unified vision stream, no bifurcation.

INVARIANTS:
  - Ljósbrú never returns raw PNG bytes to Bridge callers as a vision substitute.
  - Ljósbrú never constructs its own render pipeline.
  - Ljósbrú only accesses oracle_eye.register_external_render() — never render().
  - Screenshots are NEVER logged to Annáll (only metadata: byte count, view name, host).

See: docs/features/brunhand/ARCHITECTURE.md §VII Vision Integration (Ljósbrú)
See: docs/features/brunhand/DATA_FLOW.md §XIII Ljósbrú Feeds the Oracle Eye
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LjosbruResult:
    """Result of a Ljósbrú feed operation."""

    view_name: str           # Canonical view name registered in Oracle Eye
    view_path: Any           # Path to written PNG (None if Oracle Eye not configured)
    byte_count: int          # Size of the PNG bytes (metadata only — not the bytes)
    oracle_available: bool   # False if oracle_eye_module was not injected


class Ljosbrú:
    """Ljósbrú — the Oracle Eye integration adapter.

    Translates Brúarhönd screenshot responses into oracle_eye.register_external_render()
    calls. Holds a reference to the injected oracle_eye module and session context.

    An instance lives inside a Tengslastig session for its lifetime.
    """

    def __init__(
        self,
        oracle_eye_module: Any,
        host: str = "",
        output_dir: Any = None,
        annall: Any = None,
        annall_session_id: str = "",
    ) -> None:
        """Initialise Ljósbrú.

        Args:
            oracle_eye_module: The oracle_eye module (or any object with
                               register_external_render). If None, vision
                               integration is disabled (feed() returns None).
            host:              Target daemon host for metadata.
            output_dir:        Optional directory to write PNG renders.
            annall:            Optional AnnallPort for telemetry.
            annall_session_id: Session ID for Annáll events.
        """
        self._oracle_eye = oracle_eye_module
        self.host = host
        self.output_dir = output_dir
        self._annall = annall
        self._annall_session_id = annall_session_id

    def feed(
        self,
        png_bytes: bytes,
        session_id: str = "",
        agent_id: str = "",
        captured_at: str = "",
        run_id: str | None = None,
    ) -> LjosbruResult | None:
        """Feed PNG bytes from a daemon screenshot response into the Oracle Eye.

        This is the primary Ljósbrú entry point. Called by BrunhandClient after
        receiving a screenshot response.

        Args:
            png_bytes:   Raw PNG bytes decoded from the daemon's base64 response.
            session_id:  Tengslastig session UUID (for the view name and metadata).
            agent_id:    Agent identity string for metadata.
            captured_at: ISO 8601 timestamp from the daemon (when the screenshot was taken).
            run_id:      Optional Mode C run_id for cross-Annáll correlation.

        Returns:
            LjosbruResult if Oracle Eye is available, None if not injected.

        INVARIANT: This method never raises — exceptions are caught and logged.
        """
        if self._oracle_eye is None:
            return None

        byte_count = len(png_bytes)
        timestamp = captured_at or time.strftime("%Y%m%d_%H%M%S", time.gmtime())
        # Canonical view name pattern: "live/<session_id>/<timestamp>"
        view = f"live/{session_id}/{timestamp}" if session_id else f"live/nosession/{timestamp}"

        try:
            # Build metadata for Oracle Eye
            # We import here to avoid a circular import at module level
            from seidr_smidja.oracle_eye.eye import ExternalRenderMetadata

            metadata = ExternalRenderMetadata(
                host=self.host,
                session_id=session_id,
                agent_id=agent_id,
                captured_at=captured_at or "",
                source="brunhand",
            )

            result = self._oracle_eye.register_external_render(
                source="brunhand",
                view=view,
                png_bytes=png_bytes,
                metadata=metadata,
                output_dir=self.output_dir,
                run_id=run_id,
                annall=self._annall,
                annall_session_id=self._annall_session_id,
            )

            canonical_view_name = result.view_name

            # Log to Annáll — metadata only, NEVER the raw bytes
            self._log_annall("brunhand.client.oracle.fed", {
                "source": "brunhand",
                "view": view,
                "view_name": canonical_view_name,
                "byte_count": byte_count,
                "host": self.host,
                "session_id": session_id,
                "run_id": run_id,
            })

            logger.debug(
                "Ljósbrú: fed screenshot to Oracle Eye — %s (%d bytes)",
                canonical_view_name,
                byte_count,
            )

            return LjosbruResult(
                view_name=canonical_view_name,
                view_path=result.view_path,
                byte_count=byte_count,
                oracle_available=True,
            )

        except Exception as exc:
            logger.warning("Ljósbrú: failed to feed Oracle Eye: %s", exc)
            self._log_annall("brunhand.client.oracle.feed_failed", {
                "error": str(exc),
                "host": self.host,
                "session_id": session_id,
                "byte_count": byte_count,
            })
            return LjosbruResult(
                view_name=f"brunhand/{view}",
                view_path=None,
                byte_count=byte_count,
                oracle_available=False,
            )

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


# Convenience function for use without a session object
def feed_screenshot(
    oracle_eye: Any,
    source: str,
    view: str,
    png_bytes: bytes,
    metadata: Any,
    annall: Any = None,
    annall_session_id: str = "",
) -> Any:
    """Feed a screenshot into Oracle Eye without a session context.

    This is a lower-level function for use by brunhand_dispatch() or tests.
    Use Ljósbrú.feed() inside a Tengslastig session for the standard path.
    """
    try:
        return oracle_eye.register_external_render(
            source=source,
            view=view,
            png_bytes=png_bytes,
            metadata=metadata,
            annall=annall,
            annall_session_id=annall_session_id,
        )
    except Exception as exc:
        logger.warning("feed_screenshot: oracle_eye.register_external_render failed: %s", exc)
        return None
