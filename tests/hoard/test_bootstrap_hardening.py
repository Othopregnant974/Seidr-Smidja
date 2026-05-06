"""Tests for hoard/bootstrap.py — H-020 coverage + H-012 SHA-256 verification."""
from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml


def _make_minimal_catalog(catalog_path: Path) -> None:
    """Write a minimal catalog.yaml with one known asset."""
    catalog_data = {
        "format_version": "1",
        "bases": [
            {
                "asset_id": "vroid/sample_a",
                "display_name": "Sample A",
                "filename": "AvatarSampleA.vrm",
                "vrm_version": "0.0",
                "tags": ["sample"],
                "cached": False,
            }
        ],
    }
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(yaml.dump(catalog_data), encoding="utf-8")


class TestBootstrapCore:
    """H-020: Core bootstrap logic — download, catalog update, force flag."""

    def test_compute_sha256_correct(self, tmp_path: Path) -> None:
        from seidr_smidja.hoard.bootstrap import _compute_sha256

        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"hello world")
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert _compute_sha256(test_file) == expected

    def test_download_success_returns_true(self, tmp_path: Path) -> None:
        from seidr_smidja.hoard.bootstrap import _download

        dest = tmp_path / "test.vrm"
        fake_content = b"\x00" * 64

        # Mock httpx to avoid real network access
        mock_response = MagicMock()
        mock_response.content = fake_content
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(return_value=mock_response)

        with patch("httpx.Client", return_value=mock_client):
            result = _download("https://example.com/test.vrm", dest, verbose=False)

        assert result is True
        assert dest.exists()
        assert dest.read_bytes() == fake_content

    def test_download_failure_returns_false(self, tmp_path: Path) -> None:
        from seidr_smidja.hoard.bootstrap import _download

        dest = tmp_path / "test.vrm"

        with (
            patch("httpx.Client", side_effect=Exception("network error")),
            patch(
                "urllib.request.urlretrieve", side_effect=Exception("also failed")
            ),
        ):
            result = _download("https://example.com/test.vrm", dest, verbose=False)

        assert result is False
        assert not dest.exists()

    def test_run_bootstrap_skips_cached_assets(self, tmp_path: Path) -> None:
        """When a file already exists and force=False, it should be skipped."""
        from seidr_smidja.hoard.bootstrap import run_bootstrap

        catalog_path = tmp_path / "catalog.yaml"
        bases_dir = tmp_path / "bases"
        bases_dir.mkdir()

        # Pre-create the file to simulate already cached
        dest = bases_dir / "AvatarSampleA.vrm"
        dest.write_bytes(b"\x00" * 32)

        _make_minimal_catalog(catalog_path)

        # Patch catalog update to avoid touching real catalogs
        with patch("seidr_smidja.hoard.bootstrap._update_catalog_entry") as mock_update:
            results = run_bootstrap(
                catalog_path=catalog_path,
                bases_dir=bases_dir,
                force=False,
                verbose=False,
            )

        assert results["vroid/sample_a"] is True
        # Catalog update should still be called for cached assets
        mock_update.assert_called()

    def test_run_bootstrap_force_redownloads(self, tmp_path: Path) -> None:
        """force=True must attempt download even when file exists."""
        import copy

        from seidr_smidja.hoard.bootstrap import _BOOTSTRAP_ASSETS, run_bootstrap

        catalog_path = tmp_path / "catalog.yaml"
        bases_dir = tmp_path / "bases"
        bases_dir.mkdir()

        # Use only one asset to avoid stat() errors for the second
        single_asset = [copy.deepcopy(_BOOTSTRAP_ASSETS[0])]
        dest = bases_dir / single_asset[0]["filename"]
        dest.write_bytes(b"\x00" * 32)

        _make_minimal_catalog(catalog_path)

        def mock_download_creates_file(url, dest_path, verbose=True):
            # Simulate download by writing a file so stat() works
            dest_path.write_bytes(b"\x01" * 32)
            return True

        dl_patch = "seidr_smidja.hoard.bootstrap._download"
        with (
            patch("seidr_smidja.hoard.bootstrap._BOOTSTRAP_ASSETS", single_asset),
            patch(dl_patch, side_effect=mock_download_creates_file) as mock_dl,
            patch("seidr_smidja.hoard.bootstrap._update_catalog_entry"),
        ):
            run_bootstrap(
                catalog_path=catalog_path,
                bases_dir=bases_dir,
                force=True,
                verbose=False,
            )

        # force=True should have attempted download
        mock_dl.assert_called()

    def test_run_bootstrap_failed_download_returns_false(self, tmp_path: Path) -> None:
        """When all downloads fail, result dict must map asset_id to False."""
        from seidr_smidja.hoard.bootstrap import run_bootstrap

        catalog_path = tmp_path / "catalog.yaml"
        bases_dir = tmp_path / "bases"
        bases_dir.mkdir()
        _make_minimal_catalog(catalog_path)

        with patch("seidr_smidja.hoard.bootstrap._download", return_value=False):
            results = run_bootstrap(
                catalog_path=catalog_path,
                bases_dir=bases_dir,
                force=False,
                verbose=False,
            )

        assert "vroid/sample_a" in results
        assert results["vroid/sample_a"] is False


