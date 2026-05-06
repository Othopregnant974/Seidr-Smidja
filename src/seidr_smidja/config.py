"""seidr_smidja.config — Configuration Loader
The Forge Worker's first stone: resolve and merge the layered configuration.

Layer order (later layers override earlier):
    1. config/defaults.yaml  (shipped defaults)
    2. config/user.yaml      (user overrides, gitignored)
    3. SEIDR_* environment variables
    4. Per-request overrides (BuildRequest fields — handled in bridges.core)

All paths in config values are treated as relative to the package root
(or an explicit output_root if set). Never rely on os.getcwd() silently.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# The package root is the directory containing this file's parent (src/seidr_smidja → project root).
_PACKAGE_DIR = Path(__file__).parent
_PROJECT_ROOT = _PACKAGE_DIR.parent.parent  # src/seidr_smidja → src → project_root


def _find_config_root() -> Path:
    """Locate the project root config/ directory.

    Searches upward from the package directory for config/defaults.yaml,
    then falls back to the _PROJECT_ROOT heuristic.
    """
    # Walk upward from package dir looking for config/defaults.yaml
    candidate = _PACKAGE_DIR
    for _ in range(6):  # Safety: max 6 levels up
        config_file = candidate / "config" / "defaults.yaml"
        if config_file.exists():
            return candidate
        candidate = candidate.parent
    # Fallback to calculated project root
    return _PROJECT_ROOT


def _load_yaml_safe(path: Path) -> dict[str, Any]:
    """Load a YAML file, returning an empty dict on any failure."""
    try:
        with path.open("r", encoding="utf-8") as fh:
            result = yaml.safe_load(fh)
            return result if isinstance(result, dict) else {}
    except FileNotFoundError:
        return {}
    except yaml.YAMLError as exc:
        logger.warning("Failed to parse config file %s: %s", path, exc)
        return {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge override into base, returning a new dict."""
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def _apply_env_vars(config: dict[str, Any]) -> dict[str, Any]:
    """Apply SEIDR_* environment variables into the config dict.

    Convention: SEIDR_BLENDER_EXECUTABLE → config["blender"]["executable"]
                SEIDR_ANNALL_ADAPTER     → config["annall"]["adapter"]
    Dots and nested keys are separated by double-underscore in env var names.
    """
    env_map = {
        "SEIDR_BLENDER_PATH": ("blender", "executable"),
        "SEIDR_BLENDER_EXECUTABLE": ("blender", "executable"),
        "SEIDR_BLENDER_TIMEOUT": ("blender", "timeout_seconds"),
        "SEIDR_ANNALL_ADAPTER": ("annall", "adapter"),
        "SEIDR_ANNALL_SQLITE_PATH": ("annall", "sqlite", "db_path"),
        "SEIDR_HOARD_CATALOG": ("hoard", "catalog_path"),
        "SEIDR_HOARD_BASES_DIR": ("hoard", "bases_dir"),
        "SEIDR_OUTPUT_ROOT": ("output", "root"),
        "SEIDR_GATE_VRCHAT_TIER": ("gate", "vrchat_tier_target"),
    }
    import copy as _copy
    # Deep copy so we never mutate the caller's config dict.
    # A shallow dict() copy would share nested sub-dicts with the original —
    # mutating them would silently corrupt the input.
    result = _copy.deepcopy(config)
    for env_key, path_tuple in env_map.items():
        val = os.environ.get(env_key)
        if val is None:
            continue
        # Navigate into nested dict, creating levels as needed
        node = result
        for part in path_tuple[:-1]:
            if part not in node or not isinstance(node[part], dict):
                node[part] = {}
            node = node[part]
        node[path_tuple[-1]] = val
    return result


def load_config(project_root: Path | None = None) -> dict[str, Any]:
    """Load the merged configuration for a Seiðr-Smiðja process.

    Args:
        project_root: Optional explicit project root path. If None, auto-detected.

    Returns:
        A merged configuration dict. All runtime consumers of config should
        call this once at startup and pass the result forward as needed.
    """
    root = project_root if project_root is not None else _find_config_root()
    defaults_path = root / "config" / "defaults.yaml"
    user_path = root / "config" / "user.yaml"

    config = _load_yaml_safe(defaults_path)
    if not config:
        logger.warning(
            "defaults.yaml not found at %s — using empty config base.", defaults_path
        )

    user_overrides = _load_yaml_safe(user_path)
    if user_overrides:
        config = _deep_merge(config, user_overrides)

    config = _apply_env_vars(config)

    # Attach the resolved project root for callers that need to resolve relative paths
    config["_project_root"] = str(root)
    return config


def resolve_path(config: dict[str, Any], relative_path: str) -> Path:
    """Resolve a config-relative path string to an absolute Path.

    Uses config["_project_root"] as the base. All data files, hoard bases,
    Annáll databases, etc. are relative to this root.

    Args:
        config: The config dict from load_config().
        relative_path: A forward-slash-separated path string from config.

    Returns:
        An absolute pathlib.Path.
    """
    root = Path(config.get("_project_root", "."))
    return (root / Path(relative_path)).resolve()
