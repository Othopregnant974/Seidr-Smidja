"""tools/verify_install.py — Verify that seidr_smidja is installed correctly.

Run after installation:
    python tools/verify_install.py

Checks:
    1. Package is importable
    2. Core domains load without error
    3. Blender executable location (if configured)
    4. Hoard catalog is readable (if seeded)

Exit codes:
    0 — all checks passed
    1 — one or more checks failed
"""
from __future__ import annotations

import sys
from pathlib import Path


def _check(label: str, fn) -> bool:  # type: ignore[type-arg]
    """Run a check, print pass/fail, return True on pass."""
    try:
        fn()
        print(f"  PASS  {label}")
        return True
    except Exception as exc:
        print(f"  FAIL  {label}: {exc}")
        return False


def main() -> int:
    """Run all verification checks."""
    # Ensure src is on the path when running from the tools/ directory
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root / "src"))

    print("Seiðr-Smiðja Installation Verification")
    print("=" * 40)
    failures = 0

    # ── 1. Core package import ────────────────────────────────────────────────
    if not _check("import seidr_smidja", lambda: __import__("seidr_smidja")):
        failures += 1

    # ── 2. Loom ───────────────────────────────────────────────────────────────
    def _check_loom() -> None:
        from seidr_smidja.loom.schema import AvatarSpec
        from seidr_smidja.loom.loader import load_spec
        _ = load_spec({
            "spec_version": "1.0",
            "avatar_id": "verify_test",
            "display_name": "Verify Test",
            "base_asset_id": "vroid/sample_a",
            "metadata": {"author": "verify"},
        })

    if not _check("Loom: load_spec from dict", _check_loom):
        failures += 1

    # ── 3. Gate ───────────────────────────────────────────────────────────────
    def _check_gate() -> None:
        from seidr_smidja.gate.gate import list_rules
        from seidr_smidja.gate.models import ComplianceTarget

        rules_dir = project_root / "data" / "gate"
        if not rules_dir.exists():
            raise FileNotFoundError(f"Gate rules dir not found: {rules_dir}")
        rules = list_rules(ComplianceTarget.VRCHAT, rules_dir=rules_dir)
        if not rules:
            raise ValueError("No VRChat rules loaded")

    if not _check("Gate: VRChat rules loaded", _check_gate):
        failures += 1

    # ── 4. Annáll ─────────────────────────────────────────────────────────────
    def _check_annall() -> None:
        from seidr_smidja.annall.adapters.null import NullAnnallAdapter
        from seidr_smidja.annall.port import AnnallPort

        adapter = NullAnnallAdapter()
        assert isinstance(adapter, AnnallPort)

    if not _check("Annáll: NullAnnallAdapter satisfies protocol", _check_annall):
        failures += 1

    # ── 5. Hoard catalog ──────────────────────────────────────────────────────
    def _check_hoard() -> None:
        from seidr_smidja.hoard.local import LocalHoardAdapter

        catalog = project_root / "data" / "hoard" / "catalog.yaml"
        bases = project_root / "data" / "hoard" / "bases"
        if not catalog.exists():
            raise FileNotFoundError(
                f"Hoard catalog not found: {catalog}\n"
                "  → Run: python tools/bootstrap_hoard.py"
            )
        adapter = LocalHoardAdapter(catalog_path=catalog, bases_dir=bases)
        assets = adapter.list_assets()
        cached = [a for a in assets if a.cached]
        if not cached:
            raise ValueError(
                "No cached assets found in Hoard.\n"
                "  → Run: python tools/bootstrap_hoard.py"
            )

    if not _check("Hoard: catalog readable and seeded", _check_hoard):
        failures += 1

    # ── 6. Blender path (optional) ────────────────────────────────────────────
    def _check_blender() -> None:
        import os

        from seidr_smidja._internal.blender_runner import resolve_blender_executable, BlenderNotFoundError

        try:
            blender_path = resolve_blender_executable({})
            print(f"         (found: {blender_path})", end="")
        except BlenderNotFoundError:
            raise FileNotFoundError(
                "Blender not found. Set SEIDR_BLENDER_PATH to enable build."
            )

    blender_ok = _check("Blender: executable found (optional)", _check_blender)
    if not blender_ok:
        print("         (builds will fail, Gate and inspect work without Blender)")

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    required_failures = failures  # blender is optional, counted separately
    if required_failures == 0:
        print("All required checks passed.")
        if not blender_ok:
            print("Blender not configured — run with SEIDR_BLENDER_PATH for builds.")
        return 0
    else:
        print(f"{required_failures} required check(s) failed. See above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
