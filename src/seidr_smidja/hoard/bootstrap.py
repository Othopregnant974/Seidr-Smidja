"""seidr_smidja.hoard.bootstrap — Bootstrap the Hoard with seed VRM assets.

Downloads permissively-licensed sample VRM files from public sources and
places them in the configured bases_dir. Updates the catalog.yaml with
sha256 hashes and cached=true flags.

License notes:
    The VRM Consortium avatar samples (AvatarSampleA/B) are released under
    the CC0-1.0 license (public domain) by the VRM Consortium.
    Source: https://github.com/vrm-c/vrm-specification/tree/master/samples
    These are safe to include as test/bootstrap assets.

Invoked by:
    python tools/bootstrap_hoard.py
    python -m seidr_smidja.hoard.bootstrap
    seidr bootstrap-hoard
"""
from __future__ import annotations

import hashlib
import logging
import sys
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Source URLs for the bootstrap VRM assets.
# CC0-1.0 license — confirmed from VRM Consortium GitHub repository.
# The vrm-specification repo stores sample VRM files at these paths.
_BOOTSTRAP_ASSETS: list[dict[str, Any]] = [
    {
        "asset_id": "vroid/sample_a",
        "filename": "AvatarSampleA.vrm",
        "display_name": "VRM Sample Avatar A",
        "license": "CC0-1.0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        # Primary URL: VRM Consortium GitHub Releases (stable, versioned)
        "source_url": "https://github.com/vrm-c/vrm-specification/raw/master/samples/AvatarSample_A/AvatarSampleA.vrm",
        "fallback_urls": [
            # three-vrm sample: CC0 sample VRMs used in testing
            "https://github.com/pixiv/three-vrm/raw/dev/packages/three-vrm/tests/models/VRM0/AvatarSample-A.vrm",
        ],
    },
    {
        "asset_id": "vroid/sample_b",
        "filename": "AvatarSampleB.vrm",
        "display_name": "VRM Sample Avatar B",
        "license": "CC0-1.0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "source_url": "https://github.com/vrm-c/vrm-specification/raw/master/samples/AvatarSample_B/AvatarSampleB.vrm",
        "fallback_urls": [],
    },
]


