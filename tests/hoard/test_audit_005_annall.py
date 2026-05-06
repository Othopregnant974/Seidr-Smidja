"""AUDIT-005 regression tests — Hoard emits its own Annáll events (D-005 Option B).

Verifies that:
  - resolve() and list_assets() accept annall and session_id parameters.
  - When both are provided, 'hoard.resolved' / 'hoard.listed' events are logged
    by the Hoard domain itself.
  - When annall=None or session_id=None, no logging and no error.
  - A recording mock confirms the event fires from the domain, not from Core.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import yaml

from seidr_smidja.annall.adapters.null import NullAnnallAdapter
from seidr_smidja.annall.port import AnnallEvent
from seidr_smidja.hoard.local import LocalHoardAdapter


def _make_adapter(tmp_path: Path, sample_vrm: Path) -> LocalHoardAdapter:
    """Build a minimal LocalHoardAdapter backed by a temp catalog and one VRM."""
    bases_dir = tmp_path / "bases"
    bases_dir.mkdir()
    import shutil
    dest = bases_dir / "SampleA.vrm"
    shutil.copy(sample_vrm, dest)

    catalog_data = {
        "format_version": "1",
        "bases": [
            {
                "asset_id": "test/sample_a",
                "display_name": "Sample A",
                "filename": "SampleA.vrm",
                "vrm_version": "0.0",
                "tags": ["sample"],
                "license": "CC0-1.0",
                "cached": True,
                "file_size_bytes": dest.stat().st_size,
            }
        ],
    }
    catalog_path = tmp_path / "catalog.yaml"
    catalog_path.write_text(yaml.dump(catalog_data), encoding="utf-8")
    return LocalHoardAdapter(catalog_path=catalog_path, bases_dir=bases_dir)


class TestHoardResolveAnnallInjection:
    def test_resolve_accepts_annall_parameters(
        self, tmp_path: Path, sample_vrm_fixture: Path
    ) -> None:
        """resolve() must accept annall and session_id without raising."""
        adapter = _make_adapter(tmp_path, sample_vrm_fixture)
        null_annall = NullAnnallAdapter()
        session_id = null_annall.open_session({})
        # Must not raise
        result = adapter.resolve("test/sample_a", annall=null_annall, session_id=session_id)
        assert result.exists()

    def test_resolve_logs_hoard_resolved_event(
        self, tmp_path: Path, sample_vrm_fixture: Path
    ) -> None:
        """When annall is injected, resolve() logs a 'hoard.resolved' event
        from within the Hoard domain itself."""
        adapter = _make_adapter(tmp_path, sample_vrm_fixture)
        mock_annall = MagicMock()
        session_id = "test-session-hoard"

        adapter.resolve("test/sample_a", annall=mock_annall, session_id=session_id)

        mock_annall.log_event.assert_called_once()
        call_args = mock_annall.log_event.call_args
        logged_session_id = call_args[0][0]
        logged_event: AnnallEvent = call_args[0][1]

        assert logged_session_id == session_id
        assert logged_event.event_type == "hoard.resolved"
        assert logged_event.payload.get("asset_id") == "test/sample_a"

    def test_resolve_no_annall_no_error(
        self, tmp_path: Path, sample_vrm_fixture: Path
    ) -> None:
        """resolve() with no annall works silently."""
        adapter = _make_adapter(tmp_path, sample_vrm_fixture)
        result = adapter.resolve("test/sample_a", annall=None, session_id=None)
        assert result.exists()

    def test_resolve_annall_provided_but_no_session_id_skips_logging(
        self, tmp_path: Path, sample_vrm_fixture: Path
    ) -> None:
        """If annall is provided but session_id is None, logging is skipped silently."""
        adapter = _make_adapter(tmp_path, sample_vrm_fixture)
        mock_annall = MagicMock()
        result = adapter.resolve("test/sample_a", annall=mock_annall, session_id=None)
        mock_annall.log_event.assert_not_called()
        assert result.exists()

    def test_resolve_annall_failure_does_not_crash_hoard(
        self, tmp_path: Path, sample_vrm_fixture: Path
    ) -> None:
        """If Annáll's log_event raises, resolve() must still return the path."""
        adapter = _make_adapter(tmp_path, sample_vrm_fixture)
        broken_annall = MagicMock()
        broken_annall.log_event.side_effect = RuntimeError("Annáll failure")
        # Must not raise — path is returned despite Annáll failure
        result = adapter.resolve("test/sample_a", annall=broken_annall, session_id="x")
        assert result.exists()


class TestHoardListAssetsAnnallInjection:
    def test_list_assets_accepts_annall_parameters(
        self, tmp_path: Path, sample_vrm_fixture: Path
    ) -> None:
        """list_assets() must accept annall and session_id without raising."""
        adapter = _make_adapter(tmp_path, sample_vrm_fixture)
        null_annall = NullAnnallAdapter()
        session_id = null_annall.open_session({})
        results = adapter.list_assets(annall=null_annall, session_id=session_id)
        assert len(results) == 1

    def test_list_assets_logs_hoard_listed_event(
        self, tmp_path: Path, sample_vrm_fixture: Path
    ) -> None:
        """When annall is injected, list_assets() logs a 'hoard.listed' event."""
        adapter = _make_adapter(tmp_path, sample_vrm_fixture)
        mock_annall = MagicMock()
        session_id = "test-session-list"

        adapter.list_assets(annall=mock_annall, session_id=session_id)

        mock_annall.log_event.assert_called_once()
        logged_event: AnnallEvent = mock_annall.log_event.call_args[0][1]
        assert logged_event.event_type == "hoard.listed"
        assert logged_event.payload.get("count") == 1

    def test_list_assets_no_annall_no_error(
        self, tmp_path: Path, sample_vrm_fixture: Path
    ) -> None:
        """list_assets() with no annall works silently."""
        adapter = _make_adapter(tmp_path, sample_vrm_fixture)
        results = adapter.list_assets()
        assert isinstance(results, list)
