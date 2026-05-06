"""tools/brunhand_daemon.py — Horfunarþjónn operator launcher.

Convenience launcher for the Brúarhönd daemon on the VRoid Studio host.
Equivalent to running:
    python -m seidr_smidja.brunhand.daemon [args]

But with a friendlier operator interface and pre-flight checks.

Usage:
    python tools/brunhand_daemon.py [--host HOST] [--port PORT] [--config FILE]
    python tools/brunhand_daemon.py --help

Run this script on the machine where VRoid Studio is running.
The forge machine connects to this daemon remotely via Tailscale (or localhost).

Prerequisites:
    pip install 'seidr-smidja[brunhand-daemon]'
    export BRUNHAND_TOKEN=<your-secret-token>  (or set in config/user.yaml)

See: docs/features/brunhand/ARCHITECTURE.md
See: docs/features/brunhand/TAILSCALE.md
"""
from __future__ import annotations


def _check_environment() -> list[str]:
    """Run pre-flight checks and return a list of warnings."""
    warnings: list[str] = []

    # Check BRUNHAND_TOKEN
    import os
    token = os.environ.get("BRUNHAND_TOKEN", "").strip()
    if not token:
        warnings.append(
            "BRUNHAND_TOKEN environment variable is not set. "
            "The daemon will fail unless token is configured in user.yaml."
        )

    # Check daemon deps
    missing: list[str] = []
    try:
        import pyautogui  # noqa: F401  # type: ignore[import]
    except ImportError:
        missing.append("pyautogui")
    try:
        import mss  # noqa: F401  # type: ignore[import]
    except ImportError:
        missing.append("mss")
    try:
        import uvicorn  # noqa: F401  # type: ignore[import]
    except ImportError:
        missing.append("uvicorn")

    if missing:
        warnings.append(
            f"Missing daemon dependencies: {', '.join(missing)}. "
            f"Install with: pip install 'seidr-smidja[brunhand-daemon]'"
        )

    return warnings


def main() -> None:
    """Launch the Horfunarþjónn daemon."""
    print()
    print("Brúarhönd Daemon Launcher")
    print("=" * 50)

    warnings = _check_environment()
    if warnings:
        print()
        print("Pre-flight warnings:")
        for w in warnings:
            print(f"  WARNING: {w}")
        print()

    print("Starting Horfunarþjónn (Watching-Daemon)...")
    print()

    # Delegate to the module's main() — passes sys.argv[1:] through
    from seidr_smidja.brunhand.daemon.__main__ import main as daemon_main
    daemon_main()


if __name__ == "__main__":
    main()
