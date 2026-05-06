"""seidr_smidja.annall.adapters.file — FileAnnallAdapter

Appends JSON-lines to a .jsonl file on disk. Provides an inspectable trace
alongside SQLite when config.annall.write_jsonl_alongside is True.

Each line in the file is a JSON object representing one AnnallEvent or one
session-lifecycle event (open / close).

Never import this directly from domain code. Receive via DI from the factory.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from seidr_smidja.annall.port import (
    AnnallEvent,
    AnnallNotFoundError,
    AnnallQueryError,
    SessionFilter,
    SessionID,
    SessionOutcome,
    SessionRecord,
    SessionSummary,
)

logger = logging.getLogger(__name__)


def _to_iso(dt: datetime) -> str:
    """Serialize a datetime to ISO 8601 string."""
    return dt.isoformat()


class FileAnnallAdapter:
    """Appends structured JSON-lines to a file. Satisfies AnnallPort.

    Thread-safety: Writes are buffered and flushed per call.
    Not suitable as a sole adapter for concurrent multi-process writes,
    but fine for a single-process seidr_smidja instance.
    """

    def __init__(self, jsonl_path: Path) -> None:
        self._path = jsonl_path
        # Ensure parent dir exists
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.warning("FileAnnallAdapter: cannot create dir %s: %s", self._path.parent, exc)

    def _append(self, record: dict[str, Any]) -> None:
        """Append one JSON record to the file. Never raises to callers."""
        try:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, default=str) + "\n")
        except OSError as exc:
            # H-011: logger not print — respects Python logging configuration
            logger.warning("annall.file: failed to write to %s: %s", self._path, exc)

    def open_session(self, metadata: dict[str, Any]) -> SessionID:
        session_id = str(uuid.uuid4())
        self._append(
            {
                "kind": "session_open",
                "session_id": session_id,
                "metadata": metadata,
                "timestamp": _to_iso(datetime.now(tz=timezone.utc)),
            }
        )
        return session_id

    def log_event(self, session_id: SessionID, event: AnnallEvent) -> None:
        self._append(
            {
                "kind": "event",
                "session_id": session_id,
                "event_type": event.event_type,
                "severity": event.severity,
                "payload": event.payload,
                "timestamp": _to_iso(event.timestamp),
            }
        )

    def close_session(self, session_id: SessionID, outcome: SessionOutcome) -> None:
        self._append(
            {
                "kind": "session_close",
                "session_id": session_id,
                "success": outcome.success,
                "summary": outcome.summary,
                "elapsed_seconds": outcome.elapsed_seconds,
                "timestamp": _to_iso(datetime.now(tz=timezone.utc)),
            }
        )

    def query_sessions(self, filter: SessionFilter) -> list[SessionSummary]:
        # File adapter provides minimal query support — reads all lines, filters in-memory.
        # For heavy query use, use the SQLite adapter.
        try:
            if not self._path.exists():
                return []
            summaries: dict[str, dict[str, Any]] = {}
            with self._path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if record.get("kind") == "session_open":
                        sid = record["session_id"]
                        summaries[sid] = record
                    elif record.get("kind") == "session_close":
                        sid = record["session_id"]
                        if sid in summaries:
                            summaries[sid]["close"] = record

            results: list[SessionSummary] = []
            for sid, rec in summaries.items():
                meta = rec.get("metadata", {})
                close = rec.get("close", {})
                started = datetime.fromisoformat(rec["timestamp"])
                ended = (
                    datetime.fromisoformat(close["timestamp"]) if close else None
                )
                success = close.get("success") if close else None
                # Apply filters
                if filter.since and started < filter.since:
                    continue
                if filter.success is not None and success != filter.success:
                    continue
                if filter.agent_id and meta.get("agent_id") != filter.agent_id:
                    continue
                results.append(
                    SessionSummary(
                        session_id=sid,
                        agent_id=meta.get("agent_id"),
                        bridge_type=meta.get("bridge_type"),
                        started_at=started,
                        ended_at=ended,
                        success=success,
                        summary=close.get("summary"),
                    )
                )
            # Sort newest-first
            results.sort(key=lambda s: s.started_at, reverse=True)
            limit = filter.limit or 100
            return results[:limit]

        except OSError as exc:
            raise AnnallQueryError(f"FileAnnallAdapter: read error: {exc}", cause=exc) from exc

    def get_session(self, session_id: SessionID) -> SessionRecord:
        try:
            if not self._path.exists():
                raise AnnallNotFoundError(session_id)
            open_rec: dict[str, Any] | None = None
            close_rec: dict[str, Any] | None = None
            events: list[AnnallEvent] = []
            with self._path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if record.get("session_id") != session_id:
                        continue
                    kind = record.get("kind")
                    if kind == "session_open":
                        open_rec = record
                    elif kind == "session_close":
                        close_rec = record
                    elif kind == "event":
                        events.append(
                            AnnallEvent(
                                event_type=record.get("event_type", "unknown"),
                                payload=record.get("payload", {}),
                                severity=record.get("severity", "info"),
                                timestamp=datetime.fromisoformat(record["timestamp"]),
                            )
                        )
            if open_rec is None:
                raise AnnallNotFoundError(session_id)
            meta = open_rec.get("metadata", {})
            started = datetime.fromisoformat(open_rec["timestamp"])
            ended = (
                datetime.fromisoformat(close_rec["timestamp"]) if close_rec else None
            )
            summary = SessionSummary(
                session_id=session_id,
                agent_id=meta.get("agent_id"),
                bridge_type=meta.get("bridge_type"),
                started_at=started,
                ended_at=ended,
                success=close_rec.get("success") if close_rec else None,
                summary=close_rec.get("summary") if close_rec else None,
            )
            return SessionRecord(summary=summary, events=events)
        except OSError as exc:
            raise AnnallQueryError(
                f"FileAnnallAdapter: read error: {exc}", cause=exc
            ) from exc
