"""seidr_smidja.annall.factory — AnnallPort factory.

Constructs the correct adapter from configuration at startup.
This is the only place that imports concrete adapter classes.
Domain code must never import concrete adapters directly.
"""
from __future__ import annotations

import contextlib
import datetime
import logging
from pathlib import Path
from typing import Any

from seidr_smidja.annall.port import (
    AnnallEvent,
    AnnallPort,
    SessionFilter,
    SessionID,
    SessionOutcome,
    SessionRecord,
    SessionSummary,
)

logger = logging.getLogger(__name__)


class _CompositeAnnallAdapter:
    """H-008: Dual-write adapter that forwards all calls to two underlying adapters.

    Used when config.annall.write_jsonl_alongside = true (sqlite adapter selected):
    writes to both the SQLite adapter and a FileAnnallAdapter (JSONL trace file).
    Both adapters are driven with the SAME session_id so the JSONL file is a
    human-readable parallel trace of the SQLite records.
    """

    def __init__(self, primary: Any, secondary: Any) -> None:
        self._primary = primary
        self._secondary = secondary

    def open_session(self, metadata: dict[str, Any]) -> SessionID:
        sid: SessionID = self._primary.open_session(metadata)
        # Drive secondary with the same session_id for trace correlation.
        # FileAnnallAdapter generates its own UUID — replicate the primary's
        # session_id via _append so the JSONL trace stays correlated.
        with contextlib.suppress(Exception):
            ts = datetime.datetime.now(tz=datetime.UTC).isoformat()
            self._secondary._append(
                {
                    "kind": "session_open",
                    "session_id": sid,
                    "metadata": metadata,
                    "timestamp": ts,
                }
            )
        return sid

    def log_event(self, session_id: SessionID, event: AnnallEvent) -> None:
        self._primary.log_event(session_id, event)
        with contextlib.suppress(Exception):
            self._secondary.log_event(session_id, event)

    def close_session(self, session_id: SessionID, outcome: SessionOutcome) -> None:
        self._primary.close_session(session_id, outcome)
        with contextlib.suppress(Exception):
            self._secondary.close_session(session_id, outcome)

    def query_sessions(self, filter: SessionFilter) -> list[SessionSummary]:
        # Queries are always served by the primary (SQLite — authoritative).
        result: list[SessionSummary] = self._primary.query_sessions(filter)
        return result

    def get_session(self, session_id: SessionID) -> SessionRecord:
        record: SessionRecord = self._primary.get_session(session_id)
        return record


def make_annall(config: dict[str, Any], project_root: Path | None = None) -> AnnallPort:
    """Construct an AnnallPort from the given config dict.

    Args:
        config:       The resolved config dict from seidr_smidja.config.load_config().
        project_root: Optional explicit root for resolving relative paths in config.

    Returns:
        An AnnallPort-conforming adapter instance ready for use.

    Supported adapters (config key annall.adapter):
        "sqlite"  — SQLiteAnnallAdapter (default)
        "null"    — NullAnnallAdapter (no-op, useful for tests)
        "file"    — FileAnnallAdapter (JSON-lines)

    H-008: When adapter="sqlite" and annall.write_jsonl_alongside=true, returns a
    _CompositeAnnallAdapter that writes to both SQLite (primary) and a JSONL file
    (secondary trace). The JSONL file uses the same session_id as SQLite.
    """
    root = project_root or Path(".")
    annall_cfg = config.get("annall", {})
    adapter_name = annall_cfg.get("adapter", "sqlite")

    if adapter_name == "null":
        from seidr_smidja.annall.adapters.null import NullAnnallAdapter

        return NullAnnallAdapter()

    if adapter_name == "file":
        from seidr_smidja.annall.adapters.file import FileAnnallAdapter

        file_cfg = annall_cfg.get("file", {})
        jsonl_path_str = file_cfg.get("jsonl_path", "data/annall/runs.jsonl")
        jsonl_path = (root / Path(jsonl_path_str)).resolve()
        return FileAnnallAdapter(jsonl_path)

    # Default: sqlite
    from seidr_smidja.annall.adapters.sqlite import SQLiteAnnallAdapter

    sqlite_cfg = annall_cfg.get("sqlite", {})
    db_path_str = sqlite_cfg.get("db_path", "data/annall/runs.sqlite")
    db_path = (root / Path(db_path_str)).resolve()
    primary = SQLiteAnnallAdapter(db_path)

    # H-008: Honor the write_jsonl_alongside config key.
    # When true, wrap SQLite in a composite adapter that also writes a JSONL trace.
    write_alongside = annall_cfg.get("write_jsonl_alongside", False)
    if write_alongside:
        from seidr_smidja.annall.adapters.file import FileAnnallAdapter

        file_cfg = annall_cfg.get("file", {})
        jsonl_path_str = file_cfg.get("jsonl_path", "data/annall/runs.jsonl")
        jsonl_path = (root / Path(jsonl_path_str)).resolve()
        secondary = FileAnnallAdapter(jsonl_path)
        logger.debug(
            "Annáll: write_jsonl_alongside=true — dual-write to SQLite + %s", jsonl_path
        )
        return _CompositeAnnallAdapter(primary, secondary)

    return primary