class TestBootstrapSHA256:
    """H-012: SHA-256 pinning verification."""

    def test_hash_mismatch_deletes_file_and_returns_false(self, tmp_path: Path) -> None:
        """When expected_sha256 is set and doesn't match, the file must be deleted."""
        import copy

        from seidr_smidja.hoard.bootstrap import _BOOTSTRAP_ASSETS, run_bootstrap

        catalog_path = tmp_path / "catalog.yaml"
        bases_dir = tmp_path / "bases"
        bases_dir.mkdir()
        _make_minimal_catalog(catalog_path)

        # Patch _BOOTSTRAP_ASSETS to include a wrong expected_sha256
        patched_assets = copy.deepcopy(_BOOTSTRAP_ASSETS[:1])  # First asset only
        # A hash that will never match any real file content
        wrong_hash = "0" * 64
        patched_assets[0]["expected_sha256"] = wrong_hash

        fake_content = b"\x01" * 32  # real sha256 != 000...

        def mock_download(url, dest, verbose=True):
            dest.write_bytes(fake_content)
            return True

        with (
            patch("seidr_smidja.hoard.bootstrap._BOOTSTRAP_ASSETS", patched_assets),
            patch("seidr_smidja.hoard.bootstrap._download", side_effect=mock_download),
            patch("seidr_smidja.hoard.bootstrap._update_catalog_entry"),
        ):
            results = run_bootstrap(
                catalog_path=catalog_path,
                bases_dir=bases_dir,
                force=True,
                verbose=False,
            )

        asset_id = patched_assets[0]["asset_id"]
        assert results[asset_id] is False
        # File must be deleted after mismatch
        dest = bases_dir / patched_assets[0]["filename"]
        assert not dest.exists(), "Tampered file was not deleted after SHA-256 mismatch"

    def test_hash_match_returns_true(self, tmp_path: Path) -> None:
        """When expected_sha256 matches computed hash, bootstrap succeeds."""
        import copy

        from seidr_smidja.hoard.bootstrap import _BOOTSTRAP_ASSETS, run_bootstrap

        catalog_path = tmp_path / "catalog.yaml"
        bases_dir = tmp_path / "bases"
        bases_dir.mkdir()
        _make_minimal_catalog(catalog_path)

        fake_content = b"\x01" * 32
        correct_hash = hashlib.sha256(fake_content).hexdigest()

        patched_assets = copy.deepcopy(_BOOTSTRAP_ASSETS[:1])
        patched_assets[0]["expected_sha256"] = correct_hash

        def mock_download(url, dest, verbose=True):
            dest.write_bytes(fake_content)
            return True

        with (
            patch("seidr_smidja.hoard.bootstrap._BOOTSTRAP_ASSETS", patched_assets),
            patch("seidr_smidja.hoard.bootstrap._download", side_effect=mock_download),
            patch("seidr_smidja.hoard.bootstrap._update_catalog_entry"),
        ):
            results = run_bootstrap(
                catalog_path=catalog_path,
                bases_dir=bases_dir,
                force=True,
                verbose=False,
            )

        asset_id = patched_assets[0]["asset_id"]
        assert results[asset_id] is True

    def test_no_expected_hash_does_not_fail(self, tmp_path: Path) -> None:
        """When expected_sha256 is absent, bootstrap proceeds without verification."""
        import copy

        from seidr_smidja.hoard.bootstrap import _BOOTSTRAP_ASSETS, run_bootstrap

        catalog_path = tmp_path / "catalog.yaml"
        bases_dir = tmp_path / "bases"
        bases_dir.mkdir()
        _make_minimal_catalog(catalog_path)

        patched_assets = copy.deepcopy(_BOOTSTRAP_ASSETS[:1])
        # Remove expected_sha256 if present
        patched_assets[0].pop("expected_sha256", None)

        fake_content = b"\x01" * 32

        def mock_download(url, dest, verbose=True):
            dest.write_bytes(fake_content)
            return True

        with (
            patch("seidr_smidja.hoard.bootstrap._BOOTSTRAP_ASSETS", patched_assets),
            patch("seidr_smidja.hoard.bootstrap._download", side_effect=mock_download),
            patch("seidr_smidja.hoard.bootstrap._update_catalog_entry"),
        ):
            results = run_bootstrap(
                catalog_path=catalog_path,
                bases_dir=bases_dir,
                force=True,
                verbose=False,
            )

        asset_id = patched_assets[0]["asset_id"]
        # No expected hash → warning logged but not a failure
        assert results[asset_id] is True


