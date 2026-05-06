"""seidr_smidja.brunhand.daemon.config — Daemon configuration loading.

Loads Horfunarþjónn configuration from the standard layered config system
(env vars → config/user.yaml → config/defaults.yaml → hard defaults).

Priority order for each value (first match wins):
  1. Environment variable (BRUNHAND_* prefix)
  2. config/user.yaml  brunhand.daemon.*
  3. config/defaults.yaml  brunhand.daemon.*
  4. Hard defaults in this module

TOKEN SECURITY: The bearer token is loaded here but never stored in the returned
config dict — it is held separately in memory and injected into Gæslumaðr.
The config dict returned by load_daemon_config() contains NO token value.

See: docs/features/brunhand/ARCHITECTURE.md §V Authentication Architecture
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ─── Hard defaults ───────────────────────────────────────────────────────────

_DEFAULTS: dict[str, Any] = {
    "bind_address": "127.0.0.1",
    "port": 8848,
    "allow_remote_bind": False,
    "tls": {
        "enabled": False,
        "cert_path": None,
        "key_path": None,
    },
    "project_root": "projects",
    "export_root": "exports",
    "primitive_defaults": {
        "wait_for_window_timeout": 30.0,
        "screenshot_compression": 6,
    },
    "rate_limit": False,
    "rate_limit_window_seconds": 60,
    "rate_limit_max": 120,
    "request_timeout_seconds": 60,
}


def load_daemon_config(extra_config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Load and merge daemon configuration from all sources.

    Returns a config dict with resolved daemon settings.
    The bearer token is NOT included — call load_bearer_token() separately.

    Args:
        extra_config: Optional override dict (e.g., from --config CLI arg).

    Returns:
        Merged daemon config dict with resolved values.
    """
    cfg: dict[str, Any] = dict(_DEFAULTS)
    cfg["tls"] = dict(_DEFAULTS["tls"])
    cfg["primitive_defaults"] = dict(_DEFAULTS["primitive_defaults"])

    # Merge from file-based config if available
    try:
        from seidr_smidja.config import _find_config_root, load_config
        project_root = _find_config_root()
        file_cfg = load_config(project_root)
        brunhand_cfg = file_cfg.get("brunhand", {})
        daemon_cfg = brunhand_cfg.get("daemon", {})
        _merge_into(cfg, daemon_cfg)
    except Exception as exc:
        logger.debug("Could not load file-based config for daemon: %s", exc)

    # Apply extra_config overrides (e.g., from --config CLI arg)
    if extra_config:
        daemon_override = extra_config.get("brunhand", {}).get("daemon", {})
        _merge_into(cfg, daemon_override)

    # Environment variable overrides (highest priority after arg)
    if os.environ.get("BRUNHAND_HOST"):
        cfg["bind_address"] = os.environ["BRUNHAND_HOST"]
    if os.environ.get("BRUNHAND_PORT"):
        try:
            cfg["port"] = int(os.environ["BRUNHAND_PORT"])
        except ValueError:
            logger.warning("BRUNHAND_PORT is not a valid integer: %s", os.environ["BRUNHAND_PORT"])
    if os.environ.get("BRUNHAND_ALLOW_REMOTE_BIND", "").lower() in ("1", "true", "yes"):
        cfg["allow_remote_bind"] = True
    if os.environ.get("BRUNHAND_TLS_CERT_PATH"):
        cfg["tls"]["cert_path"] = os.environ["BRUNHAND_TLS_CERT_PATH"]
    if os.environ.get("BRUNHAND_TLS_KEY_PATH"):
        cfg["tls"]["key_path"] = os.environ["BRUNHAND_TLS_KEY_PATH"]
    if os.environ.get("BRUNHAND_TLS_ENABLED", "").lower() in ("1", "true", "yes"):
        cfg["tls"]["enabled"] = True

    return cfg


def load_bearer_token() -> str:
    """Load the bearer token from environment or config file.

    NEVER logs or returns the token in a context where it could be leaked.

    Priority order (first match wins):
      1. BRUNHAND_TOKEN env var
      2. config/user.yaml  brunhand.daemon.token (inline value)
      3. config/user.yaml  brunhand.daemon.token_path (path to file containing token)

    Returns:
        The bearer token string (non-empty).

    Raises:
        RuntimeError: If no token can be found. The daemon must not start without one.
    """
    # Priority 1: env var
    token = os.environ.get("BRUNHAND_TOKEN", "").strip()
    if token:
        logger.debug("Daemon: bearer token loaded from BRUNHAND_TOKEN env var.")
        return token

    # Priority 2 & 3: config file
    try:
        from seidr_smidja.config import _find_config_root, load_config
        project_root = _find_config_root()
        file_cfg = load_config(project_root)
        brunhand_cfg = file_cfg.get("brunhand", {})
        daemon_cfg = brunhand_cfg.get("daemon", {})

        # Priority 2: inline token value in config
        inline_token = str(daemon_cfg.get("token", "") or "").strip()
        if inline_token:
            logger.debug("Daemon: bearer token loaded from config brunhand.daemon.token.")
            return inline_token

        # Priority 3: token_path — a file containing the token
        token_path_str = daemon_cfg.get("token_path")
        if token_path_str:
            token_path = Path(token_path_str)
            if not token_path.is_absolute():
                token_path = (project_root / token_path).resolve()
            if token_path.exists():
                file_token = token_path.read_text(encoding="utf-8").strip()
                if file_token:
                    logger.debug(
                        "Daemon: bearer token loaded from token_path file."
                    )
                    return file_token
            else:
                logger.warning("BRUNHAND_TOKEN token_path does not exist: %s", token_path)
    except Exception as exc:
        logger.debug("Could not load token from config file: %s", exc)

    raise RuntimeError(
        "BRUNHAND_TOKEN is not set. The daemon will not start without a bearer token.\n"
        "Set the BRUNHAND_TOKEN environment variable or configure brunhand.daemon.token "
        "in config/user.yaml."
    )


def _merge_into(base: dict[str, Any], override: dict[str, Any]) -> None:
    """Shallow merge override into base dict (mutates base)."""
    for key, value in override.items():
        if key == "tls" and isinstance(value, dict) and isinstance(base.get("tls"), dict):
            base["tls"].update(value)
        elif key == "primitive_defaults" and isinstance(value, dict):
            if isinstance(base.get("primitive_defaults"), dict):
                base["primitive_defaults"].update(value)
            else:
                base["primitive_defaults"] = dict(value)
        else:
            base[key] = value
