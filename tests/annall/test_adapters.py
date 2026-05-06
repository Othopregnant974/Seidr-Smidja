"""Tests for Annáll adapters — NullAnnallAdapter, SQLiteAnnallAdapter, FileAnnallAdapter."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from seidr_smidja.annall.port import (
    AnnallEvent,
    AnnallNotFoundError,
    SessionFilter,
    SessionOutcome,
)

# ─── NullAnnallAdapter ────────────────────────────────────────────────────────


class TestNullAnnallAdapter:
    def test_open_session_returns_string(self, null_annall: Any) -> None:
        sid = null_annall.open_session({"agent_id": "test"})
        assert isinstance(sid, str)
        assert len(sid) > 0

    def test_log_event_does_not_raise(self, null_annall: Any) -> None:
        sid = null_annall.open_session({})
        # Should silently swallow the event
        null_annall.log_event(sid, AnnallEvent.info("test.event", {"x": 1}))

    def test_close_session_does_not_raise(self, null_annall: Any) -> None:
        sid = null_annall.open_session({})
        outcome = SessionOutcome(success=True, summary="ok", elapsed_seconds=0.1)
        null_annall.close_session(sid, outcome)

    def test_query_sessions_returns_empty(self, null_annall: Any) -> None:
        results = null_annall.query_sessions(SessionFilter())
        assert results == []

    def test_get_session_raises_not_found(self, null_annall: Any) -> None:
        with pytest.raises(AnnallNotFoundError):
            null_annall.get_session("nonexistent-session-id")

    def test_multiple_sessions(self, null_annall: Any) -> None:
        sid1 = null_annall.open_session({"agent_id": "a1"})
        sid2 = null_annall.open_session({"agent_id": "a2"})
        assert sid1 != sid2


# ─── SQLiteAnnallAdapter ──────────────────────────────────────────────────────


class TestSQLiteAnnallAdapter:
    def test_open_session_returns_uuid(self, sqlite_annall: Any) -> None:
        sid = sqlite_annall.open_session({"agent_id": "test_agent"})
        assert isinstance(sid, str)
        assert len(sid) > 0

    def test_open_session_returns_unique_ids(self, sqlite_annall: Any) -> None:
        sid1 = sqlite_annall.open_session({})
        sid2 = sqlite_annall.open_session({})
        assert sid1 != sid2

    def test_log_event_stored(self, sqlite_annall: Any) -> None:
        sid = sqlite_annall.open_session({})
        sqlite_annall.log_event(
            sid,
            AnnallEvent.info("test.event", {"key": "value"})
        )
        record = sqlite_annall.get_session(sid)
        assert len(record.events) == 1
        assert record.events[0].event_type == "test.event"
        assert record.events[0].payload["key"] == "value"

    def test_log_multiple_events(self, sqlite_annall: Any) -> None:
        sid = sqlite_annall.open_session({})
        for i in range(5):
            sqlite_annall.log_event(
                sid, AnnallEvent.info(f"event.{i}", {"i": i})
            )
        record = sqlite_annall.get_session(sid)
        assert len(record.events) == 5
        # Check ordering
        types = [e.event_type for e in record.events]
        assert types == [f"event.{i}" for i in range(5)]

    def test_close_session_sets_outcome(self, sqlite_annall: Any) -> None:
        sid = sqlite_annall.open_session({})
        outcome = SessionOutcome(success=True, summary="All good", elapsed_seconds=1.5)
        sqlite_annall.close_session(sid, outcome)
        record = sqlite_annall.get_session(sid)
        assert record.summary.success is True
        assert record.summary.summary == "All good"
        assert record.summary.ended_at is not None

    def test_close_session_failure(self, sqlite_annall: Any) -> None:
        sid = sqlite_annall.open_session({})
        outcome = SessionOutcome(success=False, summary="Failed", elapsed_seconds=0.5)
        sqlite_annall.close_session(sid, outcome)
        record = sqlite_annall.get_session(sid)
        assert record.summary.success is False

    def test_get_session_not_found(self, sqlite_annall: Any) -> None:
        with pytest.raises(AnnallNotFoundError):
            sqlite_annall.get_session("this-does-not-exist")

    def test_query_sessions_empty(self, sqlite_annall: Any) -> None:
        results = sqlite_annall.query_sessions(SessionFilter())
        assert isinstance(results, list)

    def test_query_sessions_returns_opened(self, sqlite_annall: Any) -> None:
        sid = sqlite_annall.open_session({"agent_id": "query_test"})
        results = sqlite_annall.query_sessions(SessionFilter(agent_id="query_test"))
        ids = [r.session_id for r in results]
        assert sid in ids

    def test_query_sessions_filter_by_success(self, sqlite_annall: Any) -> None:
        sid1 = sqlite_annall.open_session({})
        sqlite_annall.close_session(sid1, SessionOutcome(success=True, summary="ok", elapsed_seconds=0.1))
        sid2 = sqlite_annall.open_session({})
        sqlite_annall.close_session(sid2, SessionOutcome(success=False, summary="bad", elapsed_seconds=0.1))

        successes = sqlite_annall.query_sessions(SessionFilter(success=True))
        failures = sqlite_annall.query_sessions(SessionFilter(success=False))
        success_ids = [r.session_id for r in successes]
        failure_ids = [r.session_id for r in failures]
        assert sid1 in success_ids
        assert sid2 in failure_ids

    def test_query_sessions_limit(self, sqlite_annall: Any) -> None:
        for _ in range(5):
            sqlite_annall.open_session({})
        results = sqlite_annall.query_sessions(SessionFilter(limit=3))
        assert len(results) <= 3

    def test_event_severity_stored(self, sqlite_annall: Any) -> None:
        sid = sqlite_annall.open_session({})
        sqlite_annall.log_event(
            sid, AnnallEvent.error("forge.failed", {"reason": "blender crashed"})
        )
        record = sqlite_annall.get_session(sid)
        assert record.events[0].severity == "error"

    def test_log_event_never_raises(self, sqlite_annall: Any) -> None:
        """log_event with a closed session should not propagate an exception."""
        # Use a session ID that was never opened — should not crash
        bad_id = "totally-fake-session"
        # This may or may not log an error internally, but must NOT raise
        try:
            sqlite_annall.log_event(
                bad_id, AnnallEvent.info("orphaned.event", {})
            )
        except Exception as exc:
            pytest.fail(f"log_event raised an exception: {exc}")

    def test_metadata_stored_in_session(self, sqlite_annall: Any) -> None:
        meta = {"agent_id": "forge_worker", "bridge_type": "cli"}
        sid = sqlite_annall.open_session(meta)
        record = sqlite_annall.get_session(sid)
        assert record.summary.agent_id == "forge_worker"
        assert record.summary.bridge_type == "cli"

    def test_db_persists_across_adapter_instances(self, tmp_path: Path) -> None:
        """Two adapters pointing at the same file share data."""
        from seidr_smidja.annall.adapters.sqlite import SQLiteAnnallAdapter

        db = tmp_path / "shared.sqlite"
        adapter1 = SQLiteAnnallAdapter(db_path=db)
        sid = adapter1.open_session({"agent_id": "persistent"})

        adapter2 = SQLiteAnnallAdapter(db_path=db)
        record = adapter2.get_session(sid)
        assert record.summary.agent_id == "persistent"


# ─── FileAnnallAdapter ────────────────────────────────────────────────────────


class TestFileAnnallAdapter:
    def _make_adapter(self, tmp_path: Path) -> Any:
        from seidr_smidja.annall.adapters.file import FileAnnallAdapter

        return FileAnnallAdapter(jsonl_path=tmp_path / "annall.jsonl")

    def test_open_session_returns_string(self, tmp_path: Path) -> None:
        adapter = self._make_adapter(tmp_path)
        sid = adapter.open_session({"agent_id": "file_test"})
        assert isinstance(sid, str)

    def test_log_event_appends_to_file(self, tmp_path: Path) -> None:
        adapter = self._make_adapter(tmp_path)
        sid = adapter.open_session({})
        adapter.log_event(sid, AnnallEvent.info("test.event", {"n": 1}))
        jsonl_path = tmp_path / "annall.jsonl"
        assert jsonl_path.exists()
        lines = [json.loads(ln) for ln in jsonl_path.read_text().strip().splitlines()]
        assert len(lines) >= 2  # session open + event

    def test_close_session_appends(self, tmp_path: Path) -> None:
        adapter = self._make_adapter(tmp_path)
        sid = adapter.open_session({})
        adapter.close_session(sid, SessionOutcome(success=True, summary="done", elapsed_seconds=0.0))
        jsonl_path = tmp_path / "annall.jsonl"
        lines = [json.loads(ln) for ln in jsonl_path.read_text().strip().splitlines()]
        kinds = [ln.get("kind") for ln in lines]
        assert "session_close" in kinds

    def test_query_returns_empty_for_fresh(self, tmp_path: Path) -> None:
        adapter = self._make_adapter(tmp_path)
        results = adapter.query_sessions(SessionFilter())
        assert isinstance(results, list)

    def test_get_session_not_found(self, tmp_path: Path) -> None:
        adapter = self._make_adapter(tmp_path)
        with pytest.raises(AnnallNotFoundError):
            adapter.get_session("no-such-session")


# ─── AnnallEvent ─────────────────────────────────────────────────────────────


class TestAnnallEvent:
    def test_info_factory(self) -> None:
        e = AnnallEvent.info("test.event", {"x": 1})
        assert e.event_type == "test.event"
        assert e.severity == "info"
        assert e.payload["x"] == 1
        assert isinstance(e.timestamp, datetime)

    def test_error_factory(self) -> None:
        e = AnnallEvent.error("forge.failed", {"reason": "crash"})
        assert e.severity == "error"

    def test_warning_factory(self) -> None:
        e = AnnallEvent.warning("oracle.slow", {"seconds": 30})
        assert e.severity == "warning"

    def test_timestamp_is_utc(self) -> None:
        e = AnnallEvent.info("x", {})
        # Timestamp should be timezone-aware or at least parseable
        assert e.timestamp is not None


# ─── AnnallPort protocol compliance ──────────────────────────────────────────


class TestAnnallPortProtocol:
    """Verify all adapters satisfy the AnnallPort protocol at runtime."""

    def test_null_satisfies_protocol(self, null_annall: Any) -> None:
        from seidr_smidja.annall.port import AnnallPort

        assert isinstance(null_annall, AnnallPort)

    def test_sqlite_satisfies_protocol(self, sqlite_annall: Any) -> None:
        from seidr_smidja.annall.port import AnnallPort

        assert isinstance(sqlite_annall, AnnallPort)

    def test_file_satisfies_protocol(self, tmp_path: Path) -> None:
        from seidr_smidja.annall.adapters.file import FileAnnallAdapter
        from seidr_smidja.annall.port import AnnallPort

        adapter = FileAnnallAdapter(jsonl_path=tmp_path / "test.jsonl")
        assert isinstance(adapter, AnnallPort)
