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

    request = BuildRequest(
        spec_source=spec_path,
        base_asset_id="",  # Will be populated from spec
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

    # Load spec first to get base_asset_id (CLI knows the spec path)
    try:
        from seidr_smidja.loom.loader import load_spec

        spec = load_spec(spec_path)
        request.base_asset_id = spec.base_asset_id
    except Exception as exc:
        if output_json:
            click.echo(json.dumps({"success": False, "error": str(exc)}))
        else:
            click.echo(f"ERROR: Spec validation failed: {exc}", err=True)
        sys.exit(1)

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


@cli.command("version")
def cmd_version() -> None:
    """Print the seidr package version."""
    click.echo(f"seidr-smidja {_get_version()}")


def main() -> None:
    """Console script entry point."""
    cli(standalone_mode=True)
