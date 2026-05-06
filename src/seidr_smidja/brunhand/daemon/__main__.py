"""seidr_smidja.brunhand.daemon.__main__ — Horfunarþjónn CLI entry point.

Invocation:
    python -m seidr_smidja.brunhand.daemon [--host HOST] [--port PORT] [--config FILE]

Startup sequence:
  1. Parse CLI args.
  2. Load daemon config from layered config (env → user.yaml → defaults.yaml).
  3. Load bearer token — FAIL LOUD if not set.
  4. Refuse to bind non-localhost without allow_remote_bind: true (same defense
     pattern as Straumur H-005).
  5. Print startup banner.
  6. Start uvicorn.

See: docs/features/brunhand/ARCHITECTURE.md §III Daemon Layer Model
See: docs/features/brunhand/TAILSCALE.md for recommended remote deployment
"""
from __future__ import annotations

import argparse
import logging
import sys
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("brunhand.daemon")


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for the Horfunarþjónn daemon."""
    parser = argparse.ArgumentParser(
        prog="seidr-brunhand-daemon",
        description="Horfunarþjónn — the Watching-Daemon (Brúarhönd VRoid host server)",
    )
    parser.add_argument("--host", default=None, help="Bind address (overrides config)")
    parser.add_argument("--port", type=int, default=None, help="Port (overrides config)")
    parser.add_argument("--config", default=None, help="Path to override config YAML")
    parser.add_argument("--no-telemetry", action="store_true", default=False,
                        help="Disable Annáll telemetry (use NullAdapter)")
    args = parser.parse_args(argv)

    # Verify required daemon deps before loading anything else
    _check_daemon_deps()

    # Load extra config from --config flag if provided
    extra_cfg: dict[str, Any] = {}
    if args.config:
        try:
            import yaml
            with open(args.config, encoding="utf-8") as fh:
                extra_cfg = yaml.safe_load(fh) or {}
        except Exception as exc:
            logger.warning("Could not read --config file '%s': %s", args.config, exc)

    # Load daemon configuration
    from seidr_smidja.brunhand.daemon.config import load_daemon_config
    daemon_cfg = load_daemon_config(extra_cfg)

    # CLI args override config values
    if args.host:
        daemon_cfg["bind_address"] = args.host
    if args.port:
        daemon_cfg["port"] = args.port

    bind_address: str = daemon_cfg.get("bind_address", "127.0.0.1")
    port: int = daemon_cfg.get("port", 8848)
    allow_remote_bind: bool = daemon_cfg.get("allow_remote_bind", False)

    # ── Safety check: refuse non-localhost without allow_remote_bind ──────────
    # Same invariant as Straumur H-005. The daemon is not secure enough to
    # expose to arbitrary networks without explicit operator consent.
    _localhost_addresses = {"127.0.0.1", "::1", "localhost", "0.0.0.0"}
    is_localhost = bind_address in ("127.0.0.1", "::1", "localhost")

    if not is_localhost and not allow_remote_bind:
        logger.error(
            "Horfunarþjónn: refusing to bind to non-localhost address '%s' because "
            "brunhand.daemon.allow_remote_bind is not set to true in config/user.yaml. "
            "Add 'brunhand: {daemon: {allow_remote_bind: true}}' to config/user.yaml "
            "if Tailscale exposure is intentional. See docs/features/brunhand/TAILSCALE.md.",
            bind_address,
        )
        sys.exit(
            f"Brúarhönd daemon: refusing non-localhost bind to '{bind_address}' "
            f"without allow_remote_bind=true."
        )

    # ── Load bearer token — FAIL LOUD if missing ─────────────────────────────
    from seidr_smidja.brunhand.daemon.config import load_bearer_token
    try:
        token = load_bearer_token()
    except RuntimeError as exc:
        logger.error("Horfunarþjónn: %s", exc)
        sys.exit(str(exc))

    # ── Build Annáll adapter ──────────────────────────────────────────────────
    annall: Any = None
    if not args.no_telemetry:
        try:
            from seidr_smidja.annall.adapters.null import NullAnnallAdapter
            # Prefer null adapter for daemon-side to avoid dependency on forge config
            # Operators can configure a real SQLite adapter in config/user.yaml
            try:
                from seidr_smidja.annall.factory import make_annall
                from seidr_smidja.config import _find_config_root, load_config
                project_root = _find_config_root()
                cfg_full = load_config(project_root)
                annall = make_annall(cfg_full, project_root)
            except Exception:
                annall = NullAnnallAdapter()
        except Exception:
            annall = None

    # ── Build the FastAPI app ─────────────────────────────────────────────────
    from seidr_smidja.brunhand.daemon.app import create_daemon_app
    app = create_daemon_app(token=token, daemon_cfg=daemon_cfg, annall=annall)

    # ── Print startup banner ──────────────────────────────────────────────────
    _print_banner(bind_address, port, is_localhost, allow_remote_bind)

    # ── Start uvicorn ─────────────────────────────────────────────────────────
    try:
        import uvicorn
    except ImportError:
        logger.error(
            "uvicorn is not installed. Install with: pip install 'seidr-smidja[brunhand-daemon]'"
        )
        sys.exit("uvicorn not installed.")

    tls_cfg = daemon_cfg.get("tls", {})
    ssl_certfile = tls_cfg.get("cert_path") if tls_cfg.get("enabled") else None
    ssl_keyfile = tls_cfg.get("key_path") if tls_cfg.get("enabled") else None

    uvicorn.run(
        app,
        host=bind_address,
        port=port,
        ssl_certfile=ssl_certfile,
        ssl_keyfile=ssl_keyfile,
        log_level="info",
    )


def _check_daemon_deps() -> None:
    """Verify required daemon dependencies are installed. Fail loud if not."""
    missing: list[str] = []
    try:
        import pyautogui  # noqa: F401  # type: ignore[import]
    except ImportError:
        missing.append("pyautogui")
    try:
        import mss  # noqa: F401  # type: ignore[import]
    except ImportError:
        missing.append("mss")

    if missing:
        logger.error(
            "Horfunarþjónn: required daemon dependencies are missing: %s. "
            "Install with: pip install 'seidr-smidja[brunhand-daemon]'",
            ", ".join(missing),
        )
        sys.exit(
            f"Missing daemon dependencies: {', '.join(missing)}. "
            f"Install with: pip install 'seidr-smidja[brunhand-daemon]'"
        )


def _print_banner(
    bind_address: str,
    port: int,
    is_localhost: bool,
    allow_remote_bind: bool,
) -> None:
    """Print the daemon startup banner."""
    scheme = "http" if is_localhost else "https"
    health_url = f"{scheme}://{bind_address}:{port}/v1/brunhand/health"
    curl_cmd = f"curl {health_url}"

    lines = [
        "",
        "═" * 60,
        "  Horfunarþjónn — the Watching-Daemon",
        "  Brúarhönd v0.1 — VRoid Studio remote control",
        "═" * 60,
        f"  Bind:   {bind_address}:{port}",
        f"  Health: {health_url}",
        f"  Check:  {curl_cmd}",
        "",
    ]

    if not is_localhost:
        lines.insert(-1, "  *** REMOTE BINDING ACTIVE ***")
        lines.insert(-1, "  This daemon is reachable from the Tailscale network.")
        lines.insert(-1, "  Ensure Tailscale ACL restricts access to the forge only.")
        lines.insert(-1, "  See: docs/features/brunhand/TAILSCALE.md")
        lines.insert(-1, "")

    lines.append("═" * 60)
    lines.append("")

    for line in lines:
        logger.info(line)
        print(line)


if __name__ == "__main__":
    main()
