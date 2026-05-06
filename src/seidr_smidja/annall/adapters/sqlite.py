"""seidr_smidja.annall.adapters.sqlite — SQLiteAnnallAdapter

The default concrete implementation of AnnallPort. Writes to a local SQLite
database at a configurable path (never hardcoded). Uses stdlib sqlite3 only.

Schema is created on first connection (schema-on-startup pattern).
WAL journal mode enables concurrent-read safety.

Never import this directly from domain code. Use AnnallPort via DI.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import sys
import uuid
from collections.abc import Generator
from contextlib import contextmanager
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

_SCHEMA_SQL = """\
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS sessions (
    session_id   TEXT PRIMARY KEY,
    agent_id     TEXT,
    bridge_type  TEXT,
    started_at   TEXT NOT NULL,
    ended_at     TEXT,
    success      INTEGER,
    summary      TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    event_type   TEXT NOT NULL,
    severity     TEXT NOT NULL DEFAULT 'info',
    payload_json TEXT NOT NULL DEFAULT '{}',
    timestamp    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at);
"""


class SQLiteAnnallAdapter:
    """SQLite-backed Annáll adapter. Single file, portable, zero-server.

    Args:
        db_path: Path to the SQLite database file. Parent directories are
                 created automatically if they do not exist.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Create the database file and apply schema on first connection."""
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.executescript(_SCHEMA_SQL)
                conn.commit()
        except sqlite3.Error as exc:
            # Log to stderr — we must never raise from Annáll infrastructure setup
            print(
                f"[annall.sqlite] WARNING: could not initialize database "
                f"at {self._db_path}: {exc}",
                file=sys.stderr,
            )

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Open a SQLite connection as a context manager."""
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except sqlite3.Error as exc:
            conn.rollback()
            raise exc
        finally:
            conn.close()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(tz=timezone.utc).isoformat()

    def open_session(self, metadata: dict[str, Any]) -> SessionID:
        """Open a new session. Never raises — logs to stderr on failure."""
        session_id = str(uuid.uuid4())
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO sessions (session_id, agent_id, bridge_type, started_at, metadata_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        metadata.get("agent_id"),
                        metadata.get("bridge_type"),
                        self._now_iso(),
                        json.dumps(metadata),
                    ),
                )
        except sqlite3.Error as exc:
            print(f"[annall.sqlite] WARNING: open_session failed: {exc}", file=sys.stderr)
        return session_id

    def log_event(self, session_id: SessionID, event: AnnallEvent) -> None:
        """Log an event. Never raises."""
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO events (session_id, event_type, severity, payload_json, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        event.event_type,
                        event.severity,
                        json.dumps(event.payload, default=str),
                        event.timestamp.isoformat(),
                    ),
                )
        except sqlite3.Error as exc:
            print(f"[annall.sqlite] WARNING: log_event failed: {exc}", file=sys.stderr)

    def close_session(self, session_id: SessionID, outcome: SessionOutcome) -> None:
        """Close a session. Never raises."""
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE sessions
                    SET ended_at=?, success=?, summary=?
                    WHERE session_id=?
                    """,
                    (
                        self._now_iso(),
                        1 if outcome.success else 0,
                        outcome.summary,
                        session_id,
                    ),
                )
        except sqlite3.Error as exc:
            print(f"[annall.sqlite] WARNING: close_session failed: {exc}", file=sys.stderr)

    def query_sessions(self, filter: SessionFilter) -> list[SessionSummary]:
        """Query sessions. May raise AnnallQueryError."""
        try:
            clauses: list[str] = []
            params: list[Any] = []

            if filter.agent_id is not None:
                clauses.append("agent_id = ?")
                params.append(filter.agent_id)
            if filter.since is not None:
                clauses.append("started_at >= ?")
                params.append(filter.since.isoformat())
            if filter.success is not None:
                clauses.append("success = ?")
                params.append(1 if filter.success else 0)

            where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
            limit = filter.limit if filter.limit is not None else 100
            sql = f"""
                SELECT session_id, agent_id, bridge_type, started_at, ended_at, success, summary
                FROM sessions
                {where}
                ORDER BY started_at DESC
                LIMIT ?
            """
            params.append(limit)

            with self._connect() as conn:
                rows = conn.execute(sql, params).fetchall()

            results: list[SessionSummary] = []
            for row in rows:
                results.append(
                    SessionSummary(
                        session_id=row["session_id"],
                        agent_id=row["agent_id"],
                        bridge_type=row["bridge_type"],
                        started_at=datetime.fromisoformat(row["started_at"]),
                        ended_at=(
                            datetime.fromisoformat(row["ended_at"])
                            if row["ended_at"]
                            else None
                        ),
                        success=(
                            bool(row["success"]) if row["success"] is not None else None
                        ),
                        summary=row["summary"],
                    )
                )
            return results

        except sqlite3.Error as exc:
            raise AnnallQueryError(
                f"SQLite query failed: {exc}", cause=exc
            ) from exc

    def get_session(self, session_id: SessionID) -> SessionRecord:
        """Return full session record. Raises AnnallNotFoundError or AnnallQueryError."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM sessions WHERE session_id=?", (session_id,)
                ).fetchone()
                if row is None:
                    raise AnnallNotFoundError(session_id)

                event_rows = conn.execute(
                    """
                    SELECT event_type, severity, payload_json, timestamp
                    FROM events WHERE session_id=?
                    ORDER BY id ASC
                    """,
                    (session_id,),
                ).fetchall()

            summary = SessionSummary(
                session_id=session_id,
                agent_id=row["agent_id"],
                bridge_type=row["bridge_type"],
                started_at=datetime.fromisoformat(row["started_at"]),
                ended_at=(
                    datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None
                ),
                success=(
                    bool(row["success"]) if row["success"] is not None else None
                ),
                summary=row["summary"],
            )
            events = [
                AnnallEvent(
                    event_type=er["event_type"],
                    payload=json.loads(er["payload_json"]),
                    severity=er["severity"],
                    timestamp=datetime.fromisoformat(er["timestamp"]),
                )
                for er in event_rows
            ]
            return SessionRecord(summary=summary, events=events)

        except AnnallNotFoundError:
            raise
        except sqlite3.Error as exc:
            raise AnnallQueryError(
                f"SQLite get_session failed: {exc}", cause=exc
            ) from exc
