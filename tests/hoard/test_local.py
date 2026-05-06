"""Tests for seidr_smidja.hoard.local — LocalHoardAdapter."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from seidr_smidja.hoard.exceptions import AssetNotFoundError, HoardError
from seidr_smidja.hoard.local import LocalHoardAdapter
from seidr_smidja.hoard.port import AssetFilter


class TestLocalHoardAdapterResolve:
    def test_resolve_existing_asset(self, tmp_hoard: Path) -> None:
        catalog = tmp_hoard / "data" / "hoard" / "catalog.yaml"
        bases = tmp_hoard / "data" / "hoard" / "bases"
        adapter = LocalHoardAdapter(catalog_path=catalog, bases_dir=bases)
        result = adapter.resolve("vroid/sample_a")
        assert result.exists()
        assert result.suffix == ".vrm"

    def test_resolve_unknown_asset(self, tmp_hoard: Path) -> None:
        catalog = tmp_hoard / "data" / "hoard" / "catalog.yaml"
        bases = tmp_hoard / "data" / "hoard" / "bases"
        adapter = LocalHoardAdapter(catalog_path=catalog, bases_dir=bases)
        with pytest.raises(AssetNotFoundError) as exc_info:
            adapter.resolve("unknown/asset")
        assert "unknown/asset" in str(exc_info.value)

    def test_resolve_missing_file(self, tmp_path: Path) -> None:
        """Catalog entry exists but file is absent on disk."""
        catalog_data = {
            "format_version": "1",
            "bases": [
                {
                    "asset_id": "test/missing",
                    "display_name": "Missing",
                    "filename": "ghost.vrm",
                    "vrm_version": "0.0",
                    "tags": [],
                    "license": "CC0-1.0",
                    "cached": True,
                }
            ],
        }
        catalog = tmp_path / "catalog.yaml"
        catalog.write_text(yaml.dump(catalog_data), encoding="utf-8")
        bases = tmp_path / "bases"
        bases.mkdir()
        adapter = LocalHoardAdapter(catalog_path=catalog, bases_dir=bases)
        with pytest.raises(AssetNotFoundError, match="test/missing"):
            adapter.resolve("test/missing")

    def test_resolve_uncached_asset(self, tmp_path: Path) -> None:
        """Catalog entry with cached=False and no file → AssetNotFoundError."""
        catalog_data = {
            "format_version": "1",
            "bases": [
                {
                    "asset_id": "test/uncached",
                    "display_name": "Uncached",
                    "filename": "uncached.vrm",
                    "vrm_version": "0.0",
                    "tags": [],
                    "license": "CC0-1.0",
                    "cached": False,
                }
            ],
        }
        catalog = tmp_path / "catalog.yaml"
        catalog.write_text(yaml.dump(catalog_data), encoding="utf-8")
        bases = tmp_path / "bases"
        bases.mkdir()
        adapter = LocalHoardAdapter(catalog_path=catalog, bases_dir=bases)
        with pytest.raises(AssetNotFoundError, match="bootstrap"):
            adapter.resolve("test/uncached")

    def test_missing_catalog(self, tmp_path: Path) -> None:
        adapter = LocalHoardAdapter(
            catalog_path=tmp_path / "no_such_catalog.yaml",
            bases_dir=tmp_path / "bases",
        )
        with pytest.raises(HoardError, match="bootstrap"):
            adapter.resolve("anything")


class TestLocalHoardAdapterListAssets:
    def test_list_all(self, tmp_hoard: Path) -> None:
        catalog = tmp_hoard / "data" / "hoard" / "catalog.yaml"
        bases = tmp_hoard / "data" / "hoard" / "bases"
        adapter = LocalHoardAdapter(catalog_path=catalog, bases_dir=bases)
        assets = adapter.list_assets()
        assert len(assets) >= 1
        ids = [a.asset_id for a in assets]
        assert "vroid/sample_a" in ids

    def test_list_by_tag(self, tmp_hoard: Path) -> None:
        catalog = tmp_hoard / "data" / "hoard" / "catalog.yaml"
        bases = tmp_hoard / "data" / "hoard" / "bases"
        adapter = LocalHoardAdapter(catalog_path=catalog, bases_dir=bases)
        assets = adapter.list_assets(AssetFilter(tags=["feminine"]))
        assert all("feminine" in a.tags for a in assets)

    def test_list_by_nonexistent_tag(self, tmp_hoard: Path) -> None:
        catalog = tmp_hoard / "data" / "hoard" / "catalog.yaml"
        bases = tmp_hoard / "data" / "hoard" / "bases"
        adapter = LocalHoardAdapter(catalog_path=catalog, bases_dir=bases)
        assets = adapter.list_assets(AssetFilter(tags=["nonexistent_tag_xyz"]))
        assert assets == []

    def test_cached_flag_reflects_file_presence(self, tmp_hoard: Path) -> None:
        catalog = tmp_hoard / "data" / "hoard" / "catalog.yaml"
        bases = tmp_hoard / "data" / "hoard" / "bases"
        adapter = LocalHoardAdapter(catalog_path=catalog, bases_dir=bases)
        assets = adapter.list_assets()
        for asset in assets:
            if asset.asset_id == "vroid/sample_a":
                assert asset.cached is True  # file actually exists in tmp_hoard

    def test_catalog_path_property(self, tmp_hoard: Path) -> None:
        catalog = tmp_hoard / "data" / "hoard" / "catalog.yaml"
        bases = tmp_hoard / "data" / "hoard" / "bases"
        adapter = LocalHoardAdapter(catalog_path=catalog, bases_dir=bases)
        assert adapter.catalog_path() == catalog

    def test_catalog_lazy_loaded(self, tmp_hoard: Path) -> None:
        """Catalog is not loaded at construction time."""
        catalog = tmp_hoard / "data" / "hoard" / "catalog.yaml"
        bases = tmp_hoard / "data" / "hoard" / "bases"
        adapter = LocalHoardAdapter(catalog_path=catalog, bases_dir=bases)
        assert adapter._loaded is False
        adapter.list_assets()
        assert adapter._loaded is True


class TestLocalHoardAdapterFromConfig:
    def test_from_config(self, tmp_hoard: Path) -> None:
        config = {
            "hoard": {
                "catalog_path": "data/hoard/catalog.yaml",
                "bases_dir": "data/hoard/bases",
            }
        }
        adapter = LocalHoardAdapter.from_config(config, project_root=tmp_hoard)
        assets = adapter.list_assets()
        assert len(assets) >= 1
