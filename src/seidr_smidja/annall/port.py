"""seidr_smidja.annall.port — AnnallPort Protocol and companion data models.

All forge domains interact with Annáll exclusively through this module.
No domain may import from annall.adapters.* directly.

Decision D-005: The AnnallPort instance is injected at startup, never a global.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

# ─── Type Aliases ────────────────────────────────────────────────────────────

SessionID = str  # Opaque string; typically a UUID


# ─── Data Structures ─────────────────────────────────────────────────────────


@dataclass
class AnnallEvent:
    """A single structured event logged to a session.

    Attributes:
        event_type:  A dot-namespaced string, e.g. "loom.validated", "forge.started".
        payload:     Event-specific detail dict. Schema varies by event_type.
        severity:    One of "debug", "info", "warning", "error".
        timestamp:   UTC timestamp of the event.
    """

    event_type: str
    payload: dict[str, Any]
    severity: str = "info"
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    @classmethod
    def info(cls, event_type: str, payload: dict[str, Any] | None = None) -> AnnallEvent:
        """Convenience constructor for info-severity events."""
        return cls(event_type=event_type, payload=payload or {}, severity="info")

    @classmethod
    def error(cls, event_type: str, payload: dict[str, Any] | None = None) -> AnnallEvent:
        """Convenience constructor for error-severity events."""
        return cls(event_type=event_type, payload=payload or {}, severity="error")

    @classmethod
    def warning(cls, event_type: str, payload: dict[str, Any] | None = None) -> AnnallEvent:
        """Convenience constructor for warning-severity events."""
        return cls(event_type=event_type, payload=payload or {}, severity="warning")


@dataclass
class SessionOutcome:
    """Final outcome of a forge session.

    Attributes:
        success:          Whether the session completed successfully.
        summary:          Human-readable one-line summary.
        elapsed_seconds:  Total wall-clock time for the session.
    """

    success: bool
    summary: str
    elapsed_seconds: float


@dataclass
class SessionFilter:
    """Filter parameters for query_sessions().

    All fields are optional. None = no filter on that dimension.
    """

    agent_id: str | None = None
    since: datetime | None = None
    success: bool | None = None
    limit: int | None = 100  # Default 100 most-recent sessions


@dataclass
class SessionSummary:
    """Summary record for a past session.

    Returned by query_sessions().
    """

    session_id: SessionID
    agent_id: str | None
    bridge_type: str | None
    started_at: datetime
    ended_at: datetime | None
    success: bool | None
    summary: str | None


@dataclass
class SessionRecord:
    """Full record for a single session including all logged events.

    Returned by get_session().
    """

    summary: SessionSummary
    events: list[AnnallEvent]


# ─── Exceptions ──────────────────────────────────────────────────────────────


class AnnallQueryError(RuntimeError):
    """Raised when a query operation fails (storage unavailable, etc.)."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause


class AnnallNotFoundError(LookupError):
    """Raised when get_session() is called with an unknown session_id."""

    def __init__(self, session_id: SessionID) -> None:
        super().__init__(f"Session not found: {session_id}")
        self.session_id = session_id


# ─── AnnallPort Protocol ──────────────────────────────────────────────────────


@runtime_checkable
class AnnallPort(Protocol):
    """The abstract interface for Annáll. Every adapter implements these five methods.

    Invariants (from INTERFACE.md):
        - open_session, log_event, close_session NEVER raise to callers.
        - query_sessions and get_session MAY raise AnnallQueryError / AnnallNotFoundError.
        - No forge operation may fail because the record-keeper stumbled.
    """

    def open_session(self, metadata: dict[str, Any]) -> SessionID:
        """Open a new session and return its ID."""
        ...

    def log_event(self, session_id: SessionID, event: AnnallEvent) -> None:
        """Append a structured event to an open session. Never raises."""
        ...

    def close_session(self, session_id: SessionID, outcome: SessionOutcome) -> None:
        """Close the session and record the final outcome. Never raises."""
        ...

    def query_sessions(self, filter: SessionFilter) -> list[SessionSummary]:
        """Return session summaries matching the filter. May raise AnnallQueryError."""
        ...

    def get_session(self, session_id: SessionID) -> SessionRecord:
        """Return the full record for a session. May raise AnnallNotFoundError."""
        ...
