"""AUDIT-005 regression tests — Loom emits its own Annáll events (D-005 Option B).

Verifies that:
  - load_spec() accepts annall and session_id parameters.
  - When both are provided, a 'loom.validated' event is logged by the Loom itself.
  - When annall=None or session_id=None, no logging occurs and no error is raised.
  - A recording mock confirms the event fires from the domain, not from Core.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from seidr_smidja.annall.adapters.null import NullAnnallAdapter
from seidr_smidja.annall.port import AnnallEvent
from seidr_smidja.loom.loader import load_spec


class TestLoomAnnallInjection:
    def test_load_spec_accepts_annall_parameters(
        self, minimal_spec_dict: dict[str, Any]
    ) -> None:
        """load_spec() must accept annall and session_id without raising."""
        null_annall = NullAnnallAdapter()
        session_id = null_annall.open_session({})
        # Must not raise
        spec = load_spec(minimal_spec_dict, annall=null_annall, session_id=session_id)
        assert spec.avatar_id == "test_avatar_v1"

    def test_load_spec_logs_validated_event_when_annall_provided(
        self, minimal_spec_dict: dict[str, Any]
    ) -> None:
        """When annall is injected, load_spec() logs a 'loom.validated' event
        from within the Loom domain itself."""
        # Use a recording mock to capture what was logged
        mock_annall = MagicMock()
        mock_annall.open_session.return_value = "test-session-loom"
        session_id = "test-session-loom"

        load_spec(minimal_spec_dict, annall=mock_annall, session_id=session_id)

        # Confirm log_event was called
        mock_annall.log_event.assert_called_once()
        call_args = mock_annall.log_event.call_args
        logged_session_id = call_args[0][0]
        logged_event: AnnallEvent = call_args[0][1]

        assert logged_session_id == session_id
        assert logged_event.event_type == "loom.validated"
        assert logged_event.payload.get("avatar_id") == "test_avatar_v1"

    def test_load_spec_no_annall_no_error(
        self, minimal_spec_dict: dict[str, Any]
    ) -> None:
        """load_spec() with no annall must work silently (no logging, no crash)."""
        spec = load_spec(minimal_spec_dict, annall=None, session_id=None)
        assert spec.avatar_id == "test_avatar_v1"

    def test_load_spec_annall_provided_but_no_session_id_skips_logging(
        self, minimal_spec_dict: dict[str, Any]
    ) -> None:
        """If annall is provided but session_id is None, logging is skipped silently."""
        mock_annall = MagicMock()
        # Must not raise
        spec = load_spec(minimal_spec_dict, annall=mock_annall, session_id=None)
        mock_annall.log_event.assert_not_called()
        assert spec is not None

    def test_load_spec_annall_failure_does_not_crash_loom(
        self, minimal_spec_dict: dict[str, Any]
    ) -> None:
        """If Annáll's log_event raises, load_spec() must still return the spec."""
        broken_annall = MagicMock()
        broken_annall.log_event.side_effect = RuntimeError("Annáll is on fire")
        # Must not raise — spec is returned despite Annáll failure
        spec = load_spec(minimal_spec_dict, annall=broken_annall, session_id="sess-x")
        assert spec is not None

    def test_load_spec_from_file_with_annall(
        self, minimal_spec_yaml_file: Path
    ) -> None:
        """load_spec() with a Path source also accepts annall parameters."""
        null_annall = NullAnnallAdapter()
        session_id = null_annall.open_session({})
        spec = load_spec(minimal_spec_yaml_file, annall=null_annall, session_id=session_id)
        assert spec.avatar_id == "test_avatar_v1"
