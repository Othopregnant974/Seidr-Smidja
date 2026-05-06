"""Tests for the Rúnstafr CLI bridge — H-018 coverage + H-009 double-load regression.

Uses click.testing.CliRunner for all tests — no Blender required.
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

# ─── Common config dicts (extracted to avoid 149-char lines) ─────────────────

_NULL_CFG: dict[str, Any] = {
    "annall": {"adapter": "null"},
    "output": {"root": "output"},
}

_HOARD_CFG: dict[str, Any] = {
    "hoard": {
        "catalog_path": "data/hoard/catalog.yaml",
        "bases_dir": "data/hoard/bases",
    }
}


@pytest.fixture
def runner():
    from click.testing import CliRunner
    return CliRunner()


@pytest.fixture
def cli():
    from seidr_smidja.bridges.runstafr.cli import cli as _cli
    return _cli


@pytest.fixture
def minimal_spec_yaml(tmp_path: Path) -> Path:
    spec_dict = {
        "spec_version": "1.0",
        "avatar_id": "cli_test_avatar",
        "display_name": "CLI Test Avatar",
        "base_asset_id": "vroid/sample_a",
        "metadata": {"author": "Test", "license": "CC0-1.0"},
    }
    p = tmp_path / "spec.yaml"
    p.write_text(yaml.dump(spec_dict), encoding="utf-8")
    return p


# ─── seidr version ────────────────────────────────────────────────────────────


class TestCmdVersion:
    def test_version_exits_zero(self, runner, cli) -> None:
        result = runner.invoke(cli, ["version"])
        assert result.exit_code == 0

    def test_version_output_contains_seidr(self, runner, cli) -> None:
        result = runner.invoke(cli, ["version"])
        assert "seidr" in result.output.lower()

    def test_version_flag(self, runner, cli) -> None:
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0


# ─── seidr build ──────────────────────────────────────────────────────────────


class TestCmdBuild:
    def _make_successful_response(self, tmp_path: Path) -> Any:
        from seidr_smidja.bridges.core.dispatch import BuildResponse
        return BuildResponse(
            request_id="req-123",
            success=True,
            vrm_path=tmp_path / "output.vrm",
            elapsed_seconds=0.5,
        )

    def _make_failed_response(self) -> Any:
        from seidr_smidja.bridges.core.dispatch import BuildError, BuildResponse
        return BuildResponse(
            request_id="req-fail",
            success=False,
            errors=[
                BuildError(
                    stage="forge",
                    error_type="ForgeBuildError",
                    message="Blender not found",
                )
            ],
            elapsed_seconds=0.1,
        )

    def test_build_spec_not_found_exits_nonzero(
        self, runner, cli, tmp_path: Path
    ) -> None:
        result = runner.invoke(cli, ["build", str(tmp_path / "nonexistent.yaml")])
        assert result.exit_code != 0

    def test_build_with_valid_spec_calls_dispatch(
        self, runner, cli, minimal_spec_yaml: Path, tmp_path: Path
    ) -> None:
        """build command calls dispatch() exactly once and exits 0 on success."""
        mock_response = self._make_successful_response(tmp_path)
        dispatch_module = importlib.import_module("seidr_smidja.bridges.core.dispatch")

        with (
            patch(
                "seidr_smidja.bridges.runstafr.cli._find_project_root",
                return_value=tmp_path,
            ),
            patch(
                "seidr_smidja.bridges.runstafr.cli._load_config",
                return_value=_NULL_CFG,
            ),
            patch.object(dispatch_module, "dispatch", return_value=mock_response),
        ):
            result = runner.invoke(cli, ["build", str(minimal_spec_yaml)])

        assert result.exit_code == 0

    def test_build_json_output_flag(
        self, runner, cli, minimal_spec_yaml: Path, tmp_path: Path
    ) -> None:
        """--json flag produces parseable JSON output."""
        mock_response = self._make_successful_response(tmp_path)
        dispatch_module = importlib.import_module("seidr_smidja.bridges.core.dispatch")

        with (
            patch(
                "seidr_smidja.bridges.runstafr.cli._find_project_root",
                return_value=tmp_path,
            ),
            patch(
                "seidr_smidja.bridges.runstafr.cli._load_config",
                return_value=_NULL_CFG,
            ),
            patch.object(dispatch_module, "dispatch", return_value=mock_response),
        ):
            result = runner.invoke(
                cli, ["build", str(minimal_spec_yaml), "--json"]
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "success" in data
        assert data["success"] is True

    def test_build_failed_response_exits_nonzero(
        self, runner, cli, minimal_spec_yaml: Path, tmp_path: Path
    ) -> None:
        """When dispatch returns success=False, exit code is 1."""
        mock_response = self._make_failed_response()
        dispatch_module = importlib.import_module("seidr_smidja.bridges.core.dispatch")

        with (
            patch(
                "seidr_smidja.bridges.runstafr.cli._find_project_root",
                return_value=tmp_path,
            ),
            patch(
                "seidr_smidja.bridges.runstafr.cli._load_config",
                return_value=_NULL_CFG,
            ),
            patch.object(dispatch_module, "dispatch", return_value=mock_response),
        ):
            result = runner.invoke(cli, ["build", str(minimal_spec_yaml)])

        assert result.exit_code == 1

    def test_build_spec_loaded_once_not_twice(
        self, runner, cli, minimal_spec_yaml: Path, tmp_path: Path
    ) -> None:
        """H-009: load_spec() must be called exactly once per build command invocation.

        After the H-009 fix, the CLI passes spec.to_dict() to dispatch() instead of
        the file path, so dispatch() does not re-read the file. This test verifies
        that the spec file is read once and only once via the loom loader.
        """
        from seidr_smidja.loom.loader import load_spec as real_load_spec

        load_spec_call_count = 0

        def counting_load_spec(*args, **kwargs):
            nonlocal load_spec_call_count
            load_spec_call_count += 1
            return real_load_spec(*args, **kwargs)

        mock_response = self._make_successful_response(tmp_path)
        dispatch_module = importlib.import_module("seidr_smidja.bridges.core.dispatch")
        loom_loader_module = importlib.import_module("seidr_smidja.loom.loader")

        with (
            patch(
                "seidr_smidja.bridges.runstafr.cli._find_project_root",
                return_value=tmp_path,
            ),
            patch(
                "seidr_smidja.bridges.runstafr.cli._load_config",
                return_value=_NULL_CFG,
            ),
            patch.object(
                loom_loader_module, "load_spec", side_effect=counting_load_spec
            ),
            patch.object(dispatch_module, "dispatch", return_value=mock_response),
        ):
            runner.invoke(cli, ["build", str(minimal_spec_yaml)])

        # Per H-009 fix: the CLI loads the spec dict once, then passes it to dispatch.
        # dispatch() receives a dict (not a path) so it does NOT call load_spec again.
        assert load_spec_call_count == 1, (
            f"H-009 regression: load_spec called {load_spec_call_count} times"
            f" — should be exactly 1"
        )

    def test_build_invalid_yaml_spec_exits_error(
        self, runner, cli, tmp_path: Path
    ) -> None:
        """A spec file with invalid content exits with error code 1."""
        bad_spec = tmp_path / "bad.yaml"
        bad_spec.write_text("this: is: invalid: yaml: !!nonsense", encoding="utf-8")

        with (
            patch(
                "seidr_smidja.bridges.runstafr.cli._find_project_root",
                return_value=tmp_path,
            ),
            patch(
                "seidr_smidja.bridges.runstafr.cli._load_config",
                return_value=_NULL_CFG,
            ),
        ):
            result = runner.invoke(cli, ["build", str(bad_spec)])

        assert result.exit_code == 1

    def test_build_json_error_on_spec_failure(
        self, runner, cli, tmp_path: Path
    ) -> None:
        """--json flag emits JSON error when spec load fails."""
        bad_spec = tmp_path / "bad.yaml"
        bad_spec.write_text("{missing_required_fields: true}", encoding="utf-8")

        with (
            patch(
                "seidr_smidja.bridges.runstafr.cli._find_project_root",
                return_value=tmp_path,
            ),
            patch(
                "seidr_smidja.bridges.runstafr.cli._load_config",
                return_value=_NULL_CFG,
            ),
        ):
            result = runner.invoke(cli, ["build", str(bad_spec), "--json"])

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "error" in data


# ─── seidr inspect ────────────────────────────────────────────────────────────


class TestCmdInspect:
    def test_inspect_nonexistent_file_exits_nonzero(
        self, runner, cli, tmp_path: Path
    ) -> None:
        """inspect on a non-existent file should exit with an error."""
        result = runner.invoke(cli, ["inspect", str(tmp_path / "no_such.vrm")])
        assert result.exit_code != 0

    def test_inspect_with_real_vrm_produces_report(
        self, runner, cli, sample_vrm_fixture: Path, tmp_path: Path
    ) -> None:
        """inspect on the sample VRM fixture should produce a compliance report."""
        with (
            patch(
                "seidr_smidja.bridges.runstafr.cli._find_project_root",
                return_value=tmp_path,
            ),
            patch(
                "seidr_smidja.bridges.runstafr.cli._load_config",
                return_value={"gate": {}},
            ),
        ):
            result = runner.invoke(cli, ["inspect", str(sample_vrm_fixture)])

        # Should exit 0 (pass) or 1 (fail) — both are valid outcomes for inspection
        assert result.exit_code in (0, 1)
        assert len(result.output) > 0

    def test_inspect_json_output(
        self, runner, cli, sample_vrm_fixture: Path, tmp_path: Path
    ) -> None:
        """--json flag on inspect produces parseable JSON."""
        with (
            patch(
                "seidr_smidja.bridges.runstafr.cli._find_project_root",
                return_value=tmp_path,
            ),
            patch(
                "seidr_smidja.bridges.runstafr.cli._load_config",
                return_value={"gate": {}},
            ),
        ):
            result = runner.invoke(
                cli, ["inspect", str(sample_vrm_fixture), "--json"]
            )

        assert result.exit_code in (0, 1)
        data = json.loads(result.output)
        assert "passed" in data or "results" in data


# ─── seidr bootstrap-hoard ───────────────────────────────────────────────────


class TestCmdBootstrapHoard:
    def test_bootstrap_hoard_invokes_run_bootstrap(
        self, runner, cli, tmp_path: Path
    ) -> None:
        """bootstrap-hoard command must call run_bootstrap with correct args."""
        with (
            patch(
                "seidr_smidja.bridges.runstafr.cli._find_project_root",
                return_value=tmp_path,
            ),
            patch(
                "seidr_smidja.bridges.runstafr.cli._load_config",
                return_value=_HOARD_CFG,
            ),
            patch(
                "seidr_smidja.hoard.bootstrap.run_bootstrap",
                return_value={"vroid/sample_a": True},
            ) as mock_bootstrap,
        ):
            result = runner.invoke(cli, ["bootstrap-hoard"])

        mock_bootstrap.assert_called_once()
        assert result.exit_code == 0

    def test_bootstrap_hoard_force_flag(
        self, runner, cli, tmp_path: Path
    ) -> None:
        """--force flag is passed through to run_bootstrap."""
        with (
            patch(
                "seidr_smidja.bridges.runstafr.cli._find_project_root",
                return_value=tmp_path,
            ),
            patch(
                "seidr_smidja.bridges.runstafr.cli._load_config",
                return_value=_HOARD_CFG,
            ),
            patch(
                "seidr_smidja.hoard.bootstrap.run_bootstrap",
                return_value={},
            ) as mock_bootstrap,
        ):
            runner.invoke(cli, ["bootstrap-hoard", "--force"])

        call_kwargs = mock_bootstrap.call_args
        assert call_kwargs.kwargs.get("force") is True or (
            call_kwargs.args and True in call_kwargs.args
        )


# ─── seidr list-assets (H-022) ───────────────────────────────────────────────


class TestCmdListAssets:
    def _make_catalog(self, tmp_path: Path) -> Path:
        bases_dir = tmp_path / "data/hoard/bases"
        bases_dir.mkdir(parents=True)
        catalog_path = tmp_path / "data/hoard/catalog.yaml"
        catalog_data = {
            "format_version": "1",
            "bases": [
                {
                    "asset_id": "vroid/sample_a",
                    "display_name": "Sample A",
                    "filename": "SampleA.vrm",
                    "vrm_version": "0.0",
                    "tags": ["feminine", "sample"],
                    "cached": False,
                },
                {
                    "asset_id": "vroid/sample_b",
                    "display_name": "Sample B",
                    "filename": "SampleB.vrm",
                    "vrm_version": "0.0",
                    "tags": ["masculine", "sample"],
                    "cached": False,
                },
            ],
        }
        catalog_path.write_text(yaml.dump(catalog_data), encoding="utf-8")
        return catalog_path

    def test_list_assets_returns_all(
        self, runner, cli, tmp_path: Path
    ) -> None:
        self._make_catalog(tmp_path)
        with (
            patch(
                "seidr_smidja.bridges.runstafr.cli._find_project_root",
                return_value=tmp_path,
            ),
            patch(
                "seidr_smidja.bridges.runstafr.cli._load_config",
                return_value=_HOARD_CFG,
            ),
        ):
            result = runner.invoke(cli, ["list-assets"])

        assert result.exit_code == 0
        assert "sample_a" in result.output
        assert "sample_b" in result.output

    def test_list_assets_json_output(
        self, runner, cli, tmp_path: Path
    ) -> None:
        self._make_catalog(tmp_path)
        with (
            patch(
                "seidr_smidja.bridges.runstafr.cli._find_project_root",
                return_value=tmp_path,
            ),
            patch(
                "seidr_smidja.bridges.runstafr.cli._load_config",
                return_value=_HOARD_CFG,
            ),
        ):
            result = runner.invoke(cli, ["list-assets", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 2
        ids = {d["asset_id"] for d in data}
        assert "vroid/sample_a" in ids

    def test_list_assets_type_filter(
        self, runner, cli, tmp_path: Path
    ) -> None:
        self._make_catalog(tmp_path)
        with (
            patch(
                "seidr_smidja.bridges.runstafr.cli._find_project_root",
                return_value=tmp_path,
            ),
            patch(
                "seidr_smidja.bridges.runstafr.cli._load_config",
                return_value=_HOARD_CFG,
            ),
        ):
            result = runner.invoke(
                cli, ["list-assets", "--type", "vrm_base", "--json"]
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2  # Both are vrm_base type

    def test_list_assets_tag_filter(
        self, runner, cli, tmp_path: Path
    ) -> None:
        self._make_catalog(tmp_path)
        with (
            patch(
                "seidr_smidja.bridges.runstafr.cli._find_project_root",
                return_value=tmp_path,
            ),
            patch(
                "seidr_smidja.bridges.runstafr.cli._load_config",
                return_value=_HOARD_CFG,
            ),
        ):
            result = runner.invoke(
                cli, ["list-assets", "--tag", "feminine", "--json"]
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["asset_id"] == "vroid/sample_a"

    def test_list_assets_empty_result(
        self, runner, cli, tmp_path: Path
    ) -> None:
        self._make_catalog(tmp_path)
        with (
            patch(
                "seidr_smidja.bridges.runstafr.cli._find_project_root",
                return_value=tmp_path,
            ),
            patch(
                "seidr_smidja.bridges.runstafr.cli._load_config",
                return_value=_HOARD_CFG,
            ),
        ):
            result = runner.invoke(
                cli, ["list-assets", "--tag", "nonexistent_tag"]
            )

        assert result.exit_code == 0
        assert "No assets found" in result.output

    def test_list_assets_json_structure(
        self, runner, cli, tmp_path: Path
    ) -> None:
        """JSON output must include all required fields."""
        self._make_catalog(tmp_path)
        with (
            patch(
                "seidr_smidja.bridges.runstafr.cli._find_project_root",
                return_value=tmp_path,
            ),
            patch(
                "seidr_smidja.bridges.runstafr.cli._load_config",
                return_value=_HOARD_CFG,
            ),
        ):
            result = runner.invoke(cli, ["list-assets", "--json"])

        data = json.loads(result.output)
        for item in data:
            assert "asset_id" in item
            assert "display_name" in item
            assert "asset_type" in item
            assert "tags" in item
            assert "vrm_version" in item
            assert "cached" in item