def _compute_sha256(path: Path) -> str:
    """Compute the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, dest: Path, verbose: bool = True) -> bool:
    """Download a URL to a file. Returns True on success, False on failure.

    Uses httpx if available, falls back to urllib (stdlib).
    """
    if verbose:
        print(f"  Downloading: {url}")
        print(f"  → {dest}")

    try:
        import httpx

        with httpx.Client(follow_redirects=True, timeout=120.0) as client:
            response = client.get(url)
            response.raise_for_status()
            dest.write_bytes(response.content)
            return True
    except ImportError:
        # Fall back to urllib.request (stdlib)
        import urllib.request

        try:
            urllib.request.urlretrieve(url, str(dest))
            return True
        except Exception as exc:
            if verbose:
                print(f"  FAILED (urllib): {exc}")
            return False
    except Exception as exc:
        if verbose:
            print(f"  FAILED: {exc}")
        return False


def run_bootstrap(
    catalog_path: Path,
    bases_dir: Path,
    force: bool = False,
    verbose: bool = True,
) -> dict[str, bool]:
    """Execute the bootstrap: download seed assets and update the catalog.

    Args:
        catalog_path: Path to the catalog.yaml file to update.
        bases_dir:    Directory to write downloaded VRM files into.
        force:        If True, re-download even if file already exists.
        verbose:      If True, print progress to stdout.

    Returns:
        A dict mapping asset_id → True (success) / False (failed).
    """
    bases_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, bool] = {}

    for asset_info in _BOOTSTRAP_ASSETS:
        asset_id = asset_info["asset_id"]
        filename = asset_info["filename"]
        dest = bases_dir / filename

        if dest.exists() and not force:
            if verbose:
                print(f"[hoard] '{asset_id}' already cached at {dest} — skipping.")
            results[asset_id] = True
            _update_catalog_entry(catalog_path, asset_id, dest, asset_info)
            continue

        if verbose:
            print(f"\n[hoard] Bootstrapping '{asset_id}'...")
            print(f"  License: {asset_info['license']} — {asset_info['license_url']}")

        # Try primary URL, then fallbacks
        urls = [asset_info["source_url"]] + asset_info.get("fallback_urls", [])
        success = False
        for url in urls:
            if _download(url, dest, verbose=verbose):
                success = True
                break

        if success:
            sha256 = _compute_sha256(dest)
            size = dest.stat().st_size
            if verbose:
                print(f"  OK: {dest.name} ({size} bytes, sha256: {sha256[:16]}...)")
            _update_catalog_entry(catalog_path, asset_id, dest, asset_info, sha256=sha256, size=size)
            results[asset_id] = True
        else:
            if verbose:
                print(f"  ERROR: All download attempts failed for '{asset_id}'.")
                print(
                    "  The forge can still run once you manually place the VRM file at:"
                )
                print(f"    {dest}")
            results[asset_id] = False

    if verbose:
        successes = sum(1 for v in results.values() if v)
        print(f"\n[hoard] Bootstrap complete: {successes}/{len(results)} assets ready.")
        if successes < len(results):
            print(
                "  Run 'python tools/bootstrap_hoard.py --force' to retry failed downloads."
            )

    return results


def _update_catalog_entry(
    catalog_path: Path,
    asset_id: str,
    dest: Path,
    asset_info: dict[str, Any],
    sha256: str | None = None,
    size: int | None = None,
) -> None:
    """Update the catalog YAML entry for an asset to reflect its cached state."""
    try:
        if catalog_path.exists():
            with catalog_path.open("r", encoding="utf-8") as fh:
                catalog_data = yaml.safe_load(fh) or {}
        else:
            catalog_data = {"format_version": "1", "bases": []}

        bases: list[dict[str, Any]] = catalog_data.get("bases", [])
        entry = next((e for e in bases if e.get("asset_id") == asset_id), None)

        if sha256 is None and dest.exists():
            sha256 = _compute_sha256(dest)
        if size is None and dest.exists():
            size = dest.stat().st_size

        if entry is not None:
            entry["cached"] = True
            entry["sha256"] = sha256
            entry["file_size_bytes"] = size
            entry["source_url"] = asset_info["source_url"]
        else:
            # Add new entry
            bases.append(
                {
                    "asset_id": asset_id,
                    "display_name": asset_info["display_name"],
                    "filename": asset_info["filename"],
                    "vrm_version": "0.0",
                    "tags": [],
                    "license": asset_info["license"],
                    "license_url": asset_info["license_url"],
                    "source_url": asset_info["source_url"],
                    "sha256": sha256,
                    "cached": True,
                    "file_size_bytes": size,
                }
            )

        catalog_data["bases"] = bases
        with catalog_path.open("w", encoding="utf-8") as fh:
            yaml.dump(catalog_data, fh, allow_unicode=True, default_flow_style=False)

    except Exception as exc:
        logger.warning("Failed to update catalog for '%s': %s", asset_id, exc)


if __name__ == "__main__":
    # Allow: python -m seidr_smidja.hoard.bootstrap
    import argparse

    from seidr_smidja.config import load_config, resolve_path

    parser = argparse.ArgumentParser(description="Bootstrap the Seiðr-Smiðja Hoard with seed VRM assets.")
    parser.add_argument("--force", action="store_true", help="Re-download even if already cached.")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output.")
    args = parser.parse_args()

    config = load_config()
    catalog = resolve_path(config, config.get("hoard", {}).get("catalog_path", "data/hoard/catalog.yaml"))
    bases = resolve_path(config, config.get("hoard", {}).get("bases_dir", "data/hoard/bases"))

    results = run_bootstrap(
        catalog_path=catalog,
        bases_dir=bases,
        force=args.force,
        verbose=not args.quiet,
    )
    sys.exit(0 if all(results.values()) else 1)
