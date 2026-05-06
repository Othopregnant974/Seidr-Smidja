"""tools/bootstrap_hoard.py — Seed the Hoard with base VRM assets.

Run this once before the first build:
    python tools/bootstrap_hoard.py

This downloads CC0-1.0 licensed VRM Consortium sample avatars into
data/hoard/bases/ and updates the catalog to mark them as cached.

Exit codes:
    0 — all assets seeded successfully
    1 — one or more assets failed to download
"""
from __future__ import annotations

import sys
from pathlib import Path


def _find_project_root() -> Path:
    """Walk upward from this script to find the project root (by locating pyproject.toml)."""
    here = Path(__file__).resolve().parent
    for candidate in [here, here.parent, here.parent.parent]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    return here.parent


def main() -> int:
    """Run the bootstrap process and return an exit code."""
    project_root = _find_project_root()

    # Import the bootstrap module relative to the project
    sys.path.insert(0, str(project_root / "src"))

    from seidr_smidja.hoard.bootstrap import run_bootstrap

    catalog_path = project_root / "data" / "hoard" / "catalog.yaml"
    bases_dir = project_root / "data" / "hoard" / "bases"

    print("Seiðr-Smiðja Hoard Bootstrap")
    print("=" * 40)
    print(f"Catalog: {catalog_path}")
    print(f"Bases:   {bases_dir}")
    print()

    results = run_bootstrap(
        catalog_path=catalog_path,
        bases_dir=bases_dir,
        force=("--force" in sys.argv),
        verbose=True,
    )

    success_count = sum(1 for ok in results.values() if ok)
    fail_count = len(results) - success_count

    print()
    print(f"Bootstrap complete: {success_count} succeeded, {fail_count} failed")

    if fail_count > 0:
        print("WARNING: Some assets failed to download. Check network and URLs.")
        print("The forge can still run with any locally present assets.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
