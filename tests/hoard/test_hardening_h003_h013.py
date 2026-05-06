"""Tests for H-003 (path traversal) and H-013 (catalog validation) — Hoard hardening."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

# ─── H-003: Path traversal containment ───────────────────────────────────────


class TestHoardPathTraversal:
    """H-003: resolve() must reject catalog entries that escape bases_dir."""

    def _make_hoard(self, tmp_path: Path, entries: list[dict[str, Any]]):
        from seidr_smidja.hoard.local import LocalHoardAdapter

        bases_dir = tmp_path / "bases"
        bases_dir.mkdir()
        catalog_path = tmp_path / "catalog.yaml"
        catalog_data = {"format_version": "1", "bases": entries}
        catalog_path.write_text(yaml.dump(catalog_data), encoding="utf-8")
        return LocalHoardAdapter(catalog_path=catalog_path, bases_dir=bases_dir)

    def test_traversal_dotdot_rejected(self, tmp_path: Path) -> None:
        """'../../etc/passwd' style catalog entry must raise HoardSecurityError."""
        from seidr_smidja.hoard.exceptions import HoardSecurityError

        hoard = self._make_hoard(
            tmp_path,
            [{"asset_id": "evil", "filename": "../../etc/passwd", "vrm_version": "0.0"}],
        )
        with pytest.raises(HoardSecurityError, match="outside the Hoard bases_dir"):
            hoard.resolve("evil")

    def test_traversal_absolute_path_rejected(self, tmp_path: Path) -> None:
        """An absolute path filename that escapes bases_dir must be rejected."""
        from seidr_smidja.hoard.exceptions import HoardSecurityError

        # Use a path that definitely isn't under bases_dir
        abs_path = str(tmp_path.parent / "sensitive.vrm")
        hoard = self._make_hoard(
            tmp_path,
            [{"asset_id": "evil_abs", "filename": abs_path, "vrm_version": "0.0"}],
        )
        with pytest.raises(HoardSecurityError):
            hoard.resolve("evil_abs")

    def test_legitimate_file_inside_bases_dir_passes(self, tmp_path: Path) -> None:
        """A valid filename inside bases_dir must pass the containment check."""
        from seidr_smidja.hoard.exceptions import AssetNotFoundError

        # The file doesn't exist, so we get AssetNotFoundError — NOT HoardSecurityError
        hoard = self._make_hoard(
            tmp_path,
            [{"asset_id": "legit", "filename": "test.vrm", "vrm_version": "0.0"}],
        )
        # Should raise AssetNotFoundError (file missing), not HoardSecurityError
        with pytest.raises(AssetNotFoundError):
            hoard.resolve("legit")

    def test_traversal_with_encoded_slash_rejected(self, tmp_path: Path) -> None:
        """Path components that normalize outside bases_dir must be caught."""
        from seidr_smidja.hoard.exceptions import HoardSecurityError

        # subdir/../.. traverses out
        hoard = self._make_hoard(
            tmp_path,
            [{"asset_id": "tricky", "filename": "subdir/../../outside.vrm", "vrm_version": "0.0"}],
        )
        with pytest.raises(HoardSecurityError):
            hoard.resolve("tricky")

    def test_hoard_security_error_carries_asset_id(self, tmp_path: Path) -> None:
        """HoardSecurityError.asset_id must be set correctly."""
        from seidr_smidja.hoard.exceptions import HoardSecurityError

        hoard = self._make_hoard(
            tmp_path,
            [{"asset_id": "malicious_asset", "filename": "../../evil", "vrm_version": "0.0"}],
        )
        with pytest.raises(HoardSecurityError) as exc_info:
            hoard.resolve("malicious_asset")
        assert exc_info.value.asset_id == "malicious_asset"


# ─── H-013: Catalog validation ───────────────────────────────────────────────


class TestCatalogValidation:
    """H-013: _load_catalog() must warn on and exclude malformed entries."""

    def _make_hoard(self, tmp_path: Path, raw_yaml_content: str):
        from seidr_smidja.hoard.local import LocalHoardAdapter

        bases_dir = tmp_path / "bases"
        bases_dir.mkdir()
        catalog_path = tmp_path / "catalog.yaml"
        catalog_path.write_text(raw_yaml_content, encoding="utf-8")
        return LocalHoardAdapter(catalog_path=catalog_path, bases_dir=bases_dir)

    def test_valid_entry_accepted(self, tmp_path: Path) -> None:
        yaml_content = (
            "format_version: '1'\nbases:\n"
            "  - asset_id: good\n    filename: test.vrm\n    vrm_version: '0.0'\n"
        )
        hoard = self._make_hoard(tmp_path, yaml_content)
        # Trigger load
        assets = hoard.list_assets()
        assert len(assets) == 1
        assert assets[0].asset_id == "good"

    def test_entry_without_asset_id_excluded(self, tmp_path: Path) -> None:
        hoard = self._make_hoard(
            tmp_path,
            "format_version: '1'\nbases:\n  - filename: test.vrm\n    vrm_version: '0.0'\n",
        )
        assets = hoard.list_assets()
        assert len(assets) == 0

    def test_entry_without_filename_excluded(self, tmp_path: Path) -> None:
        hoard = self._make_hoard(
            tmp_path,
            "format_version: '1'\nbases:\n  - asset_id: no_file\n    vrm_version: '0.0'\n",
        )
        assets = hoard.list_assets()
        assert len(assets) == 0

    def test_duplicate_asset_id_second_occurrence_excluded(self, tmp_path: Path) -> None:
        hoard = self._make_hoard(
            tmp_path,
            (
                "format_version: '1'\nbases:\n"
                "  - asset_id: dupe\n    filename: first.vrm\n    vrm_version: '0.0'\n"
                "  - asset_id: dupe\n    filename: second.vrm\n    vrm_version: '0.0'\n"
            ),
        )
        assets = hoard.list_assets()
        # Only first occurrence kept
        assert len(assets) == 1

    def test_non_dict_entry_excluded(self, tmp_path: Path) -> None:
        yaml_content = (
            "format_version: '1'\nbases:\n"
            "  - just_a_string\n  - asset_id: ok\n    filename: ok.vrm\n    vrm_version: '0.0'\n"
        )
        hoard = self._make_hoard(tmp_path, yaml_content)
        assets = hoard.list_assets()
        assert len(assets) == 1
        assert assets[0].asset_id == "ok"

    def test_empty_catalog_accepted(self, tmp_path: Path) -> None:
        hoard = self._make_hoard(
            tmp_path,
            "format_version: '1'\nbases: []\n",
        )
        assets = hoard.list_assets()
        assert assets == []

    def test_mixed_valid_invalid_entries(self, tmp_path: Path) -> None:
        hoard = self._make_hoard(
            tmp_path,
            (
                "format_version: '1'\nbases:\n"
                "  - asset_id: valid_one\n    filename: one.vrm\n    vrm_version: '0.0'\n"
                "  - filename: no_id.vrm\n    vrm_version: '0.0'\n"
                "  - asset_id: valid_two\n    filename: two.vrm\n    vrm_version: '0.0'\n"
            ),
        )
        assets = hoard.list_assets()
        assert len(assets) == 2
        assert {a.asset_id for a in assets} == {"valid_one", "valid_two"}
