"""Tests for annall/factory.py (H-019 coverage) and H-008 write_jsonl_alongside."""
from __future__ import annotations

from pathlib import Path


class TestAnnallFactory:
    """H-019: Exercise all adapter construction paths in make_annall()."""

    def test_null_adapter_returned_when_configured(self, tmp_path: Path) -> None:
        from seidr_smidja.annall.adapters.null import NullAnnallAdapter
        from seidr_smidja.annall.factory import make_annall

        cfg = {"annall": {"adapter": "null"}}
        adapter = make_annall(cfg, tmp_path)
        assert isinstance(adapter, NullAnnallAdapter)

    def test_sqlite_adapter_returned_by_default(self, tmp_path: Path) -> None:
        from seidr_smidja.annall.adapters.sqlite import SQLiteAnnallAdapter
        from seidr_smidja.annall.factory import make_annall

        cfg = {"annall": {"adapter": "sqlite"}}
        adapter = make_annall(cfg, tmp_path)
        assert isinstance(adapter, SQLiteAnnallAdapter)

    def test_sqlite_adapter_is_default_when_no_adapter_key(self, tmp_path: Path) -> None:
        from seidr_smidja.annall.adapters.sqlite import SQLiteAnnallAdapter
        from seidr_smidja.annall.factory import make_annall

        cfg = {}  # No annall key at all
        adapter = make_annall(cfg, tmp_path)
        assert isinstance(adapter, SQLiteAnnallAdapter)

    def test_file_adapter_returned_when_configured(self, tmp_path: Path) -> None:
        from seidr_smidja.annall.adapters.file import FileAnnallAdapter
        from seidr_smidja.annall.factory import make_annall

        cfg = {
            "annall": {
                "adapter": "file",
                "file": {"jsonl_path": "data/annall/test.jsonl"},
            }
        }
        adapter = make_annall(cfg, tmp_path)
        assert isinstance(adapter, FileAnnallAdapter)

    def test_sqlite_db_path_resolved_relative_to_project_root(self, tmp_path: Path) -> None:
        from seidr_smidja.annall.adapters.sqlite import SQLiteAnnallAdapter
        from seidr_smidja.annall.factory import make_annall

        custom_path = "custom/path/annall.sqlite"
        cfg = {"annall": {"adapter": "sqlite", "sqlite": {"db_path": custom_path}}}
        adapter = make_annall(cfg, tmp_path)
        assert isinstance(adapter, SQLiteAnnallAdapter)
        # The db path must be under tmp_path (location-relative)
        assert str(tmp_path) in str(adapter._db_path)

    def test_file_jsonl_path_resolved_relative_to_project_root(self, tmp_path: Path) -> None:
        from seidr_smidja.annall.adapters.file import FileAnnallAdapter
        from seidr_smidja.annall.factory import make_annall

        custom_path = "logs/annall.jsonl"
        cfg = {"annall": {"adapter": "file", "file": {"jsonl_path": custom_path}}}
        adapter = make_annall(cfg, tmp_path)
        assert isinstance(adapter, FileAnnallAdapter)
        assert str(tmp_path) in str(adapter._path)

    def test_null_adapter_open_session_returns_string(self, tmp_path: Path) -> None:
        from seidr_smidja.annall.factory import make_annall

        adapter = make_annall({"annall": {"adapter": "null"}}, tmp_path)
        sid = adapter.open_session({"agent_id": "test"})
        assert isinstance(sid, str)
        assert len(sid) > 0

    def test_sqlite_adapter_functional(self, tmp_path: Path) -> None:
        """The SQLite adapter returned by factory must be functional."""
        from seidr_smidja.annall.factory import make_annall
        from seidr_smidja.annall.port import AnnallEvent, SessionOutcome

        adapter = make_annall({"annall": {"adapter": "sqlite"}}, tmp_path)
        sid = adapter.open_session({"agent_id": "factory_test"})
        adapter.log_event(sid, AnnallEvent.info("test.event", {"x": 1}))
        adapter.close_session(sid, SessionOutcome(success=True, summary="ok", elapsed_seconds=0.1))

        record = adapter.get_session(sid)
        assert record.summary.session_id == sid
        assert len(record.events) == 1


