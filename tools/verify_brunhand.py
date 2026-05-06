"""tools/verify_brunhand.py — Brúarhönd forge-to-daemon connectivity smoke check.

Run this on the FORGE machine to verify connectivity to a Horfunarþjónn daemon.

Usage:
    python tools/verify_brunhand.py --host <host_name> [--token TOKEN]

Where <host_name> is the name of a host entry in brunhand.hosts in your config,
OR a literal hostname/IP if you use --token directly.

Examples:
    BRUNHAND_TOKEN=mytoken python tools/verify_brunhand.py --host vroid-win
    python tools/verify_brunhand.py --host vroid-win --token mytoken --port 8848

Exit codes:
    0 — all checks passed
    1 — one or more checks failed

See: docs/features/brunhand/ARCHITECTURE.md
See: docs/features/brunhand/TAILSCALE.md
"""
from __future__ import annotations

import argparse
import sys


def _check(label: str, fn) -> bool:  # type: ignore[type-arg]
    """Run a check, print pass/fail, return True on pass."""
    try:
        result = fn()
        result_str = f" ({result})" if result is not None else ""
        print(f"  PASS  {label}{result_str}")
        return True
    except Exception as exc:
        print(f"  FAIL  {label}: {exc}")
        return False


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="verify_brunhand",
        description="Verify forge-to-daemon Brúarhönd connectivity",
    )
    parser.add_argument(
        "--host", required=True,
        help="Named host from brunhand.hosts config (or literal hostname with --token)",
    )
    parser.add_argument("--token", default=None, help="Bearer token (overrides BRUNHAND_TOKEN env)")
    parser.add_argument("--port", type=int, default=None, help="Daemon port (overrides config)")
    parser.add_argument("--config", default=None, help="Path to override config YAML")
    parser.add_argument("--no-screenshot", action="store_true", default=False,
                        help="Skip screenshot check (faster, no visual capture)")
    args = parser.parse_args(argv)

    print()
    print("Brúarhönd Connectivity Verification")
    print("=" * 50)
    print(f"  Target host: {args.host}")
    print()

    all_passed = True

    # ── Check 1: Package importable ───────────────────────────────────────────
    def check_import() -> str:
        from seidr_smidja.brunhand.client.client import BrunhandClient  # noqa: F401
        from seidr_smidja.brunhand.exceptions import BrunhandError  # noqa: F401
        return "ok"

    all_passed &= _check("seidr_smidja.brunhand importable", check_import)

    # ── Load config ───────────────────────────────────────────────────────────
    config: dict = {}
    try:
        from seidr_smidja.config import _find_config_root, load_config
        project_root = _find_config_root()
        config = load_config(project_root)
        if args.config:
            import yaml
            with open(args.config, encoding="utf-8") as fh:
                extra = yaml.safe_load(fh) or {}
            from seidr_smidja.config import _deep_merge
            config = _deep_merge(config, extra)
        if args.port:
            config.setdefault("brunhand", {}).setdefault("daemon", {})["port"] = args.port
        print(f"  Config: loaded from {project_root}")
    except Exception as exc:
        print(f"  Config: could not load ({exc}), using defaults")

    # ── Build client ──────────────────────────────────────────────────────────
    client = None
    token = args.token

    # Try named host first, then fall back to literal hostname
    use_named_host = bool(
        any(
            isinstance(e, dict) and e.get("name") == args.host
            for e in config.get("brunhand", {}).get("hosts", [])
        )
    )

    def build_client_check() -> str:
        nonlocal client, token
        if use_named_host:
            from seidr_smidja.brunhand.client.factory import make_client_from_config
            client = make_client_from_config(args.host, config, token_override=token)
        else:
            # Literal hostname mode — requires --token
            import os
            resolved_token = token or os.environ.get("BRUNHAND_TOKEN", "").strip()
            if not resolved_token:
                raise RuntimeError(
                    "No token found. Pass --token or set BRUNHAND_TOKEN env var. "
                    "Or add the host to brunhand.hosts in config/user.yaml."
                )
            from seidr_smidja.brunhand.client.client import BrunhandClient
            port = args.port or 8848
            client = BrunhandClient(host=args.host, token=resolved_token, port=port)
        return "client built"

    passed = _check("Build BrunhandClient", build_client_check)
    all_passed &= passed

    if not passed or client is None:
        print()
        print("Cannot continue without a client. Check config and token.")
        sys.exit(1)

    # ── Check 2: Health endpoint ──────────────────────────────────────────────
    def health_check() -> str:
        result = client.health()  # type: ignore[union-attr]
        up = f"{result.uptime_seconds:.0f}s"
        return f"{result.status}, v{result.daemon_version}, {result.os_name}, up {up}"

    all_passed &= _check("Health endpoint (no auth)", health_check)

    # ── Check 3: Capabilities ─────────────────────────────────────────────────
    def capabilities_check() -> str:
        result = client.capabilities()  # type: ignore[union-attr]
        available_count = sum(
            1 for info in result.primitives.values() if info.get("available")
        )
        return f"{available_count}/{len(result.primitives)} primitives available"

    all_passed &= _check("Capabilities endpoint (auth)", capabilities_check)

    # ── Check 4: Screenshot (optional) ───────────────────────────────────────
    if not args.no_screenshot:
        def screenshot_check() -> str:
            result = client.screenshot()  # type: ignore[union-attr]
            return f"{result.width}x{result.height}, {len(result.png_bytes)} bytes"

        all_passed &= _check("Screenshot capture", screenshot_check)

    # ── Close client ──────────────────────────────────────────────────────────
    import contextlib
    with contextlib.suppress(Exception):
        client.close()  # type: ignore[union-attr]

    print()
    if all_passed:
        print("All checks passed. Brúarhönd connection is healthy.")
        sys.exit(0)
    else:
        print("Some checks failed. See above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