class TestUpdateCatalogEntry:
    """H-020: Catalog update logic."""

    def test_update_creates_catalog_if_missing(self, tmp_path: Path) -> None:
        from seidr_smidja.hoard.bootstrap import _update_catalog_entry

        catalog_path = tmp_path / "new_catalog.yaml"
        dest = tmp_path / "AvatarSampleA.vrm"
        dest.write_bytes(b"\x00" * 32)
        asset_info = {
            "asset_id": "vroid/sample_a",
            "display_name": "Sample A",
            "filename": "AvatarSampleA.vrm",
            "license": "CC0-1.0",
            "license_url": "https://example.com",
            "source_url": "https://example.com/sample.vrm",
        }

        _update_catalog_entry(catalog_path, "vroid/sample_a", dest, asset_info)

        assert catalog_path.exists()
        with catalog_path.open() as fh:
            data = yaml.safe_load(fh)
        bases = data.get("bases", [])
        assert any(e.get("asset_id") == "vroid/sample_a" for e in bases)

    def test_update_sets_cached_true(self, tmp_path: Path) -> None:
        from seidr_smidja.hoard.bootstrap import _update_catalog_entry

        catalog_path = tmp_path / "catalog.yaml"
        _make_minimal_catalog(catalog_path)

        dest = tmp_path / "AvatarSampleA.vrm"
        dest.write_bytes(b"\x00" * 32)
        asset_info = {
            "asset_id": "vroid/sample_a",
            "display_name": "Sample A",
            "filename": "AvatarSampleA.vrm",
            "license": "CC0-1.0",
            "license_url": "https://example.com",
            "source_url": "https://example.com/sample.vrm",
        }

        _update_catalog_entry(catalog_path, "vroid/sample_a", dest, asset_info)

        with catalog_path.open() as fh:
            data = yaml.safe_load(fh)
        entry = next(e for e in data["bases"] if e["asset_id"] == "vroid/sample_a")
        assert entry["cached"] is True
