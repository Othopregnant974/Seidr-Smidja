"""seidr_smidja.bridges.runstafr.cli — Rúnstafr CLI Bridge.

The `seidr` console script. A thin translation layer:
    protocol input (CLI args) → BuildRequest → dispatch() → BuildResponse
    → human-readable or JSON output.

Entry point: seidr_smidja.bridges.runstafr.cli:main
Registered in pyproject.toml as: seidr = "seidr_smidja.bridges.runstafr.cli:main"
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any

import click


def _get_version() -> str:
    """Return the package version."""
    try:
        from importlib.metadata import version

        return version("seidr-smidja")
    except Exception:
        return "0.1.0.dev0"


def _make_annall(config: dict[str, Any], project_root: Path, no_telemetry: bool) -> Any:
    """Construct the appropriate AnnallPort."""
    if no_telemetry:
        from seidr_smidja.annall.adapters.null import NullAnnallAdapter

        return NullAnnallAdapter()
    from seidr_smidja.annall.factory import make_annall

    return make_annall(config, project_root)


def _load_config(config_path: str | None, project_root: Path) -> dict[str, Any]:
    """Load config from file and environment."""
    from seidr_smidja.config import load_config

    if config_path:
        # Minimal support for explicit config override
        import yaml

        try:
            with open(config_path, encoding="utf-8") as fh:
                user_cfg = yaml.safe_load(fh) or {}
        except Exception as exc:
            click.echo(f"WARNING: Cannot read config file {config_path}: {exc}", err=True)
            user_cfg = {}
        base = load_config(project_root)
        # Simple deep merge
        from seidr_smidja.config import _deep_merge

        return _deep_merge(base, user_cfg)
    return load_config(project_root)


def _find_project_root() -> Path:
    """Locate the project root (contains config/defaults.yaml)."""
    from seidr_smidja.config import _find_config_root

    return _find_config_root()


@click.group()
@click.version_option(version=_get_version(), prog_name="seidr")
def cli() -> None:
    """Seiðr-Smiðja — agent-only VRM avatar smithy.

    Build, inspect, and export VRM avatars via CLI.
    """


@cli.command("build")
@click.argument("spec_path", type=click.Path(exists=True, path_type=Path))
@click.option("--out", "output_dir", default=None, type=click.Path(path_type=Path), help="Output directory.")
@click.option("--config", "config_path", default=None, help="Path to override config YAML.")
@click.option("--no-telemetry", is_flag=True, default=False, help="Disable Annáll telemetry (use NullAdapter).")
@click.option("--json", "output_json", is_flag=True, default=False, help="Output result as JSON.")
@click.option("--views", default=None, help="Comma-separated render view names to request.")
@click.option("--targets", default=None, help="Comma-separated compliance targets (VRCHAT,VTUBE_STUDIO).")
def cmd_build(
    spec_path: Path,
    output_dir: Path | None,
    config_path: str | None,
    no_telemetry: bool,
    output_json: bool,
    views: str | None,
    targets: str | None,
) -> None:
    """Build a VRM avatar from a Loom spec file.

    \b
    Examples:
        seidr build examples/spec_minimal.yaml
        seidr build examples/spec_full.yaml --out out/ --json
    """
    project_root = _find_project_root()
    config = _load_config(config_path, project_root)

    # Resolve output directory
    if output_dir is None:
        output_root = config.get("output", {}).get("root", "output")
        output_dir = (project_root / output_root).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    annall = _make_annall(config, project_root, no_telemetry)

    from seidr_smidja.bridges.core.dispatch import BuildRequest, dispatch

    render_views = [v.strip() for v in views.split(",")] if views else None
    compliance_targets = [t.strip() for t in targets.split(",")] if targets else None

    # H-009: Load spec ONCE here to extract base_asset_id for BuildRequest population
    # and for the display block below. Pass the pre-parsed spec dict to dispatch()
    # instead of re-reading the file — eliminates double I/O and the race window where
    # the file could change between the two reads.
    try:
        from seidr_smidja.loom.loader import load_spec

        spec = load_spec(spec_path)
    except Exception as exc:
        if output_json:
            click.echo(json.dumps({"success": False, "error": str(exc)}))
        else:
            click.echo(f"ERROR: Spec validation failed: {exc}", err=True)
        sys.exit(1)

    request = BuildRequest(
        # Pass the in-memory dict — dispatch will not re-read the file.
        spec_source=spec.to_dict(),
        base_asset_id=spec.base_asset_id,
        output_dir=output_dir,
        render_views=render_views,
        compliance_targets=compliance_targets,
        session_metadata={
            "agent_id": "cli",
            "bridge_type": "runstafr",
            "spec_path": str(spec_path),
        },
        request_id=str(uuid.uuid4()),
    )

    if not output_json:
        click.echo(f"Building avatar: {spec.display_name} ({spec.avatar_id})")
        click.echo(f"  Spec: {spec_path}")
        click.echo(f"  Base: {spec.base_asset_id}")
        click.echo(f"  Output: {output_dir}")

    response = dispatch(request, annall, config=config)

    if output_json:
        result_dict = {
            "success": response.success,
            "request_id": response.request_id,
            "vrm_path": str(response.vrm_path) if response.vrm_path else None,
            "render_paths": {k: str(v) for k, v in response.render_paths.items()},
            "compliance_passed": (
                response.compliance_report.passed if response.compliance_report else None
            ),
            "session_id": response.annall_session_id,
            "elapsed_seconds": response.elapsed_seconds,
            "errors": [
                {"stage": e.stage, "message": e.message}
                for e in response.errors
            ],
        }
        click.echo(json.dumps(result_dict, indent=2))
    else:
        _print_build_report(response)

    sys.exit(0 if response.success else 1)


def _print_build_report(response: Any) -> None:
    """Print a human-readable build report."""
    status = "SUCCESS" if response.success else "FAILED"
    click.echo(f"\nBuild {status} ({response.elapsed_seconds:.1f}s)")
    click.echo(f"  Session ID: {response.annall_session_id}")

    if response.vrm_path:
        click.echo(f"  VRM output: {response.vrm_path}")

    if response.render_paths:
        click.echo(f"  Renders ({len(response.render_paths)}):")
        for view, path in response.render_paths.items():
            click.echo(f"    {view}: {path}")
    else:
        click.echo("  Renders: none")

    if response.compliance_report:
        cr = response.compliance_report
        click.echo(f"  Compliance: {'PASS' if cr.passed else 'FAIL'}")
        for target_key, result in cr.results.items():
            click.echo(f"    {target_key}: {'PASS' if result.passed else 'FAIL'}")
            for v in result.violations:
                prefix = "    ERROR" if v.severity.value == "ERROR" else "    WARN "
                click.echo(f"      {prefix}: [{v.rule_id}] {v.description}")

    if response.errors:
        click.echo("  Errors:")
        for err in response.errors:
            click.echo(f"    [{err.stage}] {err.message}")


@cli.command("inspect")
@click.argument("vrm_path", type=click.Path(exists=True, path_type=Path))
@click.option("--targets", default=None, help="Compliance targets (default: all).")
@click.option("--json", "output_json", is_flag=True, default=False)
@click.option("--config", "config_path", default=None)
def cmd_inspect(
    vrm_path: Path,
    targets: str | None,
    output_json: bool,
    config_path: str | None,
) -> None:
    """Run Gate compliance check on an existing .vrm file."""
    project_root = _find_project_root()
    config = _load_config(config_path, project_root)

    target_list = [t.strip() for t in targets.split(",")] if targets else None

    try:
        from seidr_smidja.gate.gate import check as gate_check

        rules_dir = None
        gate_cfg = config.get("gate", {})
        rules_dir_str = gate_cfg.get("rules_dir")
        if rules_dir_str:
            rules_dir = (project_root / rules_dir_str).resolve()
        vrchat_tier = gate_cfg.get("vrchat_tier_target", "Good")

        report = gate_check(
            vrm_path=vrm_path,
            targets=target_list,
            rules_dir=rules_dir,
            vrchat_tier=vrchat_tier,
        )
    except Exception as exc:
        if output_json:
            click.echo(json.dumps({"success": False, "error": str(exc)}))
        else:
            click.echo(f"ERROR: Gate check failed: {exc}", err=True)
        sys.exit(3)

    if output_json:
        results_dict = {}
        for key, result in report.results.items():
            results_dict[key] = {
                "passed": result.passed,
                "violations": [
                    {
                        "rule_id": v.rule_id,
                        "severity": v.severity.value,
                        "description": v.description,
                        "actual_value": str(v.actual_value),
                        "limit_value": str(v.limit_value),
                    }
                    for v in result.violations
                ],
            }
        click.echo(
            json.dumps(
                {
                    "vrm_path": str(report.vrm_path),
                    "passed": report.passed,
                    "elapsed_seconds": report.elapsed_seconds,
                    "results": results_dict,
                },
                indent=2,
            )
        )
    else:
        click.echo(f"\nCompliance Report: {vrm_path.name}")
        click.echo(f"  Overall: {'PASS' if report.passed else 'FAIL'}")
        for key, result in report.results.items():
            click.echo(f"  {key}: {'PASS' if result.passed else 'FAIL'}")
            for v in result.violations:
                click.echo(f"    {'ERROR' if v.severity.value == 'ERROR' else 'WARN '}: [{v.rule_id}] {v.description}")

    sys.exit(0 if report.passed else 1)


@cli.command("bootstrap-hoard")
@click.option("--force", is_flag=True, default=False, help="Re-download even if cached.")
@click.option("--config", "config_path", default=None)
def cmd_bootstrap_hoard(force: bool, config_path: str | None) -> None:
    """Download seed VRM assets into the Hoard."""
    project_root = _find_project_root()
    config = _load_config(config_path, project_root)
    hoard_cfg = config.get("hoard", {})

    catalog_path = (
        project_root / hoard_cfg.get("catalog_path", "data/hoard/catalog.yaml")
    ).resolve()
    bases_dir = (
        project_root / hoard_cfg.get("bases_dir", "data/hoard/bases")
    ).resolve()

    from seidr_smidja.hoard.bootstrap import run_bootstrap

    results = run_bootstrap(catalog_path=catalog_path, bases_dir=bases_dir, force=force)
    sys.exit(0 if all(results.values()) else 1)


@cli.command("list-assets")
@click.option("--type", "asset_type", default=None, help="Filter by asset type (e.g. 'vrm_base').")
@click.option("--tag", "tag", default=None, help="Filter by tag (e.g. 'feminine').")
@click.option("--json", "output_json", is_flag=True, default=False, help="Output results as JSON.")
@click.option("--config", "config_path", default=None)
def cmd_list_assets(
    asset_type: str | None,
    tag: str | None,
    output_json: bool,
    config_path: str | None,
) -> None:
    """List available assets in the Hoard.

    \b
    Examples:
        seidr list-assets
        seidr list-assets --type vrm_base --tag feminine
        seidr list-assets --json
    """
    project_root = _find_project_root()
    config = _load_config(config_path, project_root)

    from seidr_smidja.hoard.local import LocalHoardAdapter
    from seidr_smidja.hoard.port import AssetFilter

    hoard = LocalHoardAdapter.from_config(config, project_root)
    filt = AssetFilter(
        asset_type=asset_type,
        tags=[tag] if tag else [],
    )

    try:
        assets = hoard.list_assets(filt)
    except Exception as exc:
        if output_json:
            click.echo(json.dumps({"success": False, "error": str(exc)}))
        else:
            click.echo(f"ERROR: Could not list assets: {exc}", err=True)
        sys.exit(1)

    if output_json:
        result_list = [
            {
                "asset_id": a.asset_id,
                "display_name": a.display_name,
                "asset_type": a.asset_type,
                "tags": a.tags,
                "vrm_version": a.vrm_version,
                "file_size_bytes": a.file_size_bytes,
                "cached": a.cached,
            }
            for a in assets
        ]
        click.echo(json.dumps(result_list, indent=2))
    else:
        if not assets:
            click.echo("No assets found matching the given filters.")
        else:
            click.echo(f"Hoard assets ({len(assets)} found):")
            for a in assets:
                cached_flag = "[cached]" if a.cached else "[not cached]"
                tags_str = ", ".join(a.tags) if a.tags else "no tags"
                click.echo(
                    f"  {a.asset_id}  ({a.display_name})  "
                    f"VRM {a.vrm_version}  {cached_flag}  tags: {tags_str}"
                )

    sys.exit(0)


@cli.command("version")
def cmd_version() -> None:
    """Print the seidr package version."""
    click.echo(f"seidr-smidja {_get_version()}")


@cli.group("brunhand")
def cmd_brunhand() -> None:
    """Brúarhönd — remote VRoid Studio control.

    Commands for operating a Horfunarþjónn daemon on a remote VRoid Studio host.

    \b
    Requires BRUNHAND_TOKEN environment variable (or --token flag).
    Requires --host <name> flag matching an entry in brunhand.hosts config.

    \b
    Examples:
        seidr brunhand health --host vroid-win
        seidr brunhand screenshot --host vroid-win --out ./caps/screen.png
        seidr brunhand click --host vroid-win 640 400
        seidr brunhand hotkey --host vroid-win ctrl s
        seidr brunhand vroid-export --host vroid-win --out character.vrm
    """


def _brunhand_common(
    host: str, token: str | None, config_path: str | None,
) -> tuple[Any, Any, str, Any]:
    """Shared setup for all brunhand subcommands.

    Returns (client, config, resolved_token, project_root).
    """
    project_root = _find_project_root()
    config = _load_config(config_path, project_root)

    # Resolve token: flag > env > config
    resolved_token = token or ""
    if not resolved_token:
        import os
        env_key = f"BRUNHAND_TOKEN_{host.upper().replace('-', '_').replace('.', '_')}"
        resolved_token = os.environ.get(env_key, "") or os.environ.get("BRUNHAND_TOKEN", "")

    return config, resolved_token, project_root


@cmd_brunhand.command("health")
@click.option("--host", required=True, help="Named host from brunhand.hosts config.")
@click.option("--token", default=None, envvar="BRUNHAND_TOKEN", help="Bearer token.")
@click.option("--config", "config_path", default=None)
@click.option("--json", "output_json", is_flag=True, default=False)
def brunhand_health(
    host: str, token: str | None, config_path: str | None, output_json: bool,
) -> None:
    """Health check against a Brúarhönd daemon."""
    config, resolved_token, _root = _brunhand_common(host, token, config_path)
    try:
        from seidr_smidja.brunhand.client.factory import make_client_from_config
        client = make_client_from_config(host, config, token_override=resolved_token or None)
        with client:
            result = client.health()
        if output_json:
            click.echo(json.dumps({
                "status": result.status,
                "daemon_version": result.daemon_version,
                "os_name": result.os_name,
                "uptime_seconds": result.uptime_seconds,
            }))
        else:
            up = f"{result.uptime_seconds:.0f}s"
            click.echo(
                f"Daemon {host}: {result.status}"
                f" (v{result.daemon_version}, {result.os_name}, up {up})"
            )
    except Exception as exc:
        if output_json:
            click.echo(json.dumps({"success": False, "error": str(exc)}))
        else:
            click.echo(f"ERROR: {exc}", err=True)
        sys.exit(1)


@cmd_brunhand.command("capabilities")
@click.option("--host", required=True, help="Named host from brunhand.hosts config.")
@click.option("--token", default=None, envvar="BRUNHAND_TOKEN")
@click.option("--config", "config_path", default=None)
@click.option("--json", "output_json", is_flag=True, default=False)
def brunhand_capabilities(
    host: str, token: str | None, config_path: str | None, output_json: bool,
) -> None:
    """Show capability manifest from a Brúarhönd daemon."""
    config, resolved_token, _root = _brunhand_common(host, token, config_path)
    try:
        from seidr_smidja.brunhand.client.factory import make_client_from_config
        client = make_client_from_config(host, config, token_override=resolved_token or None)
        with client:
            result = client.capabilities()
        if output_json:
            click.echo(json.dumps({
                "daemon_version": result.daemon_version,
                "os_name": result.os_name,
                "primitives": result.primitives,
            }, indent=2))
        else:
            click.echo(f"Daemon {host} capabilities (v{result.daemon_version}, {result.os_name}):")
            for name, info in sorted(result.primitives.items()):
                avail = "available" if info.get("available") else "unavailable"
                click.echo(f"  {name}: {avail}")
    except Exception as exc:
        if output_json:
            click.echo(json.dumps({"success": False, "error": str(exc)}))
        else:
            click.echo(f"ERROR: {exc}", err=True)
        sys.exit(1)


@cmd_brunhand.command("screenshot")
@click.option("--host", required=True, help="Named host from brunhand.hosts config.")
@click.option("--token", default=None, envvar="BRUNHAND_TOKEN")
@click.option("--config", "config_path", default=None)
@click.option("--out", "out_path", default=None, type=click.Path(), help="Save PNG to this path.")
@click.option("--json", "output_json", is_flag=True, default=False)
def brunhand_screenshot(
    host: str, token: str | None, config_path: str | None,
    out_path: str | None, output_json: bool,
) -> None:
    """Capture a screenshot from the remote VRoid host."""
    config, resolved_token, _root = _brunhand_common(host, token, config_path)
    try:
        from seidr_smidja.brunhand.client.factory import make_client_from_config
        client = make_client_from_config(host, config, token_override=resolved_token or None)
        with client:
            result = client.screenshot()
        if out_path and result.png_bytes:
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            Path(out_path).write_bytes(result.png_bytes)
        if output_json:
            click.echo(json.dumps({
                "success": result.success,
                "width": result.width, "height": result.height,
                "captured_at": result.captured_at,
                "saved_to": out_path,
                "byte_count": len(result.png_bytes),
            }))
        else:
            saved = f" → {out_path}" if out_path else ""
            click.echo(
                f"Screenshot: {result.width}x{result.height}"
                f" ({len(result.png_bytes)} bytes){saved}"
            )
    except Exception as exc:
        if output_json:
            click.echo(json.dumps({"success": False, "error": str(exc)}))
        else:
            click.echo(f"ERROR: {exc}", err=True)
        sys.exit(1)


@cmd_brunhand.command("click")
@click.argument("x", type=int)
@click.argument("y", type=int)
@click.option("--host", required=True)
@click.option("--token", default=None, envvar="BRUNHAND_TOKEN")
@click.option("--config", "config_path", default=None)
@click.option("--button", default="left", type=click.Choice(["left", "right", "middle"]))
@click.option("--clicks", default=1, type=int)
@click.option("--json", "output_json", is_flag=True, default=False)
def brunhand_click(
    x: int, y: int, host: str, token: str | None, config_path: str | None,
    button: str, clicks: int, output_json: bool,
) -> None:
    """Send a mouse click to the remote VRoid host."""
    config, resolved_token, _root = _brunhand_common(host, token, config_path)
    try:
        from seidr_smidja.brunhand.client.factory import make_client_from_config
        client = make_client_from_config(host, config, token_override=resolved_token or None)
        with client:
            result = client.click(x=x, y=y, button=button, clicks=clicks)
        if output_json:
            click.echo(json.dumps({"success": result.success, "x": result.x, "y": result.y}))
        else:
            click.echo(f"Clicked ({result.x}, {result.y}) button={button} x{clicks}")
    except Exception as exc:
        if output_json:
            click.echo(json.dumps({"success": False, "error": str(exc)}))
        else:
            click.echo(f"ERROR: {exc}", err=True)
        sys.exit(1)


@cmd_brunhand.command("type")
@click.argument("text")
@click.option("--host", required=True)
@click.option("--token", default=None, envvar="BRUNHAND_TOKEN")
@click.option("--config", "config_path", default=None)
@click.option("--json", "output_json", is_flag=True, default=False)
def brunhand_type(
    text: str, host: str, token: str | None, config_path: str | None, output_json: bool,
) -> None:
    """Type text on the remote VRoid host."""
    config, resolved_token, _root = _brunhand_common(host, token, config_path)
    try:
        from seidr_smidja.brunhand.client.factory import make_client_from_config
        client = make_client_from_config(host, config, token_override=resolved_token or None)
        with client:
            result = client.type_text(text=text)
        if output_json:
            click.echo(json.dumps({
                "success": result.success,
                "characters_typed": result.characters_typed,
            }))
        else:
            click.echo(f"Typed {result.characters_typed} chars")
    except Exception as exc:
        if output_json:
            click.echo(json.dumps({"success": False, "error": str(exc)}))
        else:
            click.echo(f"ERROR: {exc}", err=True)
        sys.exit(1)


@cmd_brunhand.command("hotkey")
@click.argument("keys", nargs=-1, required=True)
@click.option("--host", required=True)
@click.option("--token", default=None, envvar="BRUNHAND_TOKEN")
@click.option("--config", "config_path", default=None)
@click.option("--json", "output_json", is_flag=True, default=False)
def brunhand_hotkey(
    keys: tuple[str, ...], host: str, token: str | None,
    config_path: str | None, output_json: bool,
) -> None:
    """Send a hotkey combination to the remote VRoid host.

    \b
    Examples:
        seidr brunhand hotkey --host vroid-win ctrl s
        seidr brunhand hotkey --host vroid-win ctrl shift e
    """
    config, resolved_token, _root = _brunhand_common(host, token, config_path)
    try:
        from seidr_smidja.brunhand.client.factory import make_client_from_config
        client = make_client_from_config(host, config, token_override=resolved_token or None)
        with client:
            result = client.hotkey(keys=list(keys))
        if output_json:
            click.echo(json.dumps({"success": result.success, "keys": result.keys}))
        else:
            click.echo(f"Hotkey: {'+'.join(result.keys)}")
    except Exception as exc:
        if output_json:
            click.echo(json.dumps({"success": False, "error": str(exc)}))
        else:
            click.echo(f"ERROR: {exc}", err=True)
        sys.exit(1)


@cmd_brunhand.command("vroid-open")
@click.argument("project_path")
@click.option("--host", required=True)
@click.option("--token", default=None, envvar="BRUNHAND_TOKEN")
@click.option("--config", "config_path", default=None)
@click.option("--timeout", "wait_timeout", default=60.0, type=float)
@click.option("--json", "output_json", is_flag=True, default=False)
def brunhand_vroid_open(
    project_path: str, host: str, token: str | None, config_path: str | None,
    wait_timeout: float, output_json: bool,
) -> None:
    """Open a VRoid project file on the remote VRoid host."""
    config, resolved_token, _root = _brunhand_common(host, token, config_path)
    try:
        from seidr_smidja.brunhand.client.factory import make_client_from_config
        client = make_client_from_config(host, config, token_override=resolved_token or None)
        with client:
            result = client.vroid_open_project(
                project_path=project_path, wait_timeout_seconds=wait_timeout,
            )
        if output_json:
            click.echo(json.dumps({
                "success": result.success,
                "opened_path": result.opened_path,
                "elapsed_seconds": result.elapsed_seconds,
            }))
        else:
            click.echo(f"Opened: {result.opened_path} ({result.elapsed_seconds:.1f}s)")
    except Exception as exc:
        if output_json:
            click.echo(json.dumps({"success": False, "error": str(exc)}))
        else:
            click.echo(f"ERROR: {exc}", err=True)
        sys.exit(1)


@cmd_brunhand.command("vroid-export")
@click.option("--host", required=True)
@click.option("--out", "output_path", required=True, help="Output VRM path on the daemon host.")
@click.option("--token", default=None, envvar="BRUNHAND_TOKEN")
@click.option("--config", "config_path", default=None)
@click.option("--timeout", "wait_timeout", default=120.0, type=float)
@click.option("--no-overwrite", "no_overwrite", is_flag=True, default=False)
@click.option("--json", "output_json", is_flag=True, default=False)
def brunhand_vroid_export(
    host: str, output_path: str, token: str | None, config_path: str | None,
    wait_timeout: float, no_overwrite: bool, output_json: bool,
) -> None:
    """Export a VRM from VRoid Studio on the remote host."""
    config, resolved_token, _root = _brunhand_common(host, token, config_path)
    try:
        from seidr_smidja.brunhand.client.factory import make_client_from_config
        client = make_client_from_config(host, config, token_override=resolved_token or None)
        with client:
            result = client.vroid_export_vrm(
                output_path=output_path, overwrite=not no_overwrite,
                wait_timeout_seconds=wait_timeout,
            )
        if output_json:
            click.echo(json.dumps({"success": result.success, "exported_path": result.exported_path,
                                   "elapsed_seconds": result.elapsed_seconds}))
        else:
            click.echo(f"Exported: {result.exported_path} ({result.elapsed_seconds:.1f}s)")
    except Exception as exc:
        if output_json:
            click.echo(json.dumps({"success": False, "error": str(exc)}))
        else:
            click.echo(f"ERROR: {exc}", err=True)
        sys.exit(1)


@cmd_brunhand.command("vroid-save")
@click.option("--host", required=True)
@click.option("--token", default=None, envvar="BRUNHAND_TOKEN")
@click.option("--config", "config_path", default=None)
@click.option("--json", "output_json", is_flag=True, default=False)
def brunhand_vroid_save(
    host: str, token: str | None, config_path: str | None, output_json: bool,
) -> None:
    """Save the current VRoid project on the remote host (Ctrl+S)."""
    config, resolved_token, _root = _brunhand_common(host, token, config_path)
    try:
        from seidr_smidja.brunhand.client.factory import make_client_from_config
        client = make_client_from_config(host, config, token_override=resolved_token or None)
        with client:
            result = client.vroid_save_project()
        if output_json:
            click.echo(json.dumps({
                "success": result.success,
                "elapsed_seconds": result.elapsed_seconds,
            }))
        else:
            click.echo(f"Saved ({result.elapsed_seconds:.1f}s)")
    except Exception as exc:
        if output_json:
            click.echo(json.dumps({"success": False, "error": str(exc)}))
        else:
            click.echo(f"ERROR: {exc}", err=True)
        sys.exit(1)


def main() -> None:
    """Console script entry point."""
    cli(standalone_mode=True)
