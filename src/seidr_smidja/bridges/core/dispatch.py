"""seidr_smidja.bridges.core.dispatch — The Shared Anvil.

dispatch() is the single canonical orchestration path. Every Bridge sub-module
calls here. The Core has zero awareness of which Bridge called it.

Pipeline (fixed, non-skippable per ARCHITECTURE.md §II):
    1. Loom.load_and_validate(request.spec_source)
    2. Hoard.resolve(request.base_asset_id)
    3. Forge.build(spec, base_path, request.output_dir)
    4. OracleEye.render(forge_result.vrm_path, request.output_dir, request.render_views)
    5. Gate.check(forge_result.vrm_path, request.compliance_targets)

D-005: AnnallPort is injected — never a global.
D-006: Render failure is soft (VRM returned, success=False).
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from seidr_smidja.annall.port import AnnallEvent, AnnallPort, SessionOutcome
from seidr_smidja.gate.models import ComplianceReport

# ─── Data Models ─────────────────────────────────────────────────────────────


@dataclass
class BuildRequest:
    """Normalized build request passed to the Shared Anvil from any Bridge.

    All Bridge sub-modules construct one of these from their protocol-native input
    and call dispatch(request, annall).
    """

    spec_source: Path | dict[str, Any]  # YAML file path or raw dict
    base_asset_id: str                  # Hoard catalog key
    output_dir: Path                    # Where .vrm and renders go
    render_views: list[str] | None = None       # None = full standard set
    compliance_targets: list[str] | None = None  # None = all targets
    session_metadata: dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class BuildError:
    """Structured error from a specific pipeline stage."""

    stage: str       # "loom" | "hoard" | "forge" | "oracle_eye" | "gate" | "core"
    error_type: str  # Exception class name
    message: str
    detail: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_exception(cls, stage: str, exc: Exception) -> BuildError:
        return cls(
            stage=stage,
            error_type=type(exc).__name__,
            message=str(exc),
        )


@dataclass
class BuildResponse:
    """The forge's complete answer to a BuildRequest.

    Invariant: dispatch() always returns a BuildResponse — success or failure.
    It never propagates an exception to the calling Bridge sub-module.
    """

    request_id: str
    success: bool
    vrm_path: Path | None = None
    render_paths: dict[str, Path] = field(default_factory=dict)
    compliance_report: ComplianceReport | None = None
    annall_session_id: str = ""
    elapsed_seconds: float = 0.0
    errors: list[BuildError] = field(default_factory=list)


# ─── Dispatch ────────────────────────────────────────────────────────────────


def dispatch(
    request: BuildRequest,
    annall: AnnallPort,
    hoard: Any | None = None,
    config: dict[str, Any] | None = None,
) -> BuildResponse:
    """Execute the full forge pipeline for one build request.

    Args:
        request: The normalized build request.
        annall:  An AnnallPort instance (injected at startup, D-005).
        hoard:   Optional HoardPort instance. If None, a LocalHoardAdapter is
                 constructed from config. (For testing: inject a mock hoard.)
        config:  Optional config dict. Used for path resolution.

    Returns:
        BuildResponse — always. Never raises to the calling Bridge.
    """
    overall_start = time.monotonic()
    errors: list[BuildError] = []

    # Open Annáll session
    session_id = annall.open_session(request.session_metadata)

    vrm_path: Path | None = None
    render_paths: dict[str, Path] = {}
    compliance_report: ComplianceReport | None = None

    try:
        # ── Step 1: Loom validation ───────────────────────────────────────────
        # AUDIT-005: Pass annall and session_id so Loom logs its own 'loom.validated'
        # event directly (D-005 Option B). We no longer log on the Loom's behalf here.
        spec = None
        try:
            from seidr_smidja.loom.loader import load_spec

            spec = load_spec(request.spec_source, annall=annall, session_id=session_id)
            # NOTE: loom.validated event is now emitted by load_spec() itself (AUDIT-005).
        except Exception as exc:
            err = BuildError.from_exception("loom", exc)
            errors.append(err)
            annall.log_event(
                session_id,
                AnnallEvent.error("loom.failed", {"error": str(exc)}),
            )
            # Loom failure — cannot proceed
            return _build_response(
                request,
                session_id,
                annall,
                success=False,
                vrm_path=None,
                render_paths={},
                compliance_report=None,
                errors=errors,
                elapsed=time.monotonic() - overall_start,
                summary=f"Loom validation failed: {exc}",
            )

        # ── Step 2: Hoard resolution ──────────────────────────────────────────
        # AUDIT-005: Pass annall and session_id so Hoard logs its own 'hoard.resolved'
        # event directly (D-005 Option B). We no longer log on the Hoard's behalf here.
        base_asset_path: Path | None = None
        try:
            resolved_hoard = _get_hoard(hoard, config)
            base_asset_path = resolved_hoard.resolve(
                spec.base_asset_id, annall=annall, session_id=session_id
            )
            # NOTE: hoard.resolved event is now emitted by resolve() itself (AUDIT-005).
        except Exception as exc:
            err = BuildError.from_exception("hoard", exc)
            errors.append(err)
            annall.log_event(
                session_id,
                AnnallEvent.error("hoard.failed", {"error": str(exc)}),
            )
            return _build_response(
                request,
                session_id,
                annall,
                success=False,
                vrm_path=None,
                render_paths={},
                compliance_report=None,
                errors=errors,
                elapsed=time.monotonic() - overall_start,
                summary=f"Hoard failed: {exc}",
            )

        # ── Step 3: Forge build ───────────────────────────────────────────────
        forge_success = False
        try:
            from seidr_smidja.forge.runner import build as forge_build

            forge_result = forge_build(
                spec=spec,
                base_asset=base_asset_path,
                output_dir=request.output_dir,
                config=config,
                annall=annall,
                session_id=session_id,
            )
            vrm_path = forge_result.vrm_path
            forge_success = forge_result.success
            if not forge_success:
                errors.append(
                    BuildError(
                        stage="forge",
                        error_type="ForgeBuildFailure",
                        message=f"Blender exited with code {forge_result.exit_code}",
                        detail={
                            "exit_code": forge_result.exit_code,
                            "stderr_tail": forge_result.stderr_capture[-500:],
                        },
                    )
                )
        except Exception as exc:
            err = BuildError.from_exception("forge", exc)
            errors.append(err)
            annall.log_event(
                session_id,
                AnnallEvent.error("forge.failed", {"error": str(exc)}),
            )
            # No VRM — cannot render or gate-check
            return _build_response(
                request,
                session_id,
                annall,
                success=False,
                vrm_path=None,
                render_paths={},
                compliance_report=None,
                errors=errors,
                elapsed=time.monotonic() - overall_start,
                summary=f"Forge failed: {exc}",
            )

        if not forge_success or vrm_path is None:
            # Forge subprocess failed — cannot render or gate-check
            return _build_response(
                request,
                session_id,
                annall,
                success=False,
                vrm_path=None,
                render_paths={},
                compliance_report=None,
                errors=errors,
                elapsed=time.monotonic() - overall_start,
                summary="Forge build failed.",
            )

        # ── Step 4: Oracle Eye render ─────────────────────────────────────────
        # D-006: Render failure is soft — return VRM + warnings, success=False.
        # The pipeline always calls Oracle Eye after a successful Forge build.
        try:
            from seidr_smidja.oracle_eye.eye import render as eye_render

            render_result = eye_render(
                vrm_path=vrm_path,
                output_dir=request.output_dir,
                views=request.render_views,
                config=config,
                annall=annall,
                session_id=session_id,
            )
            render_paths = render_result.render_paths
            if not render_result.success:
                errors.append(
                    BuildError(
                        stage="oracle_eye",
                        error_type="RenderFailure",
                        message=(
                            f"Oracle Eye render incomplete: {render_result.errors}"
                        ),
                        detail={
                            "views_rendered": list(render_paths.keys()),
                            "errors": render_result.errors,
                        },
                    )
                )
        except Exception as exc:
            err = BuildError.from_exception("oracle_eye", exc)
            errors.append(err)
            annall.log_event(
                session_id,
                AnnallEvent.error("oracle_eye.failed", {"error": str(exc)}),
            )
            # Soft failure: continue to Gate with the VRM we have

        # ── Step 5: Gate compliance check ────────────────────────────────────
        try:
            from seidr_smidja.gate.gate import check as gate_check

            rules_dir = None
            if config:
                from seidr_smidja.config import resolve_path

                gate_rules_dir_str = config.get("gate", {}).get("rules_dir")
                if gate_rules_dir_str:
                    rules_dir = resolve_path(config, gate_rules_dir_str)

            vrchat_tier = (config or {}).get("gate", {}).get("vrchat_tier_target", "Good")

            compliance_report = gate_check(
                vrm_path=vrm_path,
                targets=request.compliance_targets,
                rules_dir=rules_dir,
                vrchat_tier=vrchat_tier,
                annall=annall,
                session_id=session_id,
            )
            if not compliance_report.passed:
                violations = compliance_report.all_violations()
                errors.append(
                    BuildError(
                        stage="gate",
                        error_type="ComplianceFailure",
                        message=f"Compliance check failed: {len(violations)} violation(s)",
                        detail={
                            "violations_count": len(violations),
                            "violations": [
                                {
                                    "rule_id": v.rule_id,
                                    "severity": v.severity.value,
                                    "description": v.description,
                                }
                                for v in violations[:20]  # Cap at 20 for the detail dict
                            ],
                        },
                    )
                )
        except Exception as exc:
            err = BuildError.from_exception("gate", exc)
            errors.append(err)
            annall.log_event(
                session_id,
                AnnallEvent.error("gate.failed", {"error": str(exc)}),
            )

    except Exception as exc:
        # Catch-all for any unexpected error in the Core itself
        errors.append(BuildError.from_exception("core", exc))
        annall.log_event(
            session_id,
            AnnallEvent.error("core.failed", {"error": str(exc)}),
        )

    # ── Assemble final response ───────────────────────────────────────────────
    overall_success = (
        len(errors) == 0
        and vrm_path is not None
        and (compliance_report is None or compliance_report.passed)
    )

    summary = (
        "Build successful."
        if overall_success
        else f"Build failed: {errors[0].message if errors else 'unknown'}"
    )

    return _build_response(
        request,
        session_id,
        annall,
        success=overall_success,
        vrm_path=vrm_path,
        render_paths=render_paths,
        compliance_report=compliance_report,
        errors=errors,
        elapsed=time.monotonic() - overall_start,
        summary=summary,
    )


def _build_response(
    request: BuildRequest,
    session_id: str,
    annall: AnnallPort,
    success: bool,
    vrm_path: Path | None,
    render_paths: dict[str, Path],
    compliance_report: ComplianceReport | None,
    errors: list[BuildError],
    elapsed: float,
    summary: str,
) -> BuildResponse:
    """Close the Annáll session and return a BuildResponse."""
    annall.close_session(
        session_id,
        SessionOutcome(success=success, summary=summary, elapsed_seconds=elapsed),
    )
    return BuildResponse(
        request_id=request.request_id,
        success=success,
        vrm_path=vrm_path,
        render_paths=render_paths,
        compliance_report=compliance_report,
        annall_session_id=session_id,
        elapsed_seconds=elapsed,
        errors=errors,
    )


def _get_hoard(hoard: Any | None, config: dict[str, Any] | None) -> Any:
    """Return the hoard instance, constructing a default LocalHoardAdapter if needed."""
    if hoard is not None:
        return hoard
    from seidr_smidja.hoard.local import LocalHoardAdapter

    cfg = config or {}
    hoard_cfg = cfg.get("hoard", {})
    project_root = cfg.get("_project_root", ".")
    from pathlib import Path as _Path

    catalog = (_Path(project_root) / hoard_cfg.get("catalog_path", "data/hoard/catalog.yaml")).resolve()
    bases = (_Path(project_root) / hoard_cfg.get("bases_dir", "data/hoard/bases")).resolve()
    return LocalHoardAdapter(catalog_path=catalog, bases_dir=bases)