class TestWriteJsonlAlongside:
    """H-008: write_jsonl_alongside=true causes dual-write to SQLite + JSONL."""

    def test_composite_adapter_created_when_write_jsonl_alongside_true(
        self, tmp_path: Path
    ) -> None:
        from seidr_smidja.annall.factory import _CompositeAnnallAdapter, make_annall

        cfg = {
            "annall": {
                "adapter": "sqlite",
                "write_jsonl_alongside": True,
                "file": {"jsonl_path": "data/annall/alongside.jsonl"},
            }
        }
        adapter = make_annall(cfg, tmp_path)
        assert isinstance(adapter, _CompositeAnnallAdapter)

    def test_sqlite_adapter_returned_when_write_jsonl_alongside_false(
        self, tmp_path: Path
    ) -> None:
        from seidr_smidja.annall.adapters.sqlite import SQLiteAnnallAdapter
        from seidr_smidja.annall.factory import make_annall

        cfg = {
            "annall": {
                "adapter": "sqlite",
                "write_jsonl_alongside": False,
            }
        }
        adapter = make_annall(cfg, tmp_path)
        assert isinstance(adapter, SQLiteAnnallAdapter)

    def test_composite_adapter_writes_to_sqlite_and_jsonl(self, tmp_path: Path) -> None:
        """After log_event, the JSONL file must contain the event."""
        from seidr_smidja.annall.factory import make_annall
        from seidr_smidja.annall.port import AnnallEvent

        jsonl_path = tmp_path / "data/annall/trace.jsonl"
        cfg = {
            "annall": {
                "adapter": "sqlite",
                "write_jsonl_alongside": True,
                "file": {"jsonl_path": str(jsonl_path.relative_to(tmp_path))},
            }
        }
        adapter = make_annall(cfg, tmp_path)
        sid = adapter.open_session({"agent_id": "composite_test"})
        adapter.log_event(sid, AnnallEvent.info("composite.test", {"k": "v"}))

        # JSONL file must exist and contain event data
        assert jsonl_path.exists(), "JSONL trace file was not created"
        content = jsonl_path.read_text(encoding="utf-8")
        assert "composite.test" in content or sid in content

    def test_composite_adapter_get_session_uses_primary(self, tmp_path: Path) -> None:
        """get_session() must work on the composite adapter (delegates to SQLite primary)."""
        from seidr_smidja.annall.factory import make_annall
        from seidr_smidja.annall.port import AnnallEvent, SessionOutcome

        cfg = {
            "annall": {
                "adapter": "sqlite",
                "write_jsonl_alongside": True,
                "file": {"jsonl_path": "data/annall/trace.jsonl"},
            }
        }
        adapter = make_annall(cfg, tmp_path)
        sid = adapter.open_session({"agent_id": "get_session_test"})
        adapter.log_event(sid, AnnallEvent.info("test.ev", {}))
        adapter.close_session(sid, SessionOutcome(success=True, summary="ok", elapsed_seconds=0.2))

        record = adapter.get_session(sid)
        assert record.summary.session_id == sid


class TestSQLiteAdapterHardening:
    """H-010: bare raise preserves traceback; H-011: logger not print."""

    def test_raise_exc_replaced_with_bare_raise(self) -> None:
        """Verify the _connect() except clause uses bare raise (H-010)."""
        import inspect

        from seidr_smidja.annall.adapters.sqlite import SQLiteAnnallAdapter
        source = inspect.getsource(SQLiteAnnallAdapter._connect)
        # Must NOT contain "raise exc" (which replaces traceback)
        assert "raise exc" not in source, (
            "H-010 regression: 'raise exc' found in _connect() — should be bare 'raise'"
        )
        assert "raise" in source  # bare raise must be present

    def test_no_print_in_sqlite_adapter(self) -> None:
        """H-011: No print() calls in sqlite adapter source file."""
        import inspect

        from seidr_smidja.annall.adapters import sqlite as sqlite_mod

        source = inspect.getsource(sqlite_mod)
        # Filter out comment lines that mention print() (they're just documentation)
        non_comment_lines = [
            line for line in source.splitlines()
            if "print(" in line and not line.lstrip().startswith("#")
        ]
        assert len(non_comment_lines) == 0, (
            f"H-011 regression: print() in non-comment code lines of sqlite.py: "
            f"{non_comment_lines}"
        )

    def test_no_print_in_file_adapter(self) -> None:
        """H-011: No print() calls in file adapter source file."""
        import inspect

        from seidr_smidja.annall.adapters import file as file_mod

        source = inspect.getsource(file_mod)
        non_comment_lines = [
            line for line in source.splitlines()
            if "print(" in line and not line.lstrip().startswith("#")
        ]
        assert len(non_comment_lines) == 0, (
            f"H-011 regression: print() in non-comment code lines of file.py: "
            f"{non_comment_lines}"
        )
