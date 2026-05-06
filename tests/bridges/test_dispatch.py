"""Tests for seidr_smidja.bridges.core.dispatch — BuildRequest, BuildResponse, BuildError."""
from __future__ import annotations

import uuid
from pathlib import Path

from seidr_smidja.bridges.core.dispatch import BuildError, BuildRequest, BuildResponse


class TestBuildRequest:
    def test_defaults(self, tmp_path: Path) -> None:
        req = BuildRequest(
            spec_source={"spec_version": "1.0", "avatar_id": "x"},
            base_asset_id="vroid/sample_a",
            output_dir=tmp_path,
        )
        assert req.render_views is None
        assert req.compliance_targets is None
        assert req.session_metadata == {}
        # request_id is a UUID string
        uuid.UUID(req.request_id)  # raises if not valid UUID

    def test_request_id_is_unique(self, tmp_path: Path) -> None:
        r1 = BuildRequest(spec_source={}, base_asset_id="a", output_dir=tmp_path)
        r2 = BuildRequest(spec_source={}, base_asset_id="a", output_dir=tmp_path)
        assert r1.request_id != r2.request_id


class TestBuildError:
    def test_from_exception(self) -> None:
        exc = ValueError("Something went wrong")
        err = BuildError.from_exception("loom", exc)
        assert err.stage == "loom"
        assert err.error_type == "ValueError"
        assert "Something went wrong" in err.message
        assert err.detail == {}

    def test_manual_construction(self) -> None:
        err = BuildError(
            stage="gate",
            error_type="ComplianceFailure",
            message="Failed",
            detail={"violations": 3},
        )
        assert err.detail["violations"] == 3


class TestBuildResponse:
    def test_defaults(self) -> None:
        resp = BuildResponse(request_id="abc", success=True)
        assert resp.vrm_path is None
        assert resp.render_paths == {}
        assert resp.compliance_report is None
        assert resp.annall_session_id == ""
        assert resp.errors == []
        assert resp.elapsed_seconds == 0.0
