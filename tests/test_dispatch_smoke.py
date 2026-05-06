"""Whole-stack dispatch smoke test.

Uses a mock Forge (returns a fake VRM path from the tmp_hoard fixture)
and a mock Oracle Eye (returns empty render_paths, success=True).
Verifies that the dispatch() wiring is correct end-to-end without Blender.

All Gate checks run against the real sample_vrm_fixture. All Annáll writes
go to the real SQLiteAnnallAdapter backed by a temp db.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from seidr_smidja.bridges.core.dispatch import BuildRequest, BuildResponse, dispatch

# Real rules dir for Gate (relative to repo root)
_REPO_ROOT = Path(__file__).parent.parent
_RULES_DIR = _REPO_ROOT / "data" / "gate"


def _make_mock_forge_result(vrm_path: Path) -> Any:
    """Return a mock ForgeResult that looks like a successful Blender run."""
    result = MagicMock()
    result.success = True
    result.vrm_path = vrm_path
    result.exit_code = 0
    result.stderr_capture = ""
    result.stdout_capture = ""
    result.elapsed_seconds = 0.1
    return result


def _make_mock_render_result() -> Any:
    """Return a mock RenderResult with no renders — soft success."""
    result = MagicMock()
    result.success = True
    result.render_paths = {}
    result.errors = []
    result.elapsed_seconds = 0.1
    return result


class TestDispatchSmokeSuccess:
    def test_full_pipeline_returns_success(
        self,
        minimal_spec_dict: dict[str, Any],
        tmp_hoard: Path,
        sample_vrm_fixture: Path,
        sqlite_annall: Any,
        tmp_path: Path,
    ) -> None:
        """Happy path: spec→hoard→(mock forge)→(mock oracle)→gate → success."""
        # Build a mock hoard that resolves to the sample VRM
        from seidr_smidja.hoard.local import LocalHoardAdapter

        hoard = LocalHoardAdapter(
            catalog_path=tmp_hoard / "data" / "hoard" / "catalog.yaml",
            bases_dir=tmp_hoard / "data" / "hoard" / "bases",
        )

        request = BuildRequest(
            spec_source=minimal_spec_dict,
            base_asset_id="vroid/sample_a",
            output_dir=tmp_path / "output",
            compliance_targets=["VRCHAT"],
            session_metadata={"agent_id": "smoke_test", "bridge_type": "test"},
        )

        # Patch forge.runner.build to return a successful ForgeResult pointing at sample VRM
        with patch("seidr_smidja.forge.runner.build") as mock_forge:
            mock_forge.return_value = _make_mock_forge_result(sample_vrm_fixture)

            # Patch oracle_eye.eye.render to return a soft-success RenderResult
            with patch("seidr_smidja.oracle_eye.eye.render") as mock_render:
                mock_render.return_value = _make_mock_render_result()

                config = {
                    "gate": {
                        "rules_dir": str(_RULES_DIR),
                        "vrchat_tier_target": "Good",
                    }
                }

                response = dispatch(
                    request=request,
                    annall=sqlite_annall,
                    hoard=hoard,
                    config=config,
                )

        assert isinstance(response, BuildResponse)
        assert response.request_id == request.request_id
        assert response.annall_session_id != ""
        assert response.vrm_path == sample_vrm_fixture
        assert response.elapsed_seconds >= 0.0

    def test_annall_session_is_closed(
        self,
        minimal_spec_dict: dict[str, Any],
        tmp_hoard: Path,
        sample_vrm_fixture: Path,
        sqlite_annall: Any,
        tmp_path: Path,
    ) -> None:
        """After dispatch(), the Annáll session is closed with an outcome."""
        from seidr_smidja.hoard.local import LocalHoardAdapter

        hoard = LocalHoardAdapter(
            catalog_path=tmp_hoard / "data" / "hoard" / "catalog.yaml",
            bases_dir=tmp_hoard / "data" / "hoard" / "bases",
        )
        request = BuildRequest(
            spec_source=minimal_spec_dict,
            base_asset_id="vroid/sample_a",
            output_dir=tmp_path / "output",
        )

        with patch("seidr_smidja.forge.runner.build") as mock_forge:
            mock_forge.return_value = _make_mock_forge_result(sample_vrm_fixture)
            with patch("seidr_smidja.oracle_eye.eye.render") as mock_render:
                mock_render.return_value = _make_mock_render_result()
                response = dispatch(request=request, annall=sqlite_annall, hoard=hoard)

        # Session should be closed and retrievable
        record = sqlite_annall.get_session(response.annall_session_id)
        assert record.summary.ended_at is not None

    def test_response_always_returned_never_raises(
        self,
        minimal_spec_dict: dict[str, Any],
        tmp_hoard: Path,
        sqlite_annall: Any,
        tmp_path: Path,
    ) -> None:
        """Even when Forge raises an exception, dispatch() returns a BuildResponse."""
        from seidr_smidja.hoard.local import LocalHoardAdapter

        hoard = LocalHoardAdapter(
            catalog_path=tmp_hoard / "data" / "hoard" / "catalog.yaml",
            bases_dir=tmp_hoard / "data" / "hoard" / "bases",
        )
        request = BuildRequest(
            spec_source=minimal_spec_dict,
            base_asset_id="vroid/sample_a",
            output_dir=tmp_path / "output",
        )

        with patch("seidr_smidja.forge.runner.build") as mock_forge:
            mock_forge.side_effect = RuntimeError("Blender exploded")

            response = dispatch(request=request, annall=sqlite_annall, hoard=hoard)

        assert isinstance(response, BuildResponse)
        assert response.success is False
        forge_errors = [e for e in response.errors if e.stage == "forge"]
        assert len(forge_errors) > 0
        assert "Blender exploded" in forge_errors[0].message


class TestDispatchSmokeFailures:
    def test_loom_failure_returns_early(
        self, sqlite_annall: Any, tmp_path: Path
    ) -> None:
        """Invalid spec causes Loom stage failure — hoard and forge are never called."""
        bad_spec = {"spec_version": "99.9"}  # completely invalid

        request = BuildRequest(
            spec_source=bad_spec,
            base_asset_id="vroid/sample_a",
            output_dir=tmp_path / "output",
        )

        with patch("seidr_smidja.hoard.local.LocalHoardAdapter.resolve") as mock_resolve:
            response = dispatch(request=request, annall=sqlite_annall)

        assert response.success is False
        loom_errors = [e for e in response.errors if e.stage == "loom"]
        assert len(loom_errors) > 0
        # Hoard was never called
        mock_resolve.assert_not_called()

    def test_hoard_failure_returns_early(
        self,
        minimal_spec_dict: dict[str, Any],
        sqlite_annall: Any,
        tmp_path: Path,
    ) -> None:
        """Missing asset causes Hoard stage failure — forge is never called."""
        from seidr_smidja.hoard.exceptions import AssetNotFoundError

        mock_hoard = MagicMock()
        mock_hoard.resolve.side_effect = AssetNotFoundError(
            asset_id="vroid/sample_a", message="Not cached"
        )

        request = BuildRequest(
            spec_source=minimal_spec_dict,
            base_asset_id="vroid/sample_a",
            output_dir=tmp_path / "output",
        )

        with patch("seidr_smidja.forge.runner.build") as mock_forge:
            response = dispatch(request=request, annall=sqlite_annall, hoard=mock_hoard)

        assert response.success is False
        hoard_errors = [e for e in response.errors if e.stage == "hoard"]
        assert len(hoard_errors) > 0
        mock_forge.assert_not_called()

    def test_oracle_eye_failure_is_soft(
        self,
        minimal_spec_dict: dict[str, Any],
        tmp_hoard: Path,
        sample_vrm_fixture: Path,
        sqlite_annall: Any,
        tmp_path: Path,
    ) -> None:
        """Oracle Eye failure is soft — VRM is still returned, gate still runs."""
        from seidr_smidja.hoard.local import LocalHoardAdapter

        hoard = LocalHoardAdapter(
            catalog_path=tmp_hoard / "data" / "hoard" / "catalog.yaml",
            bases_dir=tmp_hoard / "data" / "hoard" / "bases",
        )
        request = BuildRequest(
            spec_source=minimal_spec_dict,
            base_asset_id="vroid/sample_a",
            output_dir=tmp_path / "output",
            compliance_targets=["VRCHAT"],
        )

        with patch("seidr_smidja.forge.runner.build") as mock_forge:
            mock_forge.return_value = _make_mock_forge_result(sample_vrm_fixture)

            # Oracle Eye raises (not soft-fail, but exception)
            with patch("seidr_smidja.oracle_eye.eye.render") as mock_render:
                mock_render.side_effect = RuntimeError("Render server down")

                config = {
                    "gate": {
                        "rules_dir": str(_RULES_DIR),
                        "vrchat_tier_target": "Good",
                    }
                }
                response = dispatch(
                    request=request,
                    annall=sqlite_annall,
                    hoard=hoard,
                    config=config,
                )

        # VRM path still comes back (Forge succeeded)
        assert response.vrm_path == sample_vrm_fixture
        # Oracle error is recorded
        oracle_errors = [e for e in response.errors if e.stage == "oracle_eye"]
        assert len(oracle_errors) > 0
        # Gate still ran (compliance_report should be set)
        assert response.compliance_report is not None

    def test_gate_failure_recorded_in_errors(
        self,
        minimal_spec_dict: dict[str, Any],
        tmp_hoard: Path,
        sample_vrm_fixture: Path,
        sqlite_annall: Any,
        tmp_path: Path,
    ) -> None:
        """When Gate reports compliance violations, BuildErrors are recorded."""
        from seidr_smidja.hoard.local import LocalHoardAdapter

        hoard = LocalHoardAdapter(
            catalog_path=tmp_hoard / "data" / "hoard" / "catalog.yaml",
            bases_dir=tmp_hoard / "data" / "hoard" / "bases",
        )
        request = BuildRequest(
            spec_source=minimal_spec_dict,
            base_asset_id="vroid/sample_a",
            output_dir=tmp_path / "output",
            compliance_targets=["VRCHAT"],
        )

        # Build a VRM that will fail Gate (boneless)
        import json
        import struct

        gltf = {
            "asset": {"version": "2.0"},
            "extensionsUsed": ["VRM"],
            "extensions": {
                "VRM": {
                    "specVersion": "0.0",
                    "humanoid": {"humanBones": []},
                    "blendShapeMaster": {"blendShapeGroups": []},
                    "firstPerson": {"lookAt": {"type": "Bone"}},
                }
            },
            "meshes": [],
            "materials": [],
            "nodes": [],
            "accessors": [],
        }
        json_bytes = json.dumps(gltf).encode("utf-8")
        pad = (4 - len(json_bytes) % 4) % 4
        json_bytes += b" " * pad
        total_len = 12 + 8 + len(json_bytes)
        binary = struct.pack("<III", 0x46546C67, 2, total_len)
        binary += struct.pack("<II", len(json_bytes), 0x4E4F534A)
        binary += json_bytes
        failing_vrm = tmp_path / "boneless.vrm"
        failing_vrm.write_bytes(binary)

        with patch("seidr_smidja.forge.runner.build") as mock_forge:
            mock_forge.return_value = _make_mock_forge_result(failing_vrm)
            with patch("seidr_smidja.oracle_eye.eye.render") as mock_render:
                mock_render.return_value = _make_mock_render_result()

                config = {
                    "gate": {
                        "rules_dir": str(_RULES_DIR),
                        "vrchat_tier_target": "Good",
                    }
                }
                response = dispatch(
                    request=request,
                    annall=sqlite_annall,
                    hoard=hoard,
                    config=config,
                )

        # Should have gate compliance errors
        gate_errors = [e for e in response.errors if e.stage == "gate"]
        assert len(gate_errors) > 0
        assert response.compliance_report is not None

    def test_null_annall_accepted(
        self,
        minimal_spec_dict: dict[str, Any],
        tmp_hoard: Path,
        sample_vrm_fixture: Path,
        null_annall: Any,
        tmp_path: Path,
    ) -> None:
        """dispatch() works with NullAnnallAdapter — no logging, no crash."""
        from seidr_smidja.hoard.local import LocalHoardAdapter

        hoard = LocalHoardAdapter(
            catalog_path=tmp_hoard / "data" / "hoard" / "catalog.yaml",
            bases_dir=tmp_hoard / "data" / "hoard" / "bases",
        )
        request = BuildRequest(
            spec_source=minimal_spec_dict,
            base_asset_id="vroid/sample_a",
            output_dir=tmp_path / "output",
        )

        with patch("seidr_smidja.forge.runner.build") as mock_forge:
            mock_forge.return_value = _make_mock_forge_result(sample_vrm_fixture)
            with patch("seidr_smidja.oracle_eye.eye.render") as mock_render:
                mock_render.return_value = _make_mock_render_result()
                response = dispatch(request=request, annall=null_annall, hoard=hoard)

        assert isinstance(response, BuildResponse)
