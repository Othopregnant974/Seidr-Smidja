"""seidr_smidja.annall.factory — AnnallPort factory.

Constructs the correct adapter from configuration at startup.
This is the only place that imports concrete adapter classes.
Domain code must never import concrete adapters directly.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from seidr_smidja.annall.port import AnnallPort


def make_annall(config: dict[str, Any], project_root: Path | None = None) -> AnnallPort:
    """Construct an AnnallPort from the given config dict.

    Args:
        config:       The resolved config dict from seidr_smidja.config.load_config().
        project_root: Optional explicit root for resolving relative paths in config.

    Returns:
        An AnnallPort-conforming adapter instance ready for use.

    Supported adapters (config key annall.adapter):
        "sqlite"  — SQLiteAnnallAdapter (default)
        "null"    — NullAnnallAdapter (no-op, useful for tests)
        "file"    — FileAnnallAdapter (JSON-lines)
    """
    root = project_root or Path(".")
    annall_cfg = config.get("annall", {})
    adapter_name = annall_cfg.get("adapter", "sqlite")

    if adapter_name == "null":
        from seidr_smidja.annall.adapters.null import NullAnnallAdapter

        return NullAnnallAdapter()  # type: ignore[return-value]

    if adapter_name == "file":
        from seidr_smidja.annall.adapters.file import FileAnnallAdapter

        file_cfg = annall_cfg.get("file", {})
        jsonl_path_str = file_cfg.get("jsonl_path", "data/annall/runs.jsonl")
        jsonl_path = (root / Path(jsonl_path_str)).resolve()
        return FileAnnallAdapter(jsonl_path)  # type: ignore[return-value]

    # Default: sqlite
    from seidr_smidja.annall.adapters.sqlite import SQLiteAnnallAdapter

    sqlite_cfg = annall_cfg.get("sqlite", {})
    db_path_str = sqlite_cfg.get("db_path", "data/annall/runs.sqlite")
    db_path = (root / Path(db_path_str)).resolve()
    return SQLiteAnnallAdapter(db_path)  # type: ignore[return-value]
