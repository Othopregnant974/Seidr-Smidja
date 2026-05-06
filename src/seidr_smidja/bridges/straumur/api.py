"""seidr_smidja.bridges.straumur.api — Straumur REST Bridge.

FastAPI application. Thin translation layer:
    HTTP request → BuildRequest → dispatch() → BuildResponse → HTTP response

Run with:
    python -m seidr_smidja.bridges.straumur
    uvicorn seidr_smidja.bridges.straumur.api:app

Endpoints:
    POST /v1/avatars         — build an avatar
    POST /v1/inspect         — standalone Gate check
    GET  /v1/assets          — list Hoard assets
    GET  /v1/health          — health check
    GET  /v1/avatars/{run_id} — retrieve session record
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# FastAPI is an optional dependency (bundled in defaults but might be absent in
# minimal installs). Import lazily so the module is importable without FastAPI.
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel as _BaseModel
    from pydantic import Field as _Field

    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False
    FastAPI = None  # type: ignore[assignment,misc]
    HTTPException = None  # type: ignore[assignment]
    _BaseModel = object  # type: ignore[assignment,misc]
    _Field = lambda *a, **kw: None  # type: ignore[assignment]


def _require_fastapi() -> None:
    if not _FASTAPI_AVAILABLE:
        raise ImportError(
            "FastAPI is required for the Straumur REST bridge. "
            "Install with: pip install 'seidr-smidja[rest]'"
        )


# ─── Request / Response models ───────────────────────────────────────────────


class BuildRequestBody(_BaseModel):  # type: ignore[misc]
    """Request body for POST /v1/avatars."""

    spec: Any  # dict (inline spec) or string (file path)
    output_dir: str | None = None
    render_views: list[str] | None = None
    compliance_targets: list[str] | None = None
    session_metadata: dict[str, Any] = {}


class InspectRequestBody(_BaseModel):  # type: ignore[misc]
    """Request body for POST /v1/inspect."""

    vrm_path: str
    targets: list[str] | None = None


class BrunhandDispatchBody(_BaseModel):  # type: ignore[misc]
    """Request body for POST /v1/brunhand/dispatch."""

    host_name: str
    primitive: str
    primitive_args: dict[str, Any] = {}
    agent_id: str = ""
    run_id: str | None = None
    token: str | None = None  # Optional per-request token override


# ─── App factory ─────────────────────────────────────────────────────────────


def _validate_vrm_path_for_inspect(vrm_path: Path, cfg: dict[str, Any], project_root: Path) -> None:
    """H-004: Validate that a VRM path submitted to POST /v1/inspect is safe to open.

    Checks:
        1. The path must end in .vrm (case-insensitive) — prevent reading arbitrary files.
        2. The resolved path must be inside an allow-listed directory tree.
           Default allow-list: <project_root>/output/ and <project_root>/data/hoard/bases/
           Operators may add additional roots via config key straumur.inspect_roots (list).

    Raises:
        HTTPException(400): If the path fails any check.
    """
    _require_fastapi()

    if vrm_path.suffix.lower() != ".vrm":
        raise HTTPException(  # type: ignore[misc]
            status_code=400,
            detail={
                "error": "invalid_vrm_path",
                "message": "vrm_path must refer to a .vrm file (by extension).",
            },
        )

    resolved = vrm_path.resolve()

    # Build the allow-list from config + safe defaults
    output_root_str = cfg.get("output", {}).get("root", "output")
    hoard_bases_str = cfg.get("hoard", {}).get("bases_dir", "data/hoard/bases")
    default_roots = [
        (project_root / output_root_str).resolve(),
        (project_root / hoard_bases_str).resolve(),
    ]
    extra_roots_cfg = cfg.get("straumur", {}).get("inspect_roots", [])
    extra_roots = [Path(r).resolve() for r in extra_roots_cfg if r]
    allow_list = default_roots + extra_roots

    for allowed_root in allow_list:
        try:
            resolved.relative_to(allowed_root)
            return  # Path is inside this allowed root — accept
        except ValueError:
            continue

    logger.warning(
        "Straumur H-004: rejected vrm_path outside allow-list: %s (allowed: %s)",
        resolved,
        [str(r) for r in allow_list],
    )
    raise HTTPException(  # type: ignore[misc]
        status_code=400,
        detail={
            "error": "vrm_path_not_allowed",
            "message": (
                "vrm_path must be inside the configured output or hoard directories. "
                "Path traversal or arbitrary file access is not permitted."
            ),
        },
    )


def create_app(config: dict[str, Any] | None = None) -> Any:
    """Create the FastAPI application.

    Args:
        config: Optional config dict. If None, loaded from defaults on first request.

    Returns:
        A configured FastAPI app instance.
    """
    _require_fastapi()

    app = FastAPI(
        title="Seiðr-Smiðja REST Bridge",
        description="Agent-facing HTTP API for the VRM avatar smithy.",
        version="0.1.0",
    )

    _config: dict[str, Any] = config or {}

    def _get_config() -> dict[str, Any]:
        nonlocal _config
        if not _config:
            from seidr_smidja.config import load_config

            _config = load_config()
        return _config

    # H-014: Cache the annall adapter — constructing a new SQLiteAnnallAdapter on
    # every request calls PRAGMA journal_mode=WAL + CREATE TABLE IF NOT EXISTS each
    # time. The adapter is expensive to construct; cache it alongside _config.
    _annall_instance: Any = None

    def _get_annall() -> Any:
        nonlocal _annall_instance
        if _annall_instance is None:
            from seidr_smidja.annall.factory import make_annall
            from seidr_smidja.config import _find_config_root

            cfg = _get_config()
            _annall_instance = make_annall(cfg, _find_config_root())
        return _annall_instance

    @app.get("/v1/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    @app.post("/v1/avatars")
    async def build_avatar(body: BuildRequestBody) -> JSONResponse:  # type: ignore[misc]
        from seidr_smidja.bridges.core.dispatch import BuildRequest, dispatch
        from seidr_smidja.config import _find_config_root

        cfg = _get_config()
        project_root = _find_config_root()

        output_dir_str = body.output_dir
        if output_dir_str:
            output_dir = Path(output_dir_str).resolve()
        else:
            output_root = cfg.get("output", {}).get("root", "output")
            output_dir = (project_root / output_root).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        spec_input = body.spec
        if isinstance(spec_input, str):
            spec_source: Path | dict[str, Any] = Path(spec_input)
        else:
            spec_source = spec_input or {}

        base_asset_id = ""
        if isinstance(spec_source, dict):
            base_asset_id = spec_source.get("base_asset_id", "")

        annall = _get_annall()
        request = BuildRequest(
            spec_source=spec_source,
            base_asset_id=base_asset_id,
            output_dir=output_dir,
            render_views=body.render_views,
            compliance_targets=body.compliance_targets,
            session_metadata={
                "agent_id": "rest_client",
                "bridge_type": "straumur",
                **body.session_metadata,
            },
            request_id=str(uuid.uuid4()),
        )

        response = dispatch(request, annall, config=cfg)

        result = {
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

        status_code = 200 if response.success else 422
        return JSONResponse(content=result, status_code=status_code)

    @app.post("/v1/inspect")
    async def inspect_vrm(body: InspectRequestBody) -> JSONResponse:  # type: ignore[misc]
        from seidr_smidja.config import _find_config_root
        from seidr_smidja.gate.gate import check as gate_check

        cfg = _get_config()
        project_root = _find_config_root()
        vrm_path = Path(body.vrm_path)

        # H-004: Reject vrm_paths that are not .vrm or that escape allowed roots.
        _validate_vrm_path_for_inspect(vrm_path, cfg, project_root)

        gate_cfg = cfg.get("gate", {})
        rules_dir_str = gate_cfg.get("rules_dir")
        rules_dir = (project_root / rules_dir_str).resolve() if rules_dir_str else None
        vrchat_tier = gate_cfg.get("vrchat_tier_target", "Good")

        try:
            report = gate_check(
                vrm_path=vrm_path,
                targets=body.targets,
                rules_dir=rules_dir,
                vrchat_tier=vrchat_tier,
            )
            result = {
                "passed": report.passed,
                "vrm_path": str(report.vrm_path),
                "targets_checked": [t.value for t in report.targets_checked],
                "elapsed_seconds": report.elapsed_seconds,
                "results": {
                    key: {
                        "passed": tr.passed,
                        "violations": [
                            {
                                "rule_id": v.rule_id,
                                "severity": v.severity.value,
                                "description": v.description,
                            }
                            for v in tr.violations
                        ],
                    }
                    for key, tr in report.results.items()
                },
            }
            return JSONResponse(content=result)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc  # type: ignore[misc]

    @app.get("/v1/assets")
    async def list_assets(asset_type: str | None = None, tag: str | None = None) -> JSONResponse:  # type: ignore[misc]
        from seidr_smidja.config import _find_config_root
        from seidr_smidja.hoard.local import LocalHoardAdapter
        from seidr_smidja.hoard.port import AssetFilter

        cfg = _get_config()
        project_root = _find_config_root()
        hoard = LocalHoardAdapter.from_config(cfg, project_root)

        filt = AssetFilter(
            asset_type=asset_type,
            tags=[tag] if tag else [],
        )
        assets = hoard.list_assets(filt)
        return JSONResponse(
            content=[
                {
                    "asset_id": a.asset_id,
                    "display_name": a.display_name,
                    "asset_type": a.asset_type,
                    "tags": a.tags,
                    "vrm_version": a.vrm_version,
                    "cached": a.cached,
                }
                for a in assets
            ]
        )

    @app.get("/v1/avatars/{session_id}")
    async def get_session(session_id: str) -> JSONResponse:
        annall = _get_annall()
        try:
            record = annall.get_session(session_id)
            return JSONResponse(
                content={
                    "session_id": record.summary.session_id,
                    "agent_id": record.summary.agent_id,
                    "bridge_type": record.summary.bridge_type,
                    "started_at": (
                        record.summary.started_at.isoformat() if record.summary.started_at else None
                    ),
                    "ended_at": (
                        record.summary.ended_at.isoformat() if record.summary.ended_at else None
                    ),
                    "success": record.summary.success,
                    "summary": record.summary.summary,
                    "events": [
                        {
                            "event_type": e.event_type,
                            "severity": e.severity,
                            "payload": e.payload,
                            "timestamp": e.timestamp.isoformat(),
                        }
                        for e in record.events
                    ],
                }
            )
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    # ── Brúarhönd dispatch endpoint ───────────────────────────────────────────
    # POST /v1/brunhand/dispatch — Mode A/C lateral VRoid primitive dispatch
    # Mode A: brunhand primitive only (no forge pipeline)
    # Mode C: caller supplies a run_id to correlate with a parallel dispatch() call

    @app.post("/v1/brunhand/dispatch")
    async def brunhand_dispatch_endpoint(body: BrunhandDispatchBody) -> JSONResponse:  # type: ignore[misc]
        """Dispatch a Brúarhönd primitive to a remote Horfunarþjónn daemon.

        Mode A: brunhand only — performs the primitive, returns the result.
        Mode C: caller passes a run_id shared with a concurrent /v1/avatars call.

        Authentication to the daemon is via BRUNHAND_TOKEN env var or the host
        entry in brunhand.hosts config (not this endpoint's bearer token).
        """
        from seidr_smidja.bridges.core.dispatch import BrunhandDispatchRequest, brunhand_dispatch

        cfg = _get_config()
        annall = _get_annall()

        request = BrunhandDispatchRequest(
            host_name=body.host_name,
            primitive=body.primitive,
            primitive_args=body.primitive_args,
            agent_id=body.agent_id or "straumur",
            run_id=body.run_id,
            request_id=str(uuid.uuid4()),
            config=cfg,
            token_override=body.token,
        )

        response = brunhand_dispatch(request, annall)

        result: dict[str, Any] = {
            "success": response.success,
            "request_id": response.request_id,
            "primitive": response.primitive,
            "host": response.host,
            "run_id": response.run_id,
            "elapsed_seconds": response.elapsed_seconds,
        }
        if response.success and response.result is not None:
            # Serialize the result — convert dataclass to dict safely
            try:
                import dataclasses
                if dataclasses.is_dataclass(response.result):
                    result["result"] = dataclasses.asdict(response.result)
                elif hasattr(response.result, "__dict__"):
                    result["result"] = response.result.__dict__
                else:
                    result["result"] = response.result
            except Exception:
                result["result"] = str(response.result)
        else:
            result["error_type"] = response.error_type
            result["error_message"] = response.error_message

        status_code = 200 if response.success else 422
        return JSONResponse(content=result, status_code=status_code)

    return app


# Module-level app instance for uvicorn
def _build_app() -> Any:
    from seidr_smidja.config import load_config

    cfg = load_config()
    return create_app(cfg)


if _FASTAPI_AVAILABLE:
    app = _build_app()
else:
    app = None  # type: ignore[assignment,misc]

if __name__ == "__main__":
    import uvicorn  # type: ignore[import]

    from seidr_smidja.config import load_config  # noqa: E402  (local import in __main__)

    # H-005: Default to localhost-only binding.
    # The forge is documented as an agent-only system. Exposing it on all interfaces
    # (0.0.0.0) without auth makes it reachable from any connected network.
    # Operators who genuinely need remote access must set SEIDR_STRAUMUR_HOST
    # AND set straumur.allow_remote_bind: true in config/user.yaml.
    _host = os.environ.get("SEIDR_STRAUMUR_HOST", "127.0.0.1")
    _port = int(os.environ.get("SEIDR_STRAUMUR_PORT", "8765"))

    # Safety check: warn loudly when binding beyond localhost
    _cfg = load_config() if _FASTAPI_AVAILABLE else {}
    _allow_remote = _cfg.get("straumur", {}).get("allow_remote_bind", False)
    if _host not in ("127.0.0.1", "::1", "localhost") and not _allow_remote:
        logger.error(
            "Straumur H-005: Refusing to bind to non-localhost host '%s' because "
            "straumur.allow_remote_bind is not set to true in config. "
            "Set SEIDR_STRAUMUR_HOST=127.0.0.1 or add 'straumur: {allow_remote_bind: true}' "
            "to config/user.yaml if remote access is intentional.",
            _host,
        )
        raise SystemExit(
            f"Straumur: refusing non-localhost bind to '{_host}' without allow_remote_bind=true."
        )
    if _host not in ("127.0.0.1", "::1", "localhost"):
        logger.warning(
            "Straumur: bound to %s:%d — this forge is accessible from remote hosts. "
            "There is no authentication. Ensure network access is restricted.",
            _host,
            _port,
        )

    uvicorn.run("seidr_smidja.bridges.straumur.api:app", host=_host, port=_port, reload=False)
