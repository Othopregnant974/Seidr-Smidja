"""
Rúnstafr — the CLI Bridge.

The `seidr` command-line tool. Parses CLI arguments using Click, constructs a
BuildRequest, calls bridges.core.dispatch(), and formats the BuildResponse as
human-readable terminal output with exit codes.

Entry point: seidr_smidja.bridges.runstafr.cli:main
Registered in pyproject.toml as the `seidr` console script.

No forge logic lives here. Rúnstafr is a door, not the forge.
"""
