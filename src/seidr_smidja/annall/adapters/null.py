"""seidr_smidja.annall.adapters.null — NullAnnallAdapter

A no-op adapter that satisfies the AnnallPort protocol without writing
anything to disk. Used in:
    - Unit tests that do not need telemetry
    - CLI invocations with --no-telemetry flag

Never import this directly from domain code. Receive via DI from the factory.
"""
from __future__ import annotations

import uuid
from typing import Any

from seidr_smidja.annall.port import (
    AnnallEvent,
    AnnallNotFoundError,
    AnnallPort,
    SessionFilter,
    SessionID,
    SessionOutcome,
    SessionRecord,
    SessionSummary,
)


class NullAnnallAdapter:
    """Swallows all events silently. Satisfies AnnallPort via structural subtyping.

    query_sessions returns an empty list.
    get_session raises AnnallNotFoundError (no sessions were ever recorded).
    """

    def open_session(self, metadata: dict[str, Any]) -> SessionID:
        # Generate a real UUID so callers that store the session_id don't break
        return str(uuid.uuid4())

    def log_event(self, session_id: SessionID, event: AnnallEvent) -> None:
        # Silent no-op — intentional
        pass

    def close_session(self, session_id: SessionID, outcome: SessionOutcome) -> None:
        # Silent no-op — intentional
        pass

    def query_sessions(self, filter: SessionFilter) -> list[SessionSummary]:
        return []

    def get_session(self, session_id: SessionID) -> SessionRecord:
        raise AnnallNotFoundError(session_id)


# Verify structural conformance at import time (belt-and-suspenders)
_: AnnallPort = NullAnnallAdapter()  # type: ignore[assignment]
